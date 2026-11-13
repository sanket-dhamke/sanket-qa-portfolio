"""Deterministic security RCA over the mocked GaussIQ-lab fixture.

No live scan. No exploit payloads. Secrets are already redacted.
"""

from __future__ import annotations

from typing import Any

from gaussiq.load import load


def _card(
    rule_id: str,
    severity: str,
    component: str,
    title: str,
    observation: str,
    cause: str,
    recommendation: str,
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "severity": severity,
        "component": component,
        "title": title,
        "observation": observation,
        "symptom": observation,
        "cause": cause,
        "likely_cause": cause,
        "recommendation": recommendation,
        "suggested": recommendation,
        "fix": recommendation,
        "evidence": evidence,
    }


def evaluate(security: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = security or load("security.json")
    api = snap.get("case_api") or {}
    secret = snap.get("secret_in_log") or {}

    fired: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def skip(rule_id: str, why: str) -> None:
        skipped.append({"id": rule_id, "why": why})

    if not api.get("auth_required"):
        fired.append(
            _card(
                "AUTH-OPEN",
                "HIGH",
                "case-intel-api",
                "Case Intelligence API is reachable without signing in",
                "Mocked case-intel-api GraphQL answered without a session cookie.",
                "Auth is not required on this demo endpoint. Anyone who can reach it can read case plans. This is a fixture finding, not a live exploit.",
                "Require a session on case-intel-api before serving case plans. A 200 from /health is not proof that auth is on.",
                [
                    f"url={api.get('url')}",
                    f"anonymous_graphql={api.get('anonymous_graphql')}",
                    "source=gaussiq/fixtures/security.json",
                ],
            )
        )
    else:
        skip("AUTH-OPEN", "case-intel-api in this snapshot requires a session.")

    if secret.get("token_like"):
        line = str(secret.get("line") or "Authorization: Bearer giq_lab_****redacted****")
        fired.append(
            _card(
                "SECRET-IN-LOG",
                "MEDIUM",
                str(secret.get("component") or "rec-engine"),
                "Token-like value in a service log (redacted)",
                f"A token-like value appeared in `{secret.get('component')}` logs. Shown redacted: {line}.",
                "The recommendation engine echoed an Authorization header. The raw value is never shown in this lab.",
                "Stop logging Authorization headers. Rotate the lab token.",
                [line, "source=gaussiq/fixtures/security.json"],
            )
        )
    else:
        skip("SECRET-IN-LOG", "No token-like log line in this snapshot.")

    if api.get("tls"):
        skip(
            "TLS-MISSING",
            "Checked — not the cause. case-intel-api already has TLS in this fixture. Open GraphQL is an auth gap, not a missing certificate on GaussIQ itself. AJ18991 is a customer sandbox SAN mismatch, a different finding.",
        )
    else:
        fired.append(
            _card(
                "TLS-MISSING",
                "HIGH",
                "case-intel-api",
                "TLS is off on Case Intelligence API",
                "case-intel-api tls=false in this snapshot.",
                "The demo API is serving case plans in cleartext.",
                "Turn TLS on. This is separate from the AJ18991 customer cert SAN mismatch.",
                ["tls=false"],
            )
        )

    if snap.get("live_scan"):
        fired.append(
            _card(
                "LIVE-SCAN",
                "WARN",
                "lab",
                "Live scan flag is on",
                "The security fixture asked for a live scan.",
                "This lab must not scan the internet.",
                "Keep live_scan=false. Findings come only from the fixture.",
                ["live_scan=true"],
            )
        )
    else:
        skip(
            "LIVE-SCAN",
            "Checked — not the cause. This lab never scans the internet. Findings come only from the security fixture.",
        )

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "WARN": 3, "INFO": 4}
    fired.sort(key=lambda row: (order.get(row["severity"], 9), row["id"]))
    counts: dict[str, int] = {}
    for row in fired:
        counts[row["severity"]] = counts.get(row["severity"], 0) + 1

    return {
        "principle": (
            "Security findings are fixture-only. No live scan, no exploit. "
            "AUTH-OPEN is missing login, not missing TLS. Secrets in logs are shown redacted."
        ),
        "fired": fired,
        "skipped": skipped,
        "counts": counts,
        "skipped_heading": "Checked — not the cause",
    }
