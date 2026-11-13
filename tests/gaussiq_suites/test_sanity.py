"""Sanity: fixture RCA for AJ18991 and the signal connector."""

from __future__ import annotations

import pytest

from gaussiq.load import load
from gaussiq.rca_engine import evaluate

pytestmark = pytest.mark.sanity


def test_signal_connector_not_ready_in_fixture() -> None:
    row = next(s for s in load("services.json")["services"] if s["id"] == "signal-connector")
    assert row["status"] == "CrashLoopBackOff"
    assert row["ready"] is False
    assert row["restarts"] == 5


def test_case_aj18991_cert_mismatch_fires() -> None:
    report = evaluate()
    fired = {row["id"]: row for row in report["fired"]}
    skipped = {row["id"]: row["why"] for row in report["skipped"]}
    assert "CERT-MISMATCH" in fired
    assert "HTTP 500" in fired["CERT-MISMATCH"]["observation"]
    assert "SAN" in fired["CERT-MISMATCH"]["cause"] or "cert" in fired["CERT-MISMATCH"]["cause"].lower()
    assert "APP-CODE-500" in skipped
    assert "not the cause" in skipped["APP-CODE-500"].lower()


def test_mttr_snapshot_present() -> None:
    perf = load("performance.json")
    assert perf["gross_mttr_hours"] == 34.2
    assert perf["net_mttr_hours"] == 25.1
    assert perf["eng_assist_hours"] == 9.4


def test_skills_gap_tls() -> None:
    gaps = load("skills.json")["items"]
    tls = next(g for g in gaps if "certificate" in g["skill"].lower())
    assert tls["coverage"] == 0
    assert tls["demand"] == "High"
