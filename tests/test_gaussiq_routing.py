"""No-network smoke: GaussIQ lab canned questions take different sources."""

from __future__ import annotations

import pytest

from gaussiq.router import CANNED_QUESTIONS, route

pytestmark = pytest.mark.smoke


def test_unknown_is_deterministic_fallback() -> None:
    result = route("write me a poem about lunch")
    assert result["source"] == "fallback:deterministic"
    assert result["metrics"] is None
    assert "will not invent" in result["answer"]
    assert result["model_available"] is False


def test_health_uses_app_status_handler() -> None:
    result = route("What is the current quality of GaussIQ 1.0?")
    assert result["source"] == "handler:app_status"
    assert result["metrics"]["health"] == "DEGRADED"
    assert result["metrics"]["gross_mttr_hours"] == 34.2
    assert "signal-connector" in result["answer"]
    assert result["awaiting_regression"] is True
    assert "not live production" in result["answer"]


def test_yes_after_health_runs_regression() -> None:
    session = {"awaiting_regression": True}
    result = route("yes", session=session)
    assert result["route"] == "run_suite"
    assert result["metrics"]["suite"] == "regression"
    assert result["metrics"]["verdict"] == "FAIL"
    assert "AUTH-OPEN" in result["answer"] or "certificate" in result["answer"].lower()


def test_aj18991_uses_case_rca() -> None:
    result = route("Why did AJ18991 return HTTP 500?")
    assert result["source"] == "handler:case_rca"
    assert result["metrics"]["case_id"] == "AJ18991"
    assert "CERT-MISMATCH" in result["metrics"]["fired"]
    assert "APP-CODE-500" in result["metrics"]["skipped"]
    assert "28.4" not in result["answer"] or result["metrics"]["case_id"] == "AJ18991"
    assert "George Jetson" in result["answer"]
    assert "500" in result["answer"]


def test_mttr_uses_perf_handler() -> None:
    result = route("What is gross MTTR in this fixture?")
    assert result["source"] == "handler:perf_metrics"
    assert result["metrics"]["gross_mttr_hours"] == 34.2
    assert result["metrics"]["eng_assist_hours"] == 9.4
    assert "34.2" in result["answer"]
    assert "not GaussIQ published" in result["answer"]


def test_why_mttr_cites_fired_rules() -> None:
    result = route("Why is MTTR high?")
    assert result["source"] == "handler:why_mttr"
    assert result["metrics"]["gross_mttr_hours"] == 34.2
    assert result["metrics"]["delta_hours"] == 3.2
    assert "CERT-MISMATCH" in result["metrics"]["fired"]
    assert "CONNECTOR-LAG" in result["metrics"]["fired"]
    assert "not live production" in result["answer"]


def test_api_smoke_on_case_plan() -> None:
    result = route("Run API smoke on case-plan APIs")
    assert result["route"] == "run_suite"
    assert result["metrics"]["suite"] == "smoke"
    assert result["metrics"]["layer"] == "api"
    assert result["metrics"]["verdict"] == "PASS"


def test_skills_handler() -> None:
    result = route("Which skill gaps are high impact?")
    assert result["source"] == "handler:skills_gaps"
    assert result["metrics"]["high_impact_gaps"] == 2
    assert "TLS" in result["answer"] or "certificate" in result["answer"].lower()


def test_security_handler() -> None:
    result = route("any security issues?")
    assert result["source"] == "handler:security_rca"
    assert "AUTH-OPEN" in result["metrics"]["fired"]
    assert "SECRET-IN-LOG" in result["metrics"]["fired"]
    assert "TLS-MISSING" in result["metrics"]["skipped"]
    assert "LIVE-SCAN" in result["metrics"]["skipped"]


def test_smoke_suite_passes() -> None:
    result = route("Run smoke suite")
    assert result["route"] == "run_suite"
    assert result["source_kind"] == "suite"
    assert result["metrics"]["verdict"] == "PASS"
    assert result["metrics"]["failed"] == 0
    assert result["metrics"]["total"] == 3


def test_sanity_suite_fails_on_connector_and_cert() -> None:
    result = route("Run sanity suite")
    assert result["metrics"]["verdict"] == "FAIL"
    ids = result["metrics"]["failed_ids"]
    assert "test_signal_connector_ready" in ids
    assert "test_case_aj18991_cert_plan" in ids


def test_login_requires_named_creds() -> None:
    missing = route("test the login")
    assert missing["metrics"]["ok"] is False
    assert "will not invent credentials" in missing["answer"]
    ok = route("Test the login with username as giquser and password as giqpass")
    assert ok["metrics"]["ok"] is True
    assert ok["metrics"]["status"] == 200
    bad = route("Test the login with username as admin and password as admin")
    assert bad["metrics"]["status"] == 401


def test_kb_case_intelligence() -> None:
    result = route("What is Case Intelligence?")
    assert result["source"].startswith("kb:")
    assert result["metrics"] is None
    assert "paraphrased" in result["answer"].lower() or "public" in result["answer"].lower()


def test_canned_questions_take_distinct_sources() -> None:
    sources = [route(q)["source"] for q in CANNED_QUESTIONS]
    assert len(set(sources)) == len(CANNED_QUESTIONS)


def test_no_model_flag() -> None:
    result = route("What is net MTTR?")
    assert result["model_available"] is False
