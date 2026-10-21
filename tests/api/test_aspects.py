from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.sanity
def test_ingest_proposal_returns_dataset_urn(client: TestClient) -> None:
    response = client.post(
        "/aspects?action=ingestProposal",
        json={
            "proposal": {
                "entityType": "dataset",
                "entityUrn": "urn:li:dataset:(urn:li:dataPlatform:postgres,analytics.public.orders,PROD)",
                "aspectName": "datasetProperties",
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "postgres" in body["urn"]
    assert "orders" in body["urn"]
