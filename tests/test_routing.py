"""No-network smoke: canned questions take different sources."""

from __future__ import annotations

import pytest

from agent.router import CANNED_QUESTIONS, route

pytestmark = pytest.mark.smoke


def test_oom_crash_uses_pod_handler() -> None:
    result = route("Which pods are crashing or restarting after OOM?")
    assert result["source"] == "handler:pod_status"
    assert result["metrics"]["crashing_pods"] >= 1
    assert result["metrics"]["oomkilled"] >= 1
    assert "datahub-mae-consumer" in result["answer"]
    assert "OOMKilled" in result["answer"]
    assert "7" in result["answer"]


def test_gms_cpu_uses_metrics_handler() -> None:
    result = route("Show CPU and memory of datahub-gms")
    assert result["source"] == "handler:resource_metrics"
    assert result["metrics"]["filter"] == "datahub-gms"
    workers = result["metrics"]["workers"]
    assert workers[0]["component"] == "datahub-gms"
    assert workers[0]["cpu_pct"] == 41.2
    assert "41.2" in result["answer"]


def test_sources_and_assets_use_ingestion_handler() -> None:
    result = route("Show postgres and oracle ingestion sources and total assets")
    assert result["source"] == "handler:ingestion_assets"
    assert result["metrics"]["postgres_assets"] == 86
    assert result["metrics"]["oracle_assets"] == 54
    assert result["metrics"]["total_assets"] == 140
    assert "postgres-analytics" in result["answer"]
    assert "oracle-finance" in result["answer"]
    assert "140" in result["answer"]


def test_ingest_postgres_opens_recipe() -> None:
    result = route("Ingest a postgres source")
    assert result["source"] == "handler:ingest_recipe"
    assert result["ui"] == "recipe_editor"
    assert "type: postgres" in result["recipe"]
    assert "host_port:" in result["recipe"]
    assert result["metrics"] is None


def test_graphql_create_uses_kb() -> None:
    result = route("What GraphQL mutation creates an ingestion source?")
    assert result["source"].startswith("kb:")
    assert "createIngestionSource" in result["answer"]
    assert "/api/graphql" in result["answer"]
    assert result["metrics"] is None


def test_canned_questions_take_distinct_sources() -> None:
    sources = [route(question)["source"] for question in CANNED_QUESTIONS]
    assert len(set(sources)) == len(CANNED_QUESTIONS)


def test_unknown_is_deterministic_fallback() -> None:
    result = route("write me a poem about lunch")
    assert result["source"] == "fallback:deterministic"
    assert result["metrics"] is None
    assert "will not invent" in result["answer"]


def test_mae_consumer_cpu_filters_component() -> None:
    result = route("Show CPU and memory of datahub-mae-consumer")
    assert result["source"] == "handler:resource_metrics"
    assert result["metrics"]["filter"] == "datahub-mae-consumer"
    assert result["metrics"]["workers"][0]["cpu_pct"] == 88.1
