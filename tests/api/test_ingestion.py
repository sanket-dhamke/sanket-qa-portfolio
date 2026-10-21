from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

LIST_SOURCES = """
query {
  listIngestionSources(input: { start: 0, count: 20 }) {
    total
    ingestionSources {
      urn
      name
      type
      assets
    }
  }
}
"""

ASSET_COUNTS = """
query {
  assetCounts
}
"""

CREATE_EXEC = """
mutation($input: CreateIngestionExecutionRequestInput!) {
  createIngestionExecutionRequest(input: $input)
}
"""

POLL = """
query($urn: String!) {
  listExecutionRequests(urn: $urn) {
    executionRequests {
      urn
      result { status durationMs }
    }
  }
}
"""


@pytest.mark.smoke
def test_list_ingestion_sources_postgres_and_oracle(client: TestClient) -> None:
    started = time.perf_counter()
    response = client.post("/api/graphql", json={"query": LIST_SOURCES})
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    payload = response.json()["data"]["listIngestionSources"]
    names = {row["name"]: row for row in payload["ingestionSources"]}
    assert "postgres-analytics" in names
    assert names["postgres-analytics"]["type"] == "postgres"
    assert names["postgres-analytics"]["assets"] == 86
    assert names["oracle-finance"]["type"] == "oracle"
    assert names["oracle-finance"]["assets"] == 54
    assert payload["total"] == 2
    assert elapsed < 1.0


@pytest.mark.sanity
def test_asset_counts_match_fixture(client: TestClient) -> None:
    response = client.post("/api/graphql", json={"query": ASSET_COUNTS})
    assert response.status_code == 200
    counts = response.json()["data"]["assetCounts"]
    assert counts["assets"] == 140
    assert counts["datasets"] == 115
    assert set(counts) >= {"assets", "datasets", "containers", "dataJobs", "lineage_edges"}


@pytest.mark.sanity
def test_create_source_from_yaml_then_poll_execution(
    client: TestClient, payloads: Path
) -> None:
    recipe = yaml.safe_load((payloads / "postgres_recipe.yml").read_text(encoding="utf-8"))
    assert recipe["source"]["type"] == "postgres"
    assert recipe["source"]["config"]["host_port"] == "db.lab.example:5432"
    assert recipe["source"]["config"]["database"] == "analytics"
    assert "public" in recipe["source"]["config"]["schema_pattern"]["allow"]

    create = json.loads(
        (payloads / "create_ingestion_source.json").read_text(encoding="utf-8")
    )
    create["variables"]["input"]["name"] = recipe["pipeline_name"]
    create["variables"]["input"]["type"] = recipe["source"]["type"]
    create["variables"]["input"]["config"]["recipe"] = json.dumps(recipe)

    created = client.post("/api/graphql", json=create)
    assert created.status_code == 200
    source_urn = created.json()["data"]["createIngestionSource"]
    assert source_urn.startswith("urn:li:dataHubIngestionSource:")

    exec_resp = client.post(
        "/api/graphql",
        json={
            "query": CREATE_EXEC,
            "variables": {"input": {"ingestionSourceUrn": source_urn}},
        },
    )
    assert exec_resp.status_code == 200
    run_id = exec_resp.json()["data"]["createIngestionExecutionRequest"]
    assert run_id.startswith("urn:li:dataHubExecutionRequest:")

    statuses = []
    body = None
    for _ in range(4):
        poll = client.post("/api/graphql", json={"query": POLL, "variables": {"urn": run_id}})
        assert poll.status_code == 200
        body = poll.json()["data"]["listExecutionRequests"]["executionRequests"][0]
        statuses.append(body["result"]["status"])
        if body["result"]["status"] == "SUCCESS":
            break
    assert statuses[0] == "PENDING"
    assert "RUNNING" in statuses
    assert body["result"]["status"] == "SUCCESS"
    assert body["result"]["durationMs"] == 18420
