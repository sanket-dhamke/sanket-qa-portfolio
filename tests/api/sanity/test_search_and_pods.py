"""Sanity: search/index freshness and pod story while GMS itself is healthy."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent.executor import load
from tests.helpers.graphql import ASSET_COUNTS, LIST_INCIDENTS, LIST_SOURCES, gql
from tests.helpers.lab_evidence import component_pod
from utils.jsonutil import dig


@pytest.mark.sanity
def test_search_across_entities_total_matches_fixture(client: TestClient) -> None:
    response = client.post(
        "/api/graphql",
        json={"query": "query { searchAcrossEntities { total } }"},
    )
    assert response.status_code == 200
    total = dig(response.json(), "data", "searchAcrossEntities", "total")
    assert total == 115


@pytest.mark.sanity
def test_open_incidents_include_mae_search_lag(client: TestClient) -> None:
    response = client.post("/api/graphql", json=gql(LIST_INCIDENTS))
    assert response.status_code == 200
    payload = dig(response.json(), "data", "listIncidents")
    titles = [row["title"] for row in payload["incidents"]]
    assert payload["open"] == 3
    assert any("MAE consumer OOM" in title or "Search index lag" in title for title in titles)


@pytest.mark.sanity
def test_postgres_source_still_listed(client: TestClient) -> None:
    response = client.post("/api/graphql", json=gql(LIST_SOURCES))
    assert response.status_code == 200
    names = {
        row["name"]: row
        for row in dig(response.json(), "data", "listIngestionSources", "ingestionSources")
    }
    assert names["postgres-analytics"]["type"] == "postgres"
    assert names["postgres-analytics"]["assets"] == 86


@pytest.mark.sanity
def test_config_cli_version_is_pinned(client: TestClient) -> None:
    response = client.get("/config")
    assert response.status_code == 200
    body = response.json()
    assert body["managedIngestion"]["defaultCliVersion"] == "0.14.1"
    assert body["managedIngestion"]["enabled"] is True


@pytest.mark.sanity
def test_frontend_pod_is_running() -> None:
    frontend = component_pod("datahub-frontend")
    assert frontend["status"] == "Running"
    assert frontend["ready"] is True
    assert frontend["restarts"] == 0
    assert not frontend.get("last_reason")


@pytest.mark.sanity
def test_mce_consumer_recovered_and_ready() -> None:
    mce = component_pod("datahub-mce-consumer")
    assert mce["status"] == "Running"
    assert mce["ready"] is True
    assert mce["restarts"] == 2
    assert mce.get("last_reason") == "Error"


@pytest.mark.sanity
def test_gms_health_still_ok_while_mae_is_down(client: TestClient) -> None:
    response = client.post("/api/graphql", json=gql(ASSET_COUNTS))
    assert client.get("/health").json()["ok"] is True
    assert response.status_code == 200
    assert dig(response.json(), "data", "assetCounts", "datasets") == 115
    mae = component_pod("datahub-mae-consumer", load("cluster.json"))
    assert mae["status"] == "CrashLoopBackOff"
    assert mae.get("last_reason") == "OOMKilled"
