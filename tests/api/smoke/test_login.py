from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.helpers.auth import assert_emuser_session, login_body


@pytest.mark.smoke
def test_login_emuser_ok(client: TestClient) -> None:
    response = client.post("/logIn", json=login_body())
    assert response.status_code == 200
    assert_emuser_session(response.json())


@pytest.mark.smoke
def test_login_from_payload_file(client: TestClient, payloads: Path) -> None:
    body = json.loads((payloads / "login.json").read_text(encoding="utf-8"))
    response = client.post("/logIn", json=body)
    assert response.status_code == 200
    assert_emuser_session(response.json())
