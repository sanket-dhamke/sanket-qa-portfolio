from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from utils.jsonutil import dig


@pytest.mark.sanity
def test_list_incidents_open_count(client: TestClient, payloads: Path) -> None:
    body = json.loads((payloads / "list_incidents.json").read_text(encoding="utf-8"))
    response = client.post("/api/graphql", json=body)
    assert response.status_code == 200
    payload = dig(response.json(), "data", "listIncidents")
    assert payload["open"] == 3
    assert payload["total"] == 5
