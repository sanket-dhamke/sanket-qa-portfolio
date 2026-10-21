from __future__ import annotations

from agent.router import route


def test_login_with_lab_user() -> None:
    result = route(
        "Test the login with username as emuser and password as empass"
    )
    assert result["source"] == "handler:login_api"
    assert result["metrics"]["ok"] is True
    assert result["metrics"]["status"] == 200
    assert "urn:li:corpuser:emuser" in result["answer"]
    assert result["metrics"] is not None


def test_login_without_credentials_does_not_invent() -> None:
    result = route("Test the login")
    assert result["source"] == "handler:login_api"
    assert result["metrics"]["ok"] is False
    assert result["metrics"]["status"] == 400
    assert "will not invent" in result["answer"]


def test_login_wrong_password() -> None:
    result = route("login with username as emuser and password as wrong")
    assert result["metrics"]["status"] == 401
    assert "401" in result["answer"]
    assert "RCA" in result["answer"]


def test_api_sanity_suite_has_formatted_failure() -> None:
    result = route("Run API sanity suite")
    assert result["route"] == "run_suite"
    assert result["metrics"]["suite"] == "sanity"
    assert result["metrics"]["layer"] == "api"
    assert result["metrics"]["verdict"] == "PASS"
    assert result["metrics"]["failed"] == 0


def test_ui_sanity_suite_reports_search_rca() -> None:
    result = route("Check UI sanity")
    assert result["metrics"]["suite"] == "sanity"
    assert result["metrics"]["layer"] == "ui"
    assert result["metrics"]["verdict"] == "FAIL"
    assert "ui.search_datasets" in result["metrics"]["failed_ids"]
    assert "MAE consumer" in result["answer"] or "mae-consumer" in result["answer"]
    assert "Cause:" in result["answer"]
    assert "Fix:" in result["answer"]


def test_how_many_assets_stays_on_ingestion_handler() -> None:
    result = route("How many assets are there?")
    assert result["source"] == "handler:ingestion_assets"
    assert result["metrics"]["total_assets"] == 140
    assert "140" in result["answer"]


def test_alerts_run_incidents_api() -> None:
    result = route("check total no of alerts in datahub")
    assert result["source"] == "handler:execute_api:graphql.listIncidents"
    assert result["metrics"]["open"] == 3
    assert "Open: 3" in result["answer"]


def test_capacity_1m_and_10m() -> None:
    result = route(
        "What configuration needs to be upgraded to ingest 10m or 1m assets?"
    )
    assert result["source"] == "handler:capacity_plan"
    assert result["metrics"]["current_assets"] == 140
    assert result["metrics"]["targets"] == [10_000_000, 1_000_000]
    assert "datahub-mae-consumer" in result["answer"]
    assert "OOM" in result["answer"] or "1536" in result["answer"]
    assert "1 million" in result["answer"]
    assert "10 million" in result["answer"]


def test_app_status_runs_smoke_sanity_and_asks_regression() -> None:
    result = route("What is the current state of the application?")
    assert result["source"] == "handler:app_status"
    assert result["metrics"]["health"] == "DEGRADED"
    assert result["awaiting_regression"] is True
    assert result["session_update"]["awaiting_regression"] is True
    assert "smoke" in result["answer"].lower()
    assert "sanity" in result["answer"].lower()
    assert "yes" in result["answer"].lower()


def test_yes_after_status_runs_regression() -> None:
    first = route("What is the current state of the application?")
    session = first["session_update"]
    result = route("yes", session=session)
    assert result["route"] == "run_suite"
    assert result["metrics"]["suite"] == "regression"
    assert result["metrics"]["verdict"] == "FAIL"
    assert "perf.mae_memory_headroom" in result["metrics"]["failed_ids"]
    assert result["session_update"]["awaiting_regression"] is False


def test_no_after_status_skips_regression() -> None:
    first = route("what is current state of the application")
    result = route("no", session=first["session_update"])
    assert result["route"] == "skip_regression"
    assert result["metrics"]["regression"] == "skipped"
