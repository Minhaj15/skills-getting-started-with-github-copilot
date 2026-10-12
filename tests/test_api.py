from copy import deepcopy
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


INITIAL_ACTIVITIES = deepcopy(activities)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_activities():
    activities.clear()
    activities.update(deepcopy(INITIAL_ACTIVITIES))
    yield
    activities.clear()
    activities.update(deepcopy(INITIAL_ACTIVITIES))


def test_get_activities_returns_activity_data_without_caching(client):
    # Arrange
    activity_name = "Chess Club"

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert activity_name in response.json()
    assert response.json()[activity_name]["participants"]
    assert response.headers["cache-control"] == "no-store"


def test_signup_adds_participant(client):
    # Arrange
    activity_name = "Art Club"
    email = "new.student@mergington.edu"
    signup_url = f"/activities/{quote(activity_name, safe='')}/signup"

    # Act
    response = client.post(signup_url, params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    assert email in client.get("/activities").json()[activity_name]["participants"]


def test_signup_rejects_duplicate_without_changing_participants(client):
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"
    signup_url = f"/activities/{quote(activity_name, safe='')}/signup"
    original_participants = client.get("/activities").json()[activity_name]["participants"]

    # Act
    response = client.post(signup_url, params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert client.get("/activities").json()[activity_name]["participants"] == original_participants


def test_signup_returns_not_found_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    signup_url = f"/activities/{quote(activity_name, safe='')}/signup"

    # Act
    response = client.post(signup_url, params={"email": "student@mergington.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_signup_routes_require_email_query_parameter(client, method):
    # Arrange
    signup_url = f"/activities/{quote('Art Club', safe='')}/signup"

    # Act
    response = client.request(method, signup_url)

    # Assert
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "email"]


def test_unregister_removes_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "michael@mergington.edu"
    signup_url = f"/activities/{quote(activity_name, safe='')}/signup"
    original_participants = client.get("/activities").json()[activity_name]["participants"]

    # Act
    response = client.delete(signup_url, params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {activity_name}"
    }
    updated_participants = client.get("/activities").json()[activity_name]["participants"]
    assert email not in updated_participants
    assert len(updated_participants) == len(original_participants) - 1


def test_unregister_returns_not_found_for_missing_participant(client):
    # Arrange
    activity_name = "Chess Club"
    signup_url = f"/activities/{quote(activity_name, safe='')}/signup"

    # Act
    response = client.delete(
        signup_url,
        params={"email": "not.signed.up@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_unregister_returns_not_found_for_unknown_activity(client):
    # Arrange
    activity_name = "Unknown Club"
    signup_url = f"/activities/{quote(activity_name, safe='')}/signup"

    # Act
    response = client.delete(
        signup_url,
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"