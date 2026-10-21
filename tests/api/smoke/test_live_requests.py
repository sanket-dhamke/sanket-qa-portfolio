"""Optional requests calls against a running mock GMS (uvicorn)."""

from __future__ import annotations

import pytest

from utils.gms import health, login


@pytest.mark.live
@pytest.mark.smoke
def test_live_mock_gms_health_with_requests() -> None:
    response = health()
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["component"] == "datahub-gms"


@pytest.mark.live
@pytest.mark.smoke
def test_live_login_emuser_with_requests() -> None:
    response = login()
    assert response.status_code == 200
    assert response.json()["actor"] == "urn:li:corpuser:emuser"
