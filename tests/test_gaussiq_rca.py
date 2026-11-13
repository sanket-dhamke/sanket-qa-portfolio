"""Named rules fire or skip on the GaussIQ demo fixtures."""

from __future__ import annotations

from gaussiq.handlers import compute_app_health
from gaussiq.rca_engine import evaluate
from gaussiq.security_engine import evaluate as evaluate_security


def test_cert_mismatch_fires_app_code_skipped() -> None:
    report = evaluate()
    fired = {row["id"] for row in report["fired"]}
    skipped = {row["id"] for row in report["skipped"]}
    assert "CERT-MISMATCH" in fired
    assert "APP-CODE-500" in skipped
    assert "CONNECTOR-LAG" in fired
    assert "SKILL-GAP-TLS" in fired
    assert "CPU-HOT" in skipped
    assert "INSIGHTS-DOWN" in skipped
    assert "not fired" not in report.get("skipped_heading", "").lower()
    assert "Checked — not the cause" in report["skipped_heading"]


def test_health_is_degraded_not_critical() -> None:
    snapshot = compute_app_health()
    assert snapshot["health"] == "DEGRADED"
    assert snapshot["smokePassed"] is True
    assert snapshot["crashloop"] is True
    assert snapshot["authOpen"] is True


def test_security_auth_open_not_tls() -> None:
    report = evaluate_security()
    fired = {row["id"] for row in report["fired"]}
    skipped = {row["id"]: row["why"] for row in report["skipped"]}
    assert "AUTH-OPEN" in fired
    assert "SECRET-IN-LOG" in fired
    assert "TLS-MISSING" in skipped
    assert "auth gap" in skipped["TLS-MISSING"].lower()
    secret = next(r for r in report["fired"] if r["id"] == "SECRET-IN-LOG")
    blob = " ".join(secret["evidence"])
    assert "redacted" in blob.lower()
    assert "giq_lab_****redacted****" in blob
