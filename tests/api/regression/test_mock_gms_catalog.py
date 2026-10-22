"""Regression: broader mock GMS catalog, login edges, and cluster fixture checks."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent.executor import load
from tests.helpers.auth import login_body
from tests.helpers.graphql import CREATE_EXEC, LIST_SOURCES, POLL_EXEC, gql
from tests.helpers.lab_evidence import component_pod
from utils.jsonutil import dig


@pytest.mark.regression
def test_unsupported_aspect_action_fails(client: TestClient) -> None:
    response = client.post("/aspects?action=notARealAction", json={"proposal": {}})
    assert response.status_code == 200
    assert response.json()["success"] is False


@pytest.mark.regression
def test_reset_clears_created_ingestion_source(client: TestClient) -> None:
    created = client.post(
        "/api/graphql",
        json={
            "query": 'mutation { createIngestionSource(input: { name: "adhoc-lab", type: "postgres" }) }'
        },
    )
    assert created.status_code == 200
    listed = client.post("/api/graphql", json=gql(LIST_SOURCES))
    assert dig(listed.json(), "data", "listIngestionSources", "total") == 3
    reset = client.post("/reset")
    assert reset.json()["status"] == "reset"
    listed = client.post("/api/graphql", json=gql(LIST_SOURCES))
    assert dig(listed.json(), "data", "listIngestionSources", "total") == 2


@pytest.mark.regression
def test_login_unknown_user_unauthorized(client: TestClient) -> None:
    response = client.post("/logIn", json=login_body(username="not-a-lab-user"))
    assert response.status_code == 401


@pytest.mark.regression
def test_dataset_graphql_is_not_implemented(client: TestClient) -> None:
    response = client.post("/api/graphql", json={"query": "query { dataset }"})
    assert response.status_code == 400
    assert "errors" in response.json()


@pytest.mark.regression
def test_health_mode_is_lab_mock(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["ok"] is True
    assert body["mode"] == "lab-mock"
    assert body["component"] == "datahub-gms"


@pytest.mark.regression
def test_listed_source_assets_sum_to_fixture_total(client: TestClient) -> None:
    payload = dig(
        client.post("/api/graphql", json=gql(LIST_SOURCES)).json(),
        "data",
        "listIngestionSources",
    )
    assert sum(row["assets"] for row in payload["ingestionSources"]) == 140


@pytest.mark.regression
def test_ingest_proposal_returns_orders_urn(client: TestClient) -> None:
    response = client.post("/aspects?action=ingestProposal", json={"proposal": {}})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "analytics.public.orders" in response.json()["urn"]


@pytest.mark.regression
def test_create_source_inline_mutation(client: TestClient) -> None:
    response = client.post(
        "/api/graphql",
        json={
            "query": """
            mutation {
              createIngestionSource(input: {
                name: "inline-postgres"
                type: "postgres"
                config: { executorId: "default" }
              })
            }
            """
        },
    )
    assert response.status_code == 200
    urn = dig(response.json(), "data", "createIngestionSource")
    assert urn.startswith("urn:li:dataHubIngestionSource:")


@pytest.mark.regression
def test_execution_poll_pending_then_running(client: TestClient) -> None:
    create = client.post(
        "/api/graphql",
        json={
            "query": 'mutation { createIngestionSource(input: { name: "poll-lab", type: "postgres" }) }'
        },
    )
    source_urn = dig(create.json(), "data", "createIngestionSource")
    exec_resp = client.post(
        "/api/graphql",
        json=gql(CREATE_EXEC, {"input": {"ingestionSourceUrn": source_urn}}),
    )
    run_id = dig(exec_resp.json(), "data", "createIngestionExecutionRequest")
    first = client.post("/api/graphql", json=gql(POLL_EXEC, {"urn": run_id}))
    second = client.post("/api/graphql", json=gql(POLL_EXEC, {"urn": run_id}))
    assert (
        dig(first.json(), "data", "listExecutionRequests", "executionRequests")[0]["result"]["status"]
        == "PENDING"
    )
    assert (
        dig(second.json(), "data", "listExecutionRequests", "executionRequests")[0]["result"]["status"]
        == "RUNNING"
    )


@pytest.mark.regression
def test_mae_memory_is_at_the_pod_limit() -> None:
    workers = {row["component"]: row for row in load("metrics.json")["workers"]}
    mae = workers["datahub-mae-consumer"]
    assert mae["memory_mib"] == mae["memory_limit_mib"] == 1536


@pytest.mark.regression
def test_gms_java_opts_set_heap() -> None:
    opts = load("cluster.json")["platform"]["gms_java_opts"]
    assert "-Xms1g" in opts
    assert "-Xmx2g" in opts


@pytest.mark.regression
def test_actions_executor_pod_is_running() -> None:
    actions = component_pod("datahub-actions")
    assert actions["status"] == "Running"
    assert actions["ready"] is True
    assert actions["memory_limit_mib"] == 2048


@pytest.mark.regression
def test_oracle_source_is_present(client: TestClient) -> None:
    payload = dig(
        client.post("/api/graphql", json=gql(LIST_SOURCES)).json(),
        "data",
        "listIngestionSources",
    )
    names = {row["name"]: row for row in payload["ingestionSources"]}
    assert names["oracle-finance"]["type"] == "oracle"
    assert names["oracle-finance"]["assets"] == 54


@pytest.mark.regression
def test_config_stateful_ingestion_capable(client: TestClient) -> None:
    body = client.get("/config").json()
    assert body["statefulIngestionCapable"] is True
    assert "datahub-gms" in body["datahub"]["server"]


@pytest.mark.regression
def test_duplicate_create_sources_get_unique_urns(client: TestClient) -> None:
    query = {
        "query": 'mutation { createIngestionSource(input: { name: "dup-lab", type: "postgres" }) }'
    }
    first = dig(client.post("/api/graphql", json=query).json(), "data", "createIngestionSource")
    second = dig(client.post("/api/graphql", json=query).json(), "data", "createIngestionSource")
    assert first != second
    assert first.startswith("urn:li:dataHubIngestionSource:")
    assert second.startswith("urn:li:dataHubIngestionSource:")
