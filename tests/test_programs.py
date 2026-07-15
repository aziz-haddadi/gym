from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.program import WorkoutProgramCycleState
from app.services.time import local_today

pytestmark = pytest.mark.anyio


async def create_program(
    client,
    *,
    name="My split",
    advance_on_any_workout=True,
    steps=None,
):
    response = await client.post(
        "/api/programs",
        json={
            "name": name,
            "advance_on_any_workout": advance_on_any_workout,
            "steps": steps
            or [
                {
                    "step_type": "workout",
                    "label": "Push",
                    "muscle_groups": ["Chest", "Triceps"],
                },
                {"step_type": "rest", "label": "Rest day"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_machine(client, name, muscle_group):
    response = await client.post(
        "/api/machines", json={"name": name, "muscle_group": muscle_group}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def log_workout(client, title, machine_ids):
    response = await client.post(
        "/api/workouts",
        json={
            "workout_date": str(local_today("Africa/Tunis")),
            "title": title,
            "entries": [
                {
                    "machine_id": machine_id,
                    "sets": [{"weight_kg": 20, "reps": 10}],
                }
                for machine_id in machine_ids
            ],
        },
    )
    assert response.status_code == 201, response.text


async def test_activation_keeps_exactly_one_active_and_resets_new_program(
    authenticated_client,
):
    first = await create_program(authenticated_client, name="First")
    second = await create_program(
        authenticated_client,
        name="Second",
        steps=[{"step_type": "workout", "label": "Legs", "muscle_groups": ["Legs"]}],
    )

    response = await authenticated_client.post(f"/api/programs/{first['id']}/activate")
    assert response.status_code == 200
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["program_id"] == first["id"]
    assert due["step"]["position"] == 0

    response = await authenticated_client.post(f"/api/programs/{second['id']}/activate")
    assert response.status_code == 200
    programs = (await authenticated_client.get("/api/programs")).json()
    assert sum(program["is_active"] for program in programs) == 1
    assert next(program for program in programs if program["is_active"])["id"] == second["id"]
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["program_id"] == second["id"]
    assert due["step"]["position"] == 0


async def test_workout_advances_then_rest_lazily_advances_but_workout_waits(
    authenticated_client,
):
    chest = await create_machine(authenticated_client, "Chest press", "Chest")
    program = await create_program(
        authenticated_client,
        steps=[
            {"step_type": "workout", "label": "Chest", "muscle_groups": ["Chest"]},
            {"step_type": "rest", "label": "Recovery"},
            {"step_type": "workout", "label": "Pull", "muscle_groups": ["Back"]},
        ],
    )
    await authenticated_client.post(f"/api/programs/{program['id']}/activate")

    await log_workout(authenticated_client, "Chest", [chest])
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["step"]["label"] == "Recovery"

    with SessionLocal() as db:
        state = db.scalar(select(WorkoutProgramCycleState))
        state.last_advanced_date = local_today("Africa/Tunis") - timedelta(days=1)
        db.commit()

    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["step"]["label"] == "Pull"

    old_date = local_today("Africa/Tunis") - timedelta(days=20)
    with SessionLocal() as db:
        state = db.scalar(select(WorkoutProgramCycleState))
        state.last_advanced_date = old_date
        db.commit()

    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["step"]["label"] == "Pull"
    assert due["last_advanced_date"] == str(old_date)


async def test_match_mode_requires_every_planned_muscle_group(authenticated_client):
    chest = await create_machine(authenticated_client, "Chest press", "Chest")
    back = await create_machine(authenticated_client, "Pulldown", "Back")
    program = await create_program(
        authenticated_client,
        advance_on_any_workout=False,
        steps=[
            {
                "step_type": "workout",
                "label": "Upper",
                "muscle_groups": ["Chest", "Back"],
            },
            {"step_type": "rest", "label": "Rest"},
        ],
    )
    await authenticated_client.post(f"/api/programs/{program['id']}/activate")

    await log_workout(authenticated_client, "Chest only", [chest])
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["step"]["label"] == "Upper"

    await log_workout(authenticated_client, "Full upper", [chest, back])
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["step"]["step_type"] == "rest"


async def test_reordering_preserves_due_step_identity_and_removal_moves_forward(
    authenticated_client,
):
    program = await create_program(
        authenticated_client,
        steps=[
            {"step_type": "workout", "label": "A"},
            {"step_type": "workout", "label": "B"},
            {"step_type": "workout", "label": "C"},
        ],
    )
    await authenticated_client.post(f"/api/programs/{program['id']}/activate")
    await authenticated_client.post(
        "/api/programs/active/advance",
        json={"target_step_id": program["steps"][1]["id"]},
    )

    steps_by_label = {step["label"]: step for step in program["steps"]}
    reordered = [steps_by_label[label] for label in ("C", "B", "A")]
    response = await authenticated_client.put(
        f"/api/programs/{program['id']}/steps",
        json={
            "steps": [
                {
                    "id": step["id"],
                    "step_type": step["step_type"],
                    "label": step["label"],
                    "muscle_groups": step["muscle_groups"],
                }
                for step in reordered
            ]
        },
    )
    assert response.status_code == 200, response.text
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["step"]["id"] == steps_by_label["B"]["id"]
    assert due["step"]["position"] == 1

    response = await authenticated_client.put(
        f"/api/programs/{program['id']}/steps",
        json={
            "steps": [
                {
                    "id": step["id"],
                    "step_type": step["step_type"],
                    "label": step["label"],
                    "muscle_groups": step["muscle_groups"],
                }
                for step in (steps_by_label["C"], steps_by_label["A"])
            ]
        },
    )
    assert response.status_code == 200, response.text
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["step"]["id"] == steps_by_label["A"]["id"]


async def test_manual_jump_and_archiving_active_program(authenticated_client):
    program = await create_program(authenticated_client)
    await authenticated_client.post(f"/api/programs/{program['id']}/activate")
    target = program["steps"][1]
    response = await authenticated_client.post(
        "/api/programs/active/advance", json={"target_step_id": target["id"]}
    )
    assert response.status_code == 200
    assert response.json()["step"]["id"] == target["id"]

    response = await authenticated_client.delete(f"/api/programs/{program['id']}")
    assert response.status_code == 204
    assert (await authenticated_client.get("/api/programs/active/due")).json() is None
    archived = (await authenticated_client.get("/api/programs?include_archived=true")).json()
    assert archived[0]["archived_at"] is not None
    assert archived[0]["is_active"] is False
