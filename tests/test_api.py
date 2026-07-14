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
                        {"weight_kg": 27.5, "reps": 10, "rpe": 7.5},
                        {"weight_kg": 22.5, "reps": 8, "rpe": 8, "is_drop_set": True},
                    ],
                }
            ],
        },
    )
    assert workout_response.status_code == 201
    workout = workout_response.json()
    assert workout["total_sets"] == 2
    assert workout["drop_sets"] == 1
    assert workout["entries"][0]["sets"][1]["is_drop_set"] is True
    assert float(workout["total_volume_kg"]) == 455

    stats_response = await authenticated_client.get("/api/stats/overview")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["total_workouts"] == 1
    assert stats["total_sets"] == 2
    assert stats["total_reps"] == 18
    assert float(stats["total_volume_kg"]) == 455
    assert float(stats["personal_records"][0]["max_weight_kg"]) == 27.5


async def test_specific_arm_muscle_groups_replace_combined_groups(authenticated_client):
    for group in ("Biceps", "Triceps", "Forearms"):
        response = await authenticated_client.post(
            "/api/machines",
            json={"name": f"{group} exercise", "muscle_group": group},
        )
        assert response.status_code == 201

    for removed_group in ("Arms", "Full Body"):
        response = await authenticated_client.post(
            "/api/machines",
            json={"name": f"Old {removed_group}", "muscle_group": removed_group},
        )
        assert response.status_code == 422


async def test_workout_date_range_drives_calendar_month(authenticated_client):
    for workout_date, title in (
        ("2026-07-14", "July push day"),
        ("2026-08-02", "August pull day"),
    ):
        response = await authenticated_client.post(
            "/api/workouts",
            json={"workout_date": workout_date, "title": title},
        )
        assert response.status_code == 201

    response = await authenticated_client.get(
        "/api/workouts?date_from=2026-07-01&date_to=2026-07-31&limit=100"
    )
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1
    assert [(item["workout_date"], item["title"]) for item in page["items"]] == [
        ("2026-07-14", "July push day")
    ]


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
