from datetime import timedelta

import pytest

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.services.time import local_today

pytestmark = pytest.mark.anyio


async def create_machine(client, name, muscle_group):
    response = await client.post(
        "/api/machines",
        json={"name": name, "muscle_group": muscle_group},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def create_template(client, name, machine_ids):
    response = await client.post(
        "/api/workout-templates",
        json={
            "name": name,
            "exercises": [
                {"machine_id": machine_id, "notes": f"Exercise {position + 1}"}
                for position, machine_id in enumerate(machine_ids)
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_saved_workout_crud_and_exercise_reordering(authenticated_client):
    press = await create_machine(authenticated_client, "Chest press", "Chest")
    fly = await create_machine(authenticated_client, "Cable fly", "Chest")
    template = await create_template(
        authenticated_client, "Chest workout", [press["id"], fly["id"]]
    )

    assert [item["machine_name"] for item in template["exercises"]] == [
        "Chest press",
        "Cable fly",
    ]
    assert all("sets" not in item for item in template["exercises"])

    response = await authenticated_client.put(
        f"/api/workout-templates/{template['id']}/exercises",
        json={
            "exercises": [
                {
                    "id": template["exercises"][1]["id"],
                    "machine_id": fly["id"],
                    "notes": "Start here",
                },
                {
                    "id": template["exercises"][0]["id"],
                    "machine_id": press["id"],
                    "notes": None,
                },
            ]
        },
    )
    assert response.status_code == 200, response.text
    assert [item["machine_name"] for item in response.json()["exercises"]] == [
        "Cable fly",
        "Chest press",
    ]

    response = await authenticated_client.delete(
        f"/api/workout-templates/{template['id']}"
    )
    assert response.status_code == 204
    assert (await authenticated_client.get("/api/workout-templates")).json() == []
    archived = (
        await authenticated_client.get(
            "/api/workout-templates?include_archived=true"
        )
    ).json()
    assert archived[0]["archived_at"] is not None


async def test_daily_session_can_replace_template_exercises_without_mutating_template(
    authenticated_client,
):
    curl = await create_machine(authenticated_client, "Biceps curl", "Biceps")
    hammer = await create_machine(authenticated_client, "Hammer curl", "Biceps")
    forearm = await create_machine(authenticated_client, "Wrist curl", "Forearms")
    template = await create_template(
        authenticated_client, "Arms", [curl["id"], hammer["id"]]
    )

    response = await authenticated_client.post(
        "/api/workouts",
        json={
            "template_id": template["id"],
            "workout_date": str(local_today("Africa/Tunis")),
            "title": "Arms — adjusted today",
            "entries": [
                {
                    "machine_id": curl["id"],
                    "sets": [{"weight_kg": 27.5, "reps": 10}],
                },
                {
                    "machine_id": forearm["id"],
                    "sets": [
                        {
                            "weight_kg": 22.5,
                            "reps": 12,
                            "is_drop_set": True,
                        }
                    ],
                },
            ],
        },
    )
    assert response.status_code == 201, response.text
    session = response.json()
    assert session["template_id"] == template["id"]
    assert session["template_name"] == "Arms"
    assert [entry["machine_name"] for entry in session["entries"]] == [
        "Biceps curl",
        "Wrist curl",
    ]
    assert float(session["entries"][0]["sets"][0]["weight_kg"]) == 27.5

    unchanged = (
        await authenticated_client.get(f"/api/workout-templates/{template['id']}")
    ).json()
    assert [item["machine_name"] for item in unchanged["exercises"]] == [
        "Biceps curl",
        "Hammer curl",
    ]


async def test_program_waits_for_start_date_and_linked_template_tracks_source(
    authenticated_client,
):
    push = await create_machine(authenticated_client, "Shoulder press", "Shoulders")
    replacement = await create_machine(
        authenticated_client, "Lateral raise", "Shoulders"
    )
    template = await create_template(authenticated_client, "Push", [push["id"]])
    today = local_today("Africa/Tunis")
    starts_on = today + timedelta(days=2)

    response = await authenticated_client.post(
        "/api/programs",
        json={
            "name": "Delayed split",
            "starts_on": str(starts_on),
            "advance_on_any_workout": False,
            "steps": [
                {
                    "step_type": "workout",
                    "label": "Push",
                    "linked_workout_template_id": template["id"],
                },
                {"step_type": "rest", "label": "Rest"},
            ],
        },
    )
    assert response.status_code == 201, response.text
    program = response.json()
    response = await authenticated_client.post(
        f"/api/programs/{program['id']}/activate",
        json={"starts_on": str(starts_on)},
    )
    assert response.status_code == 200, response.text

    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["is_started"] is False
    assert due["starts_on"] == str(starts_on)
    assert due["step"]["linked_workout_template_id"] == template["id"]

    early = await authenticated_client.post(
        "/api/workouts",
        json={
            "template_id": template["id"],
            "workout_date": str(today),
            "title": "Early session",
            "entries": [
                {
                    "machine_id": replacement["id"],
                    "sets": [{"weight_kg": 12.5, "reps": 12}],
                }
            ],
        },
    )
    assert early.status_code == 201, early.text
    assert (await authenticated_client.get("/api/programs/active/due")).json()[
        "step"
    ]["label"] == "Push"

    response = await authenticated_client.patch(
        f"/api/programs/{program['id']}", json={"starts_on": str(today)}
    )
    assert response.status_code == 200, response.text
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["is_started"] is True

    matching = await authenticated_client.post(
        "/api/workouts",
        json={
            "template_id": template["id"],
            "workout_date": str(today),
            "title": "Push — changed exercise today",
            "entries": [
                {
                    "machine_id": replacement["id"],
                    "sets": [{"weight_kg": 15, "reps": 10}],
                }
            ],
        },
    )
    assert matching.status_code == 201, matching.text
    due = (await authenticated_client.get("/api/programs/active/due")).json()
    assert due["step"]["step_type"] == "rest"


async def test_program_start_date_cannot_be_cleared(authenticated_client):
    response = await authenticated_client.post(
        "/api/programs",
        json={
            "name": "Simple split",
            "steps": [{"step_type": "workout", "label": "Train"}],
        },
    )
    assert response.status_code == 201, response.text

    response = await authenticated_client.patch(
        f"/api/programs/{response.json()['id']}", json={"starts_on": None}
    )
    assert response.status_code == 422


async def test_saved_workouts_are_private_to_their_owner(authenticated_client):
    machine = await create_machine(authenticated_client, "Private press", "Chest")
    template = await create_template(
        authenticated_client, "Private workout", [machine["id"]]
    )

    with SessionLocal() as db:
        db.add(
            User(
                username="other-athlete",
                password_hash=hash_password("another-correct-horse-password"),
                timezone="Africa/Tunis",
            )
        )
        db.commit()

    assert (await authenticated_client.post("/api/auth/logout")).status_code == 204
    login = await authenticated_client.post(
        "/api/auth/login",
        json={
            "username": "other-athlete",
            "password": "another-correct-horse-password",
        },
    )
    assert login.status_code == 200, login.text

    response = await authenticated_client.get(
        f"/api/workout-templates/{template['id']}"
    )
    assert response.status_code == 404
    assert (await authenticated_client.get("/api/workout-templates")).json() == []

    response = await authenticated_client.post(
        "/api/workouts",
        json={
            "template_id": template["id"],
            "workout_date": str(local_today("Africa/Tunis")),
            "title": "Unauthorized source",
            "entries": [],
        },
    )
    assert response.status_code == 404
