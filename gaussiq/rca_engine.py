"""Deterministic RCA over GaussIQ-lab fixtures.

Named rules fire or skip. A model never chooses which rule fires and never
invents a number. HTTP 500 is a symptom — CERT-MISMATCH vs APP-CODE-500.
"""

from __future__ import annotations

from typing import Any

from gaussiq.load import load


def memory_pct(service: dict[str, Any]) -> float:
    limit = float(service.get("memory_limit_mib") or 0)
    if not limit:
        return 0.0
    return round(100.0 * float(service.get("memory_mib") or 0) / limit, 1)


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


def evaluate(
    services: dict[str, Any] | None = None,
    cases: dict[str, Any] | None = None,
    skills: dict[str, Any] | None = None,
) -> dict[str, Any]:
    services = services or load("services.json")
    cases = cases or load("cases.json")
    skills = skills or load("skills.json")
    rows: list[dict[str, Any]] = services["services"]
    items: list[dict[str, Any]] = cases["items"]
    gaps: list[dict[str, Any]] = skills["items"]

    fired: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def skip(rule_id: str, why: str) -> None:
        skipped.append({"id": rule_id, "why": why})

    aj = next((c for c in items if c["id"] == "AJ18991"), None)
    cert = bool(
        aj
        and "cert" in (aj.get("likely_cause") or "").lower()
        and "500" in (aj.get("symptom") or "")
    )
    if cert and aj:
        fired.append(
            _card(
                "CERT-MISMATCH",
                "HIGH",
                aj["component"],
                "AJ18991 HTTP 500 is a certificate SAN mismatch",
                aj["symptom"]
                + " on "
                + aj["product"]
                + " (customer "
                + aj["customer"]
                + ", "
                + aj["org"]
                + ").",
                aj["likely_cause"]
                + ". Similar DEMO tickets "
                + ", ".join(aj.get("similar") or [])
                + " point at the same cert path. Discarded KB: "
                + "; ".join(aj.get("kb_discarded") or [])
                + ".",
                "Reissue the sandbox certificate with the matching SAN, then re-run the migration. "
                "Do not patch the wizard for a generic 500.",
                [
                    f"id={aj['id']} severity={aj['severity']} region={aj['region']}",
                    f"component={aj['component']}",
                    "similar=" + ", ".join(aj.get("similar") or []),
                ],
            )
        )
        skip(
            "APP-CODE-500",
            "Checked — not the cause. The 500 is the TLS SAN mismatch on AJ18991, not a defect in the SFM wizard code.",
        )
    else:
        skip("CERT-MISMATCH", "No AJ18991 cert-mismatch case in this snapshot.")
        http500 = [c for c in items if "500" in (c.get("symptom") or "")]
        if http500:
            fired.append(
                _card(
                    "APP-CODE-500",
                    "HIGH",
                    http500[0].get("component") or "unknown",
                    "HTTP 500 without a cert mismatch",
                    http500[0]["symptom"],
                    "No certificate SAN evidence in this snapshot, so the 500 stays an application error until more evidence arrives.",
                    "Collect the job record and HAR before guessing a code fix.",
                    [http500[0]["id"]],
                )
            )
        else:
            skip("APP-CODE-500", "No HTTP 500 case in this snapshot.")

    lag = [
        s
        for s in rows
        if not s.get("ready") or str(s.get("status") or "").lower() not in {"running", "succeeded"}
    ]
    if lag:
        fired.append(
            _card(
                "CONNECTOR-LAG",
                "HIGH",
                lag[0]["id"],
                "Signal connector is not running",
                f"{len(lag)} of {len(rows)} GaussIQ 1.0 demo services are not ready: "
                + ", ".join(s["id"] for s in lag)
                + ".",
                "Ticketing signals are not landing, so Case Intelligence similar-case evidence goes stale (see AJ18802).",
                "Restore signal-connector before trusting empty case plans. Empty evidence is not a missing KB article.",
                [
                    f"{s['id']} status={s['status']} restarts={s['restarts']} last_reason={s.get('last_reason') or '-'}"
                    for s in lag
                ],
            )
        )
    else:
        skip("CONNECTOR-LAG", "Every demo service is Running and ready.")

    tls_gap = next(
        (g for g in gaps if "certificate" in g["skill"].lower() and g["coverage"] == 0),
        None,
    )
    if tls_gap:
        fired.append(
            _card(
                "SKILL-GAP-TLS",
                "HIGH",
                "skills-intel-api",
                "No one on this shift has recent cert troubleshooting",
                f"{tls_gap['skill']} demand={tls_gap['demand']} coverage={tls_gap['coverage']} recency_days={tls_gap['recency_days']}.",
                tls_gap["why"],
                "Pair AJ18991 with someone who has closed a cert case, or treat this as a training gap. Do not auto-assign from a model.",
                [tls_gap["why"]],
            )
        )
    else:
        skip("SKILL-GAP-TLS", "TLS / certificate coverage is present in this snapshot.")

    pressure = [
        s
        for s in rows
        if memory_pct(s) >= 90
        or "oom" in str(s.get("last_reason") or "").lower()
        or "workingsethigh" in str(s.get("last_reason") or "").lower()
    ]
    if pressure:
        row = pressure[0]
        pct = memory_pct(row)
        fired.append(
            _card(
                "MEM-PRESSURE",
                "HIGH",
                row["id"],
                "Working set near the memory limit",
                f"`{row['id']}` memory {row['memory_mib']}/{row['memory_limit_mib']} MiB "
                f"({pct}% of its limit), restarts={row.get('restarts') or 0}, "
                f"last_reason={row.get('last_reason') or '-'}.",
                "Recommendation engine is holding a large evidence working set. "
                "This is memory pressure, not CPU saturation and not the crash-looping connector.",
                "Raise the rec-engine memory limit or shrink the evidence pack before expecting fast RCA. "
                "Do not scale CPU for a memory finding.",
                [
                    f"{s['id']} mem={s['memory_mib']}/{s['memory_limit_mib']} MiB "
                    f"({memory_pct(s)}%) cpu={s['cpu_pct']}% restarts={s.get('restarts') or 0}"
                    for s in pressure
                ],
            )
        )
    else:
        skip(
            "MEM-PRESSURE",
            "No sampled GaussIQ 1.0 service is at ≥90% of its memory limit.",
        )

    hot = [s for s in rows if float(s.get("cpu_pct") or 0) >= 80]
    if hot:
        fired.append(
            _card(
                "CPU-HOT",
                "HIGH",
                hot[0]["id"],
                "CPU at or above 80% of limit",
                f"`{hot[0]['id']}` CPU {hot[0]['cpu_pct']}% of its limit.",
                "Sustained CPU near the limit throttles recommendations.",
                "Raise the CPU limit or add a replica. Percentages are of each service limit, not the node.",
                [f"{s['id']} {s['cpu_pct']}%" for s in hot],
            )
        )
    else:
        skip(
            "CPU-HOT",
            "Checked — not the cause. No sampled GaussIQ 1.0 service is at ≥80% of its CPU limit. "
            "rec-engine is memory-bound (MEM-PRESSURE), not CPU-bound.",
        )

    insights = next((s for s in rows if s["id"] == "insights-api"), None)
    if insights and insights.get("ready") and insights.get("status") == "Running":
        skip(
            "INSIGHTS-DOWN",
            "Checked — not the cause. Management Insights API is Running. Stale case plans come from the connector, not Insights being down.",
        )
    elif insights:
        fired.append(
            _card(
                "INSIGHTS-DOWN",
                "HIGH",
                "insights-api",
                "Management Insights API is not ready",
                f"insights-api status={insights.get('status')} ready={insights.get('ready')}.",
                "Leader MTTR tiles cannot refresh while Insights is down.",
                "Restore insights-api, then re-read the performance fixture.",
                [f"status={insights.get('status')}"],
            )
        )
    else:
        skip("INSIGHTS-DOWN", "No insights-api row in this snapshot.")

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "WARN": 3, "INFO": 4}
    fired.sort(key=lambda row: (order.get(row["severity"], 9), row["id"]))
    counts: dict[str, int] = {}
    for row in fired:
        counts[row["severity"]] = counts.get(row["severity"], 0) + 1

    unhealthy = len(lag)
    return {
        "principle": (
            "HTTP 500 is a symptom. Name the component. CERT-MISMATCH fires when the "
            "sandbox certificate SAN does not match; APP-CODE-500 is skipped in that case. "
            "A skipped rule is part of the diagnosis."
        ),
        "fired": fired,
        "skipped": skipped,
        "counts": counts,
        "service_count": len(rows),
        "unhealthy": unhealthy,
        "skipped_heading": "Checked — not the cause",
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "Deterministic RCA — rules first. No model chose a tool or a number.",
        report["principle"],
        "",
        f"Fired ({len(report['fired'])}):",
    ]
    for row in report["fired"]:
        lines.append(
            f"[{row['severity']}] {row['id']} · {row['component']} — {row['title']}"
        )
        lines.append(f"  Symptom: {row['observation']}")
        for item in row.get("evidence") or []:
            lines.append(f"    - {item}")
        lines.append(f"  Cause: {row['cause']}")
        lines.append(f"  Fix: {row['recommendation']}")
        lines.append("")
    lines.append(report.get("skipped_heading") or "Checked — not the cause")
    for row in report["skipped"]:
        lines.append(f"- {row['id']}: {row['why']}")
    return "\n".join(lines).strip()
