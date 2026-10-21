from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.regression
def test_unknown_graphql_operation_returns_errors(client: TestClient) -> None:
    response = client.post("/api/graphql", json={"query": "query { notARealField }"})
    assert response.status_code == 400
    body = response.json()
    assert "errors" in body
    assert "mock GMS" in body["errors"][0]["message"]
