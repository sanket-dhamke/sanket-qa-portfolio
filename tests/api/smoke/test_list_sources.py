from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers.graphql import LIST_SOURCES, gql
from utils.http import assert_fast, elapsed_ms
from utils.jsonutil import dig


@pytest.mark.smoke
def test_list_ingestion_sources_postgres_and_oracle(client: TestClient) -> None:
    response, ms = elapsed_ms(lambda: client.post("/api/graphql", json=gql(LIST_SOURCES)))
    assert response.status_code == 200
    payload = dig(response.json(), "data", "listIngestionSources")
    names = {row["name"]: row for row in payload["ingestionSources"]}
    assert names["postgres-analytics"]["type"] == "postgres"
    assert names["postgres-analytics"]["assets"] == 86
    assert names["oracle-finance"]["type"] == "oracle"
    assert names["oracle-finance"]["assets"] == 54
    assert payload["total"] == 2
    assert_fast(ms / 1000.0)
