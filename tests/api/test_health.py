from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient


@pytest.mark.smoke
def test_gms_health_ok_and_fast(client: TestClient) -> None:
    started = time.perf_counter()
    response = client.get("/health")
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["component"] == "datahub-gms"
    assert elapsed < 1.0


@pytest.mark.smoke
def test_gms_config_schema(client: TestClient) -> None:
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert body["managedIngestion"]["enabled"] is True
    assert "datahub-gms" in body["datahub"]["server"]
