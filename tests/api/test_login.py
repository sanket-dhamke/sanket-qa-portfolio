from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.smoke
def test_login_emuser_ok(client: TestClient) -> None:
    response = client.post("/logIn", json={"username": "emuser", "password": "empass"})
    assert response.status_code == 200
    body = response.json()
    assert body["actor"] == "urn:li:corpuser:emuser"
    assert body["role"] == "Admin"


@pytest.mark.sanity
def test_login_rejects_bad_password(client: TestClient) -> None:
    response = client.post("/logIn", json={"username": "emuser", "password": "nope"})
    assert response.status_code == 401


@pytest.mark.sanity
def test_list_incidents_open_count(client: TestClient) -> None:
    response = client.post(
        "/api/graphql",
        json={"query": "query { listIncidents { open total } }"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]["listIncidents"]
    assert payload["open"] == 3
    assert payload["total"] == 5


@pytest.mark.regression
def test_login_missing_body_unauthorized(client: TestClient) -> None:
    response = client.post("/logIn", json={})
    assert response.status_code == 401
