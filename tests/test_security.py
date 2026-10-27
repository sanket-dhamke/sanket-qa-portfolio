"""Security RCA is fixture rules — the model never invents findings or CVEs."""

from __future__ import annotations

from agent.executor import app_health, compute_app_health, load
from agent.rca_engine import evaluate as evaluate_rca
from agent.router import route
from agent.security_engine import evaluate, format_report


def test_auth_open_secret_and_dep_from_fixture() -> None:
    report = evaluate()
    fired = {row["id"]: row for row in report["fired"]}
    skipped = {row["id"]: row["why"] for row in report["skipped"]}
    assert "AUTH-OPEN" in fired
    assert fired["AUTH-OPEN"]["severity"] == "HIGH"
    assert "SECRET-IN-LOG" in fired
    assert "****redacted****" in fired["SECRET-IN-LOG"]["observation"]
    assert "DEP-CVE" in fired
    assert "lab_issue" in fired["DEP-CVE"]["cause"]
    assert "TLS" in skipped
    assert "LIVE-SCAN" in skipped
    assert "Checked — not the cause" in skipped["TLS"]
    text = format_report(report)
    assert "Checked — not the cause" in text
    assert "not fired" not in text
    assert "HTTP 000" not in text
    assert "CVE-20" not in text
    assert "agent/fixtures/security.json" in text


def test_any_security_issues_uses_handler() -> None:
    result = route("any security issues?")
    assert result["source"] == "handler:security_rca"
    assert result["ui"] == "security"
    assert "AUTH-OPEN" in result["metrics"]["fired"]
    assert "SECRET-IN-LOG" in result["metrics"]["fired"]
    assert "TLS" in result["metrics"]["skipped"]
    assert "AUTH-OPEN" in result["answer"]
    assert "Checked — not the cause" in result["answer"]
    assert "agent/fixtures/security.json" in result["answer"]
    assert "not fired" not in result["answer"]
    assert "HTTP 000" not in result["answer"]
    assert "CVE-20" not in result["answer"]


def test_why_gms_exposed_is_auth_open() -> None:
    result = route("why is GMS exposed?")
    assert result["source"] == "handler:security_rca"
    assert "AUTH-OPEN" in result["answer"]
    assert "session" in result["answer"].lower()


def test_login_still_wins_over_auth_substring() -> None:
    result = route("Test the login with username as emuser and password as empass")
    assert result["source"] == "handler:login_api"


def test_auth_open_keeps_app_health_degraded_not_critical() -> None:
    health = app_health()
    assert health["health"] == "DEGRADED"
    assert "AUTH-OPEN" in " ".join(health["health_reasons"])
    assert health["snapshot"]["auth_open"] is True
    assert health["smoke"]["verdict"] == "PASS"
    cluster = load("cluster.json")
    rca = evaluate_rca(cluster=cluster)
    sec = evaluate()
    smoke_fail = {"verdict": "FAIL", "failed": 1, "passed": 0, "total": 1}
    critical = compute_app_health(
        cluster, rca, smoke_fail, {"verdict": "PASS"}, security_report=sec
    )
    assert critical["health"] == "CRITICAL"
    assert critical["auth_open"] is True
