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
    assert "not of node capacity" in result["answer"]
    assert "pod's configured limit" in result["answer"]


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


def test_why_api_sanity_fail_is_read_not_a_job() -> None:
    result = route("Why did API sanity fail?")
    assert result["route"] == "suite_explain"
    assert result["metrics"]["mode"] == "read"
    assert result["metrics"]["git_pull"] is False
    assert "job" not in result
    assert result["answer"].startswith("API sanity failed (11/12)")
    assert "Open Allure report" in result["answer"]
    assert "Catalog replay" in result["answer"]
    assert "Catalog read" not in result["answer"]
    assert "git_pull" not in result["answer"]
    assert "api.mae_search_index" in (result["metrics"].get("failed_ids") or [])
    assert result["allure"][0]["href"] == "reports/allure-api/index.html"


def test_run_api_smoke_is_user_friendly_with_allure() -> None:
    result = route("Run API smoke")
    assert result["route"] == "run_suite"
    assert result["metrics"]["layer"] == "api"
    assert result["metrics"]["suite"] == "smoke"
    assert result["job"]["git_pull"] is False
    assert result["job"]["credentials"] == "none"
    assert result["job"]["sha"]
    assert result["answer"].splitlines()[0] == "API smoke passed (6/6) in ~400 ms"
    assert "GMS GET /health" in result["answer"]
    assert "Open Allure report" in result["answer"]
    assert "Catalog replay — not a live pytest run." in result["answer"]
    assert "Pipeline job" not in result["answer"]
    assert "git_pull" not in result["answer"]
    assert "Jenkins" not in result["answer"]
    assert "handler:run_suite" not in result["answer"]
    assert "GitHub Pages does not spawn" not in result["answer"]
    assert result["allure"][0]["href"] == "reports/allure-api/index.html"
    assert result["allure"][0]["label"] == "Open Allure report"


def test_last_pipeline_sha_is_read() -> None:
    result = route("What is the last pipeline SHA?")
    assert result["route"] == "pipeline_status"
    assert result["metrics"]["mode"] == "read"
    assert "never git-pulls" in result["answer"]


def test_mae_consumer_cpu_filters_component() -> None:
    result = route("Show CPU and memory of datahub-mae-consumer")
    assert result["source"] == "handler:resource_metrics"
    assert result["metrics"]["filter"] == "datahub-mae-consumer"
    assert result["metrics"]["workers"][0]["cpu_pct"] == 88.1
