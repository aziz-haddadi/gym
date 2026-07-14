import pytest

pytestmark = pytest.mark.anyio


async def test_complete_workout_flow(authenticated_client):
    machine_response = await authenticated_client.post(
        "/api/machines",
        json={
            "name": "Incline Chest Press",
            "muscle_group": "Chest",
            "notes": "Seat position 4",
        },
    )
    assert machine_response.status_code == 201
    machine_id = machine_response.json()["id"]

    workout_response = await authenticated_client.post(
        "/api/workouts",
        json={
            "workout_date": "2026-07-14",
            "title": "Push day",
            "duration_minutes": 64,
            "entries": [
                {
                    "machine_id": machine_id,
                    "sets": [
                        {"weight_kg": 50, "reps": 10, "rpe": 7.5},
                        {"weight_kg": 55, "reps": 8, "rpe": 8},
                    ],
                }
            ],
        },
    )
    assert workout_response.status_code == 201
    workout = workout_response.json()
    assert workout["total_sets"] == 2
    assert float(workout["total_volume_kg"]) == 940

    stats_response = await authenticated_client.get("/api/stats/overview")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_workouts"] == 1
    assert stats["total_sets"] == 2
    assert stats["total_reps"] == 18
    assert float(stats["total_volume_kg"]) == 940
    assert float(stats["personal_records"][0]["max_weight_kg"]) == 55


async def test_machine_names_are_unique_per_user(authenticated_client):
    payload = {"name": "Leg Press", "muscle_group": "Legs"}
    assert (await authenticated_client.post("/api/machines", json=payload)).status_code == 201

    duplicate = await authenticated_client.post(
        "/api/machines", json={"name": "  leg   press ", "muscle_group": "Legs"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "A machine with this name already exists"


async def test_anonymous_api_request_is_rejected(client):
    response = await client.get("/api/machines")

    assert response.status_code == 401
