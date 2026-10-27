"""Security smoke: fixture is mocked, TLS is on, secrets already redacted."""

from __future__ import annotations

import pytest

from agent.executor import load

pytestmark = pytest.mark.smoke


def test_security_fixture_is_mocked_not_a_live_scan() -> None:
    snap = load("security.json")
    assert "not a live scan" in snap["note"].lower()
    assert snap["gms"]["auth_required"] is False
    assert "****redacted****" in snap["secret_in_log"]["line"]
    assert snap["dependency"].get("cve") in (None, "")


def test_gms_tls_is_on_in_the_fixture() -> None:
    snap = load("security.json")
    assert snap["gms"]["tls"] is True
