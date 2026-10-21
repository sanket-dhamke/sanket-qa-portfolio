from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from utils.http import assert_fast, elapsed_ms
from utils.jsonutil import dig


@pytest.mark.smoke
def test_gms_health_ok_and_fast(client: TestClient) -> None:
    response, ms = elapsed_ms(lambda: client.get("/health"))
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["component"] == "datahub-gms"
    assert_fast(ms / 1000.0)


@pytest.mark.smoke
def test_gms_config_schema(client: TestClient) -> None:
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert dig(body, "managedIngestion", "enabled") is True
    assert "datahub-gms" in dig(body, "datahub", "server")
