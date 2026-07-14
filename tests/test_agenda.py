import pytest

pytestmark = pytest.mark.anyio


async def test_weekly_agenda_crud(authenticated_client):
    response = await authenticated_client.get("/api/agenda")
    assert response.status_code == 200
    assert response.json() == []

    monday_response = await authenticated_client.put(
        "/api/agenda/0",
        json={"workout_name": "  Push   day  ", "notes": "Chest and triceps"},
    )
    assert monday_response.status_code == 200
    monday = monday_response.json()
    assert monday["day_of_week"] == 0
    assert monday["workout_name"] == "Push day"
    assert monday["notes"] == "Chest and triceps"

    friday_response = await authenticated_client.put(
        "/api/agenda/4",
        json={"workout_name": "Leg day"},
    )
    assert friday_response.status_code == 200

    response = await authenticated_client.get("/api/agenda")
    assert [item["day_of_week"] for item in response.json()] == [0, 4]

    update_response = await authenticated_client.put(
        "/api/agenda/0",
        json={"workout_name": "Pull day", "notes": "  "},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == monday["id"]
    assert updated["workout_name"] == "Pull day"
    assert updated["notes"] is None

    response = await authenticated_client.get("/api/agenda")
    assert len(response.json()) == 2

    invalid_response = await authenticated_client.put(
        "/api/agenda/7",
        json={"workout_name": "Invalid"},
    )
    assert invalid_response.status_code == 422

    delete_response = await authenticated_client.delete("/api/agenda/0")
    assert delete_response.status_code == 204

    missing_response = await authenticated_client.delete("/api/agenda/0")
    assert missing_response.status_code == 404
