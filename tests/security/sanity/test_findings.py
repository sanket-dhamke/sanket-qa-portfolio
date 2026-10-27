"""Security sanity: AUTH-OPEN is the finding; TLS is not the cause."""

from __future__ import annotations

import pytest

from agent.executor import load
from agent.security_engine import evaluate, format_report

pytestmark = pytest.mark.sanity


def test_auth_open_fires_from_the_fixture() -> None:
    report = evaluate()
    fired = {row["id"] for row in report["fired"]}
    assert "AUTH-OPEN" in fired


def test_tls_is_checked_not_the_cause() -> None:
    report = evaluate()
    skipped = {row["id"]: row["why"] for row in report["skipped"]}
    assert "TLS" in skipped
    assert "Checked — not the cause" in skipped["TLS"]
    assert "not fired" not in format_report(report)


@pytest.mark.lab_issue
def test_gms_rejects_anonymous_graphql_and_rest() -> None:
    snap = load("security.json")
    assert snap["gms"]["auth_required"] is True, (
        "datahub-gms answered without a session (AUTH-OPEN). "
        "App health is DEGRADED. This is a mocked fixture finding, not a live exploit."
    )
