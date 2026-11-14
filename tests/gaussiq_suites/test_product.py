"""Golden-case product suite: ingest fixtures, assert Case Intelligence outcomes."""

from __future__ import annotations

import pytest

from gaussiq.load import load
from gaussiq.rca_engine import evaluate

pytestmark = pytest.mark.product


def _aj18991() -> dict:
    return next(c for c in load("cases.json")["items"] if c["id"] == "AJ18991")


def test_golden_aj18991_rca() -> None:
    aj = _aj18991()
    report = evaluate()
    fired = {row["id"]: row for row in report["fired"]}
    skipped = {row["id"]: row["why"] for row in report["skipped"]}
    assert "500" in aj["symptom"]
    assert "cert" in aj["likely_cause"].lower()
    assert "CERT-MISMATCH" in fired
    assert "APP-CODE-500" in skipped
    assert "not the cause" in skipped["APP-CODE-500"].lower()


def test_golden_aj18991_assignment() -> None:
    gaps = load("skills.json")["items"]
    tls = next(g for g in gaps if "certificate" in g["skill"].lower())
    assert tls["demand"] == "High"
    assert int(tls.get("people") or 0) == 0
    assert tls["coverage"] == 0


def test_golden_aj18991_details() -> None:
    aj = _aj18991()
    assert aj["id"] == "AJ18991"
    assert aj["customer"] == "George Jetson"
    assert aj["org"] == "Rocket Pack Express"
    assert aj["product"] == "Spaceley Sprocket migration tool"
    assert aj["severity"] == "Business Critical"
    assert aj["region"] == "EMEA"


def test_golden_aj18991_similar() -> None:
    aj = _aj18991()
    assert aj["similar"] == ["AJ18268", "AJ18600"]
