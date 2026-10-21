from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers.auth import login_body


@pytest.mark.regression
def test_login_rejects_bad_password(client: TestClient) -> None:
    response = client.post("/logIn", json=login_body(password="nope"))
    assert response.status_code == 401


@pytest.mark.regression
def test_login_missing_body_unauthorized(client: TestClient) -> None:
    response = client.post("/logIn", json={})
    assert response.status_code == 401
