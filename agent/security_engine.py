"""Deterministic security RCA over a mocked DataHub fixture.

Rules produce severity, observation, cause, and fix. A model never chooses
which rule fires, never invents a CVE number, and never runs a live scan.
No exploit payloads. Secrets are already redacted in the fixture.
"""

from __future__ import annotations

from typing import Any

from agent.executor import load


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
    gms = snap.get("gms") or {}
    secret = snap.get("secret_in_log") or {}
    dep = snap.get("dependency") or {}

    fired: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def skip(rule_id: str, why: str) -> None:
        skipped.append({"id": rule_id, "why": why})

    if not gms.get("auth_required"):
        fired.append(
            _card(
                "AUTH-OPEN",
                "HIGH",
                "datahub-gms",
                "GMS is reachable without signing in",
                "Mocked datahub-gms GraphQL and REST answered without a session cookie.",
                "Auth is not required on this lab GMS endpoint. Anyone who can reach the service can read metadata. This is a fixture finding, not a live exploit.",
                "Require a session (PLAY_SESSION) on GMS before serving metadata. A 200 from /health is not proof that auth is on.",
                [
                    f"url={gms.get('url')}",
                    f"anonymous_graphql={gms.get('anonymous_graphql')}",
                    f"anonymous_rest={gms.get('anonymous_rest')}",
                    "source=agent/fixtures/security.json",
                ],
            )
        )
    else:
        skip("AUTH-OPEN", "GMS in this snapshot requires a session.")

    if secret.get("token_like"):
        line = str(secret.get("line") or "PLAY_SESSION=dh_lab_****redacted****")
        fired.append(
            _card(
                "SECRET-IN-LOG",
                "MEDIUM",
                str(secret.get("component") or "datahub-frontend"),
                "Token-like value in a pod log (redacted)",
                f"A session cookie appeared in `{secret.get('component')}` logs. Shown redacted: {line}.",
                "The lab frontend echoed a PLAY_SESSION cookie into logs. The raw value is never shown in this console.",
                "Stop logging Authorization and session headers. Rotate the lab session cookie.",
                [line, "source=agent/fixtures/security.json"],
            )
        )
    else:
        skip("SECRET-IN-LOG", "No token-like log line in this snapshot.")

    if dep.get("advisory"):
        cited = str(dep.get("cited_as") or "lab_issue")
        fired.append(
            _card(
                "DEP-CVE",
                "WARN",
                str(dep.get("package") or "dependency"),
                "Mocked dependency advisory (lab_issue)",
                f"{dep.get('package')}: {dep.get('advisory')}",
                f"Cited as `{cited}` in the security fixture. Not a live scan. No CVE number is invented.",
                "Track the advisory in the lab catalog. Do not treat this as a production CVE match.",
                [
                    f"package={dep.get('package')}",
                    f"cited_as={cited}",
                    "cve=none (not invented)",
                    "source=agent/fixtures/security.json",
                ],
            )
        )
    else:
        skip("DEP-CVE", "No mocked advisory in this snapshot.")

    if gms.get("tls"):
        skip(
            "TLS",
            "Checked — not the cause. datahub-gms already has TLS in this fixture. Open GMS is an auth gap, not a missing certificate.",
        )
    else:
        fired.append(
            _card(
                "TLS",
                "HIGH",
                "datahub-gms",
                "TLS is off on GMS",
                "The security fixture has tls=false on datahub-gms.",
                "Traffic to GMS is not encrypted in this snapshot.",
                "Serve GMS over TLS. This lab still would not scan the public internet.",
                ["tls=false", "source=agent/fixtures/security.json"],
            )
        )

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
            "Security rules read a mocked DataHub fixture. The model does not invent "
            "findings, CVE numbers, or exploit steps. AUTH-OPEN means GMS answered "
            "without a session. Secrets in logs are shown redacted. No live scan."
        ),
        "skipped_heading": "Checked — not the cause",
        "fired": fired,
        "skipped": skipped,
        "counts": counts,
        "kind": "security",
    }


def format_report(report: dict[str, Any]) -> str:
    heading = report.get("skipped_heading") or "Checked — not the cause"
    lines = [
        "Deterministic security RCA — rules first. No model chose a finding or a CVE.",
        report["principle"],
        "",
        f"Fired ({len(report['fired'])}):",
    ]
    for row in report["fired"]:
        lines.append(
            f"[{row['severity']}] {row['id']} · {row['component']} — {row['title']}"
        )
        lines.append(f"  Observation: {row['observation']}")
        for item in row.get("evidence") or []:
            lines.append(f"    - {item}")
        lines.append(f"  Cause: {row['cause']}")
        lines.append(f"  Fix: {row['recommendation']}")
        lines.append("")
    lines.append(f"{heading}:")
    for row in report["skipped"]:
        lines.append(f"- {row['id']}: {row['why']}")
    lines.append("")
    lines.append("Cited source: agent/fixtures/security.json · agent/security_engine.py")
    return "\n".join(lines).strip()
