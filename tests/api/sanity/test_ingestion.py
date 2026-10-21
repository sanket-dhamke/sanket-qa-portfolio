from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from tests.helpers.graphql import ASSET_COUNTS, CREATE_EXEC, POLL_EXEC, gql
from utils.jsonutil import dig


@pytest.mark.sanity
def test_asset_counts_match_fixture(client: TestClient) -> None:
    response = client.post("/api/graphql", json=gql(ASSET_COUNTS))
    assert response.status_code == 200
    counts = dig(response.json(), "data", "assetCounts")
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
    source_urn = dig(created.json(), "data", "createIngestionSource")
    assert source_urn.startswith("urn:li:dataHubIngestionSource:")

    exec_resp = client.post(
        "/api/graphql",
        json=gql(CREATE_EXEC, {"input": {"ingestionSourceUrn": source_urn}}),
    )
    assert exec_resp.status_code == 200
    run_id = dig(exec_resp.json(), "data", "createIngestionExecutionRequest")
    assert run_id.startswith("urn:li:dataHubExecutionRequest:")

    statuses = []
    body = None
    for _ in range(4):
        poll = client.post("/api/graphql", json=gql(POLL_EXEC, {"urn": run_id}))
        assert poll.status_code == 200
        body = dig(poll.json(), "data", "listExecutionRequests")["executionRequests"][0]
        statuses.append(body["result"]["status"])
        if body["result"]["status"] == "SUCCESS":
            break
    assert statuses[0] == "PENDING"
    assert "RUNNING" in statuses
    assert body["result"]["status"] == "SUCCESS"
    assert body["result"]["durationMs"] == 18420
