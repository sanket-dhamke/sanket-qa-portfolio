"""Regression extras: security fixtures + eng assist."""

from __future__ import annotations

import pytest

from gaussiq.load import load
from gaussiq.security_engine import evaluate

pytestmark = pytest.mark.regression


def test_case_api_auth_open_in_fixture() -> None:
    report = evaluate()
    fired = {row["id"]: row for row in report["fired"]}
    skipped = {row["id"]: row["why"] for row in report["skipped"]}
    assert "AUTH-OPEN" in fired
    assert fired["AUTH-OPEN"]["component"] == "case-intel-api"
    assert "TLS-MISSING" in skipped
    assert "LIVE-SCAN" in skipped


def test_secret_in_rec_engine_logs_redacted() -> None:
    report = evaluate()
    fired = {row["id"]: row for row in report["fired"]}
    assert "SECRET-IN-LOG" in fired
    blob = " ".join(fired["SECRET-IN-LOG"].get("evidence") or [])
    assert "redacted" in blob.lower()
    assert "giq_lab_****redacted****" in blob


def test_eng_assist_hours() -> None:
    perf = load("performance.json")
    assert perf["eng_assist_hours"] == 9.4
    assert "original" in perf["note"].lower()
