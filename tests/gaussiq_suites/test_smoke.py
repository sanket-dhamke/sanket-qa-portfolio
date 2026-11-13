"""Smoke: GaussIQ 1.0 demo services that should stay green."""

from __future__ import annotations

import pytest

from gaussiq.load import load

pytestmark = pytest.mark.smoke


def _by_id(sid: str) -> dict:
    rows = load("services.json")["services"]
    return next(s for s in rows if s["id"] == sid)


def test_case_intel_health() -> None:
    row = _by_id("case-intel-api")
    assert row["status"] == "Running"
    assert row["ready"] is True


def test_skills_intel_health() -> None:
    row = _by_id("skills-intel-api")
    assert row["status"] == "Running"
    assert row["ready"] is True


def test_insights_health() -> None:
    row = _by_id("insights-api")
    assert row["status"] == "Running"
    assert row["ready"] is True
