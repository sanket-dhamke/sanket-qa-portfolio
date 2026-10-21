from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.mark.sanity
def test_ingest_proposal_returns_dataset_urn(client: TestClient, payloads: Path) -> None:
    proposal = json.loads((payloads / "ingest_proposal.json").read_text(encoding="utf-8"))
    response = client.post("/aspects?action=ingestProposal", json=proposal)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "postgres" in body["urn"]
    assert "orders" in body["urn"]
