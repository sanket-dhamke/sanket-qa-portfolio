"""App health, smoke, and sanity must tell the same DataHub lab story."""

from __future__ import annotations

from agent.executor import app_health, compute_app_health, load, run_suite
from agent.rca_engine import evaluate
from agent.router import route


def test_live_fixture_is_degraded_with_failing_sanity() -> None:
    health = app_health()
    assert health["health"] == "DEGRADED"
    assert health["smoke"]["verdict"] == "PASS"
    assert health["sanity"]["verdict"] == "FAIL"
    assert "OOMKilled" in " ".join(health["health_reasons"]) or "CrashLoopBackOff" in " ".join(
        health["health_reasons"]
    )
    rca = health["sanity_report"]["rcas"][0]
    blob = " ".join(
        [str(rca.get(k) or "") for k in ("symptom", "cause", "fix")]
        + list(rca.get("evidence") or [])
    )
    assert "mae-consumer" in blob.lower() or "OOM" in blob
    assert health["snapshot"]["oom"] is True
    assert health["snapshot"]["crashloop"] is True


def test_critical_requires_smoke_fail() -> None:
    cluster = load("cluster.json")
    report = evaluate(cluster=cluster)
    smoke_fail = {"verdict": "FAIL", "failed": 1, "passed": 0, "total": 1}
    sanity_fail = {"verdict": "FAIL", "failed": 1, "passed": 0, "total": 1}
    critical = compute_app_health(cluster, report, smoke_fail, sanity_fail)
    assert critical["health"] == "CRITICAL"
    smoke_pass = {"verdict": "PASS", "failed": 0, "passed": 1, "total": 1}
    degraded = compute_app_health(cluster, report, smoke_pass, sanity_fail)
    assert degraded["health"] == "DEGRADED"
    assert not (degraded["health"] == "CRITICAL" and smoke_pass["verdict"] == "PASS")


def test_suites_are_not_both_green_on_this_fixture() -> None:
    smoke = run_suite("smoke")
    sanity = run_suite("sanity")
    assert smoke["verdict"] == "PASS"
    assert sanity["verdict"] == "FAIL"
    failed_ids = sanity["failed_ids"]
    assert "api.mae_search_index" in failed_ids
    assert "ui.search_datasets" in failed_ids


def test_chat_current_state_uses_degraded() -> None:
    result = route("What is the current state of the application?")
    assert result["metrics"]["health"] == "DEGRADED"
    assert result["metrics"]["smoke_verdict"] == "PASS"
    assert result["metrics"]["sanity_verdict"] == "FAIL"
    assert "DEGRADED" in result["answer"]
    assert "unknown" not in result["answer"].lower()
