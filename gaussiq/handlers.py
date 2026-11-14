"""Handlers read fixtures only. A model never invents a number."""

from __future__ import annotations

import re
from typing import Any

from gaussiq.load import load
from gaussiq import rca_engine, security_engine
from gaussiq.rca_engine import memory_pct

YES = re.compile(
    r"^\s*(y|yes|yeah|yep|ok|okay|sure|do it|go ahead|please run|run it|run them|run regression)\b",
    re.I,
)
NO = re.compile(r"^\s*(n|no|nope|skip|not now|later|don't|dont)\b", re.I)

SUITE_FOOTNOTE = "Catalog replay — not a live pytest run."
ALLURE_LAYERS = ("api", "ui")
ALLURE_SUITES = ("smoke", "sanity", "regression", "product")


def report_layer(layer: str | None) -> str:
    """Committed Allure slices are api|ui, matching DataHub."""
    if layer == "ui":
        return "ui"
    return "api"


def allure_href(layer: str | None, suite: str | None) -> str | None:
    dest = report_layer(layer)
    if dest not in ALLURE_LAYERS:
        return None
    if suite in ALLURE_SUITES:
        ver = "a3" if suite == "product" else "a2"
        return f"reports/allure-gaussiq-{dest}-{suite}/index.html?v={ver}"
    return None


def allure_links(summary: dict[str, Any]) -> list[dict[str, str]]:
    layers: list[str] = []
    if summary.get("layer"):
        layers = [str(summary["layer"])]
    else:
        for case in summary.get("cases") or []:
            layer = case.get("layer")
            if layer and layer not in layers:
                layers.append(str(layer))
    if not layers:
        layers = ["api"]
    suite = summary.get("suite")
    present: list[str] = []
    for layer in layers:
        dest = report_layer(layer)
        if dest not in present:
            present.append(dest)
    links = []
    for layer in present:
        href = allure_href(layer, suite)
        if not href:
            continue
        label = "Open Allure report"
        if len(present) > 1:
            label = f"Open {layer.upper()} Allure report"
        links.append({"href": href, "label": label, "layer": layer, "suite": str(suite or "")})
    return links


def caveat() -> str:
    return (
        "Keyword/rule router. Numbers come from checked-in fixtures, not a model. "
        "Fictional GaussIQ 1.0 demo tenant — not a live product. Not affiliated with GaussIQ."
    )


def _services() -> dict[str, Any]:
    return load("services.json")


def _cases() -> dict[str, Any]:
    return load("cases.json")


def _perf() -> dict[str, Any]:
    return load("performance.json")


def _skills() -> dict[str, Any]:
    return load("skills.json")


def _users() -> dict[str, Any]:
    return load("users.json")


def _kb() -> dict[str, Any]:
    return load("kb.json")


def _suites() -> dict[str, Any]:
    return load("suites.json")


def _security() -> dict[str, Any]:
    return load("security.json")


def _evidence() -> dict[str, Any]:
    return load("evidence.json")


def rec_engine_saturated(services: dict[str, Any] | None = None) -> bool:
    rows = (services or _services())["services"]
    rec = next((s for s in rows if s["id"] == "rec-engine"), None)
    if not rec:
        return False
    return memory_pct(rec) >= 90


def _evidence_rung(session: dict[str, Any] | None) -> int:
    pack = _evidence()
    ladder = pack["ladder"]
    rung = int((session or {}).get("evidence_rung") or 0)
    return max(0, min(rung, len(ladder) - 1))


def _format_evidence_row(row: dict[str, Any], saturated: bool) -> list[str]:
    sat = "yes" if saturated else "no"
    return [
        f"Case {_evidence()['case_id']}-style plan (demo fixture, not live production).",
        f"Evidence pack: {row['attachments_mb']} MB attachments, {row['similar_tickets']} similar tickets.",
        f"Time-to-RCA p50 {row['p50_seconds']} s · p95 {row['p95_seconds']} s.",
        f"Engineer wait {row['engineer_wait_seconds']} s (queue + rec-engine).",
        f"rec-engine saturated: {sat}. Memory working set is at or above 90% of its limit in this snapshot.",
        _evidence()["note"],
    ]


def extract_credentials(question: str) -> dict[str, str | None]:
    u = re.search(
        r"user(?:name)?(?:\s+as)?\s*[:=]?\s*['\"]?([A-Za-z0-9._-]+)",
        question or "",
        re.I,
    )
    p = re.search(
        r"pass(?:word)?(?:\s+as)?\s*[:=]?\s*['\"]?([A-Za-z0-9._-]+)",
        question or "",
        re.I,
    )
    return {"username": u.group(1) if u else None, "password": p.group(1) if p else None}


def infer_suite(question: str) -> tuple[str | None, str | None]:
    q = (question or "").lower()
    layer = None
    if re.search(r"\bui\b", q):
        layer = "ui"
    elif re.search(r"\bapi\b", q):
        layer = "api"
    elif "performance" in q:
        layer = "performance"
    elif "security" in q:
        layer = "security"
    suite = None
    if (
        "golden" in q
        or "product suite" in q
        or "product-feature" in q
        or "product feature" in q
        or "product functionality" in q
    ):
        suite = "product"
    elif "regression" in q:
        suite = "regression"
    elif "sanity" in q:
        suite = "sanity"
    elif "smoke" in q:
        suite = "smoke"
    return suite, layer


def run_suite(suite: str, layer: str | None = None) -> dict[str, Any]:
    rows = _suites()["cases"]
    cases = [c for c in rows if suite in (c.get("suites") or [])]
    if layer:
        cases = [c for c in cases if c.get("layer") == layer]
    passed = [c for c in cases if c.get("status") == "pass"]
    failed = [c for c in cases if c.get("status") == "fail"]
    rcas = [
        dict({"id": c["id"], "name": c["name"]}, **(c.get("rca") or {}))
        for c in failed
        if c.get("rca")
    ]
    return {
        "suite": suite,
        "layer": layer,
        "total": len(cases),
        "passed": len(passed),
        "failed": len(failed),
        "skipped": len(cases) - len(passed) - len(failed),
        "duration_ms": sum(int(c.get("duration_ms") or 0) for c in cases),
        "failed_ids": [c["id"] for c in failed],
        "rcas": rcas,
        "cases": cases,
        "verdict": "FAIL" if failed else "PASS",
    }


def _plain_fail_why(case: dict[str, Any]) -> str:
    rca = case.get("rca") or {}
    blob = " ".join(
        [
            str(rca.get("id") or ""),
            str(rca.get("symptom") or ""),
            str(rca.get("cause") or ""),
            str(case.get("actual") or ""),
        ]
    )
    if "AUTH-OPEN" in blob:
        return "Case Intelligence API does not require login (AUTH-OPEN)"
    if "SECRET-IN-LOG" in blob:
        return "Authorization header echoed in rec-engine logs (redacted)"
    if "CERT-MISMATCH" in blob:
        return "AJ18991 HTTP 500 is a certificate SAN mismatch (CERT-MISMATCH)"
    if "CONNECTOR-LAG" in blob:
        return "signal-connector is crash-looping, so evidence is stale (CONNECTOR-LAG)"
    text = rca.get("symptom") or rca.get("cause") or case.get("actual") or "failed"
    return str(text).split(".")[0].strip()


def format_suite(summary: dict[str, Any]) -> str:
    suite = summary.get("suite") or "suite"
    layer = summary.get("layer")
    prefix = ""
    if layer == "api":
        prefix = "API "
    elif layer == "security":
        prefix = "Security "
    elif layer == "performance":
        prefix = "Performance "
    verb = "passed" if summary.get("failed") == 0 else "failed"
    ms = int(summary.get("duration_ms") or 0)
    approx = f"~{round(ms / 10) * 10} ms" if ms >= 50 else f"{ms} ms"
    headline = (
        f"{prefix}{suite} {verb} ({summary.get('passed')}/{summary.get('total')}) in {approx}"
    )
    lines = [headline, ""]
    fails = [c for c in summary.get("cases") or [] if c.get("status") == "fail"]
    if fails:
        lines.append("1 failed:" if len(fails) == 1 else f"{len(fails)} failed:")
        for row in fails:
            lines.append(f"- {row.get('name') or row.get('id')} — {_plain_fail_why(row)}")
    else:
        for row in summary.get("cases") or []:
            lines.append(f"- {row.get('name') or row.get('id')}")
    links = allure_links(summary)
    if links:
        lines.append("")
        for link in links:
            lines.append(link["label"])
    lines.append("")
    lines.append(SUITE_FOOTNOTE)
    return "\n".join(lines)


def format_engine_report(report: dict[str, Any] | None) -> str:
    if not report:
        return "No RCA report in this demo payload."
    return rca_engine.format_report(report)


def compute_app_health(
    last_smoke: dict[str, Any] | None = None,
    last_sanity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    services = _services()["services"]
    rca = rca_engine.evaluate()
    sec = security_engine.evaluate()
    last_smoke = last_smoke if last_smoke is not None else run_suite("smoke")
    reasons: list[str] = []

    crashloop = any("crashloop" in str(s.get("status") or "").lower() for s in services)
    smoke_fail = bool(last_smoke and last_smoke.get("verdict") == "FAIL")
    sanity_fail = bool(last_sanity and last_sanity.get("verdict") == "FAIL")
    fired = rca.get("fired") or []
    high_rca = any(str(f.get("severity") or "").upper() in {"CRITICAL", "HIGH"} for f in fired)
    auth_open = any(f.get("id") == "AUTH-OPEN" for f in (sec.get("fired") or []))
    not_ready = any(not s.get("ready") or s.get("status") != "Running" for s in services)
    restarts = any(int(s.get("restarts") or 0) > 0 for s in services)
    all_running = bool(services) and all(
        s.get("status") == "Running" and s.get("ready") for s in services
    )
    smoke_passed = bool(last_smoke and last_smoke.get("verdict") == "PASS")

    if smoke_fail:
        reasons.append("smoke FAIL")
        health = "CRITICAL"
    else:
        if crashloop:
            reasons.append("CrashLoopBackOff")
        if sanity_fail:
            reasons.append("sanity FAIL")
        if high_rca:
            reasons.append("HIGH RCA")
        if restarts:
            reasons.append("restarts")
        if not_ready:
            reasons.append("service not ready")
        if auth_open:
            reasons.append("AUTH-OPEN")
        healthy_ok = (
            all_running
            and smoke_passed
            and not crashloop
            and not high_rca
            and not restarts
            and not sanity_fail
            and not auth_open
        )
        if healthy_ok:
            health = "HEALTHY"
            reasons.append("services Running, smoke PASS, no HIGH RCA")
        else:
            health = "DEGRADED"

    return {
        "health": health,
        "reasons": reasons,
        "lastSmoke": last_smoke,
        "lastSanity": last_sanity,
        "crashloop": crashloop,
        "smokeFail": smoke_fail,
        "sanityFail": sanity_fail,
        "highRca": high_rca,
        "authOpen": auth_open,
        "allRunning": all_running,
        "smokePassed": smoke_passed,
        "fired": fired,
    }


def health_status(_question: str = "") -> dict[str, Any]:
    bundle = _services()
    rows = bundle["services"]
    unhealthy = [s for s in rows if s.get("status") != "Running" or not s.get("ready")]
    smoke = run_suite("smoke")
    sanity = run_suite("sanity")
    snapshot = compute_app_health(last_smoke=smoke, last_sanity=sanity)
    health = snapshot["health"]
    lines = [
        f"Quality of GaussIQ 1.0 (demo): {health} on tenant `{bundle['tenant']}` queue `{bundle['queue']}` (simulated, not live production).",
        f"Services: {len(unhealthy)} / {len(rows)} not ready ("
        + (", ".join(s["id"] for s in unhealthy) or "none")
        + ").",
        f"Open support cases: {_cases()['open']}. Gross MTTR: {_perf()['gross_mttr_hours']} h. Eng assist: {_perf()['eng_assist_hours']} h.",
        "Root cause (from fixtures):",
    ]
    for f in snapshot["fired"]:
        lines.append(f"- {f['severity']} {f['id']} {f['component']}: {f['title']}")
    sec_fired = security_engine.evaluate().get("fired") or []
    if sec_fired:
        lines.append("Security (from fixtures):")
        for f in sec_fired:
            lines.append(f"- {f['severity']} {f['id']} {f['component']}: {f['title']}")
    lines.append(
        f"Auto-ran smoke: {smoke['verdict']} {smoke['passed']}/{smoke['total']} and sanity: {sanity['verdict']} {sanity['passed']}/{sanity['total']}."
    )
    if sanity.get("rcas"):
        rca = sanity["rcas"][0]
        lines.append("")
        lines.append(
            "RCA — "
            + str(rca.get("name") or rca.get("id"))
            + "\nSymptom: "
            + str(rca.get("symptom") or "")
            + "\nCause: "
            + str(rca.get("cause") or "")
            + "\nFix: "
            + str(rca.get("fix") or "")
        )
    lines.append("")
    lines.append(
        "Full regression is heavier (API + security + performance). Say yes to run it, or no to stop here."
    )
    return {
        "route": "app_status",
        "source": "handler:app_status",
        "tools": ["run_suite:smoke", "run_suite:sanity", "read_fixture:gaussiq/fixtures/services.json"],
        "answer": "\n".join(lines),
        "metrics": {
            "health": health,
            "health_reasons": snapshot["reasons"],
            "unhealthy": len(unhealthy),
            "open_cases": _cases()["open"],
            "gross_mttr_hours": _perf()["gross_mttr_hours"],
            "eng_assist_hours": _perf()["eng_assist_hours"],
            "smoke_verdict": smoke["verdict"],
            "sanity_verdict": sanity["verdict"],
        },
        "ui": "verdict",
        "awaiting_regression": True,
        "session_update": {"awaiting_regression": True},
        "health": {
            "smoke_report": smoke,
            "sanity_report": sanity,
            "health": health,
            "reasons": snapshot["reasons"],
        },
        "caveat": caveat(),
    }


def skip_regression(_question: str = "") -> dict[str, Any]:
    snapshot = compute_app_health(
        last_smoke=run_suite("smoke"), last_sanity=run_suite("sanity")
    )
    return {
        "route": "skip_regression",
        "source": "handler:app_status",
        "tools": [],
        "answer": (
            "Regression skipped. Current quality verdict stays at the smoke + sanity read: "
            f"GaussIQ 1.0 demo services are {snapshot['health']} until signal-connector is Running "
            "and AJ18991 is off the cert SAN mismatch."
        ),
        "metrics": {
            "regression": "skipped",
            "health": snapshot["health"],
            "health_reasons": snapshot["reasons"],
        },
        "ui": "verdict",
        "awaiting_regression": False,
        "session_update": {"awaiting_regression": False},
        "caveat": caveat(),
    }


def case_rca(question: str = "") -> dict[str, Any]:
    items = _cases()["items"]
    blob = (question or "").upper()
    wanted = None
    for row in items:
        if row["id"] in blob:
            wanted = row
            break
    if wanted is None:
        wanted = next((c for c in items if c["id"] == "AJ18991"), items[0])
    report = rca_engine.evaluate()
    lines = [
        f"Case {wanted['id']} — {wanted['org']} / {wanted['customer']} / {wanted['product']}.",
        f"Severity {wanted['severity']}. Region {wanted['region']}. Status {wanted['status']}.",
        f"Symptom: {wanted['symptom']}",
        f"Component: {wanted['component']}",
        f"Likely cause (fixture): {wanted['likely_cause']}",
        "Similar DEMO tickets: " + ", ".join(wanted.get("similar") or ["none"]) + ".",
        "Discarded knowledge: " + "; ".join(wanted.get("kb_discarded") or ["none"]) + ".",
        f"Verify: {wanted['verification']}",
        "",
        format_engine_report(report),
    ]
    return {
        "route": "case_rca",
        "source": "handler:case_rca",
        "tools": ["read_fixture:gaussiq/fixtures/cases.json", "rule_rca:gaussiq/rca_engine.py"],
        "answer": "\n".join(lines),
        "metrics": {
            "case_id": wanted["id"],
            "open_cases": _cases()["open"],
            "fired": [r["id"] for r in report["fired"]],
            "skipped": [r["id"] for r in report["skipped"]],
        },
        "ui": "rca",
        "rca": report,
        "case": wanted,
        "caveat": caveat(),
    }


def why_mttr(_question: str = "") -> dict[str, Any]:
    p = _perf()
    b = p["baseline"]
    report = rca_engine.evaluate()
    delta_g = round(p["gross_mttr_hours"] - b["gross_mttr_hours"], 1)
    direction = "above" if delta_g > 0 else "below"
    lines = [
        f"Gross MTTR is {p['gross_mttr_hours']} hours in this demo fixture, {abs(delta_g)} hours {direction} the lab baseline of {b['gross_mttr_hours']}.",
        f"Net MTTR {p['net_mttr_hours']} h vs baseline {b['net_mttr_hours']}. Eng assist {p['eng_assist_hours']} h vs {b['eng_assist_hours']}.",
        "These are original demo-tenant fixtures, not live production and not GaussIQ published ranges.",
        "Why it is high in this snapshot:",
    ]
    for row in report["fired"]:
        if row["id"] in {"CERT-MISMATCH", "CONNECTOR-LAG", "SKILL-GAP-TLS"}:
            lines.append(f"- {row['id']}: {row['title']}")
    lines.append("")
    lines.append(
        "Checked — not the cause: APP-CODE-500 (the 500 is the cert), CPU-HOT "
        "(rec-engine is memory-bound, not CPU-bound), INSIGHTS-DOWN."
    )
    if any(row["id"] == "MEM-PRESSURE" for row in report["fired"]):
        lines.append(
            "Platform note: MEM-PRESSURE is firing on rec-engine. That slows recommendations; "
            "it is not the whole MTTR gap (cert SAN + connector lag still dominate open time)."
        )
    lines.append("")
    lines.append(format_engine_report(report))
    return {
        "route": "why_mttr",
        "source": "handler:why_mttr",
        "tools": [
            "read_fixture:gaussiq/fixtures/performance.json",
            "rule_rca:gaussiq/rca_engine.py",
        ],
        "answer": "\n".join(lines),
        "metrics": {
            "gross_mttr_hours": p["gross_mttr_hours"],
            "baseline_gross_mttr_hours": b["gross_mttr_hours"],
            "delta_hours": delta_g,
            "fired": [r["id"] for r in report["fired"]],
        },
        "ui": "rca",
        "rca": report,
        "caveat": caveat(),
    }


def perf_metrics(_question: str = "") -> dict[str, Any]:
    p = _perf()
    b = p["baseline"]
    lines = [
        f"Performance fixture for tenant `{p['tenant']}` ({p['window']}). Snapshot `{p['generated_at']}`.",
        p["note"],
        f"Gross MTTR: {p['gross_mttr_hours']} hours (baseline {b['gross_mttr_hours']}).",
        f"Net MTTR: {p['net_mttr_hours']} hours (baseline {b['net_mttr_hours']}).",
        f"Eng assist: {p['eng_assist_hours']} hours (baseline {b['eng_assist_hours']}).",
        f"Open cases: {p['open_cases']}. Resolved in 7 days: {p['resolved_7d']}.",
        "Gross MTTR is open-to-close including wait. Net MTTR pauses customer wait. Eng assist is engineer touch time.",
        "These are original demo-tenant numbers, not GaussIQ published 10–20% marketing ranges.",
    ]
    return {
        "route": "perf_metrics",
        "source": "handler:perf_metrics",
        "tools": ["read_fixture:gaussiq/fixtures/performance.json"],
        "answer": "\n".join(lines),
        "metrics": {
            "gross_mttr_hours": p["gross_mttr_hours"],
            "net_mttr_hours": p["net_mttr_hours"],
            "eng_assist_hours": p["eng_assist_hours"],
            "open_cases": p["open_cases"],
        },
        "ui": "performance",
        "caveat": caveat(),
    }


def skills_gaps(_question: str = "") -> dict[str, Any]:
    bundle = _skills()
    lines = [
        f"Skills Intelligence fixture for `{bundle['tenant']}`. {bundle['note']}",
        f"High-impact gaps: {bundle['high_impact_gaps']}.",
    ]
    for row in bundle["items"]:
        lines.append(
            f"- {row['skill']} demand={row['demand']} coverage={row['coverage']} recency_days={row['recency_days']}"
        )
        lines.append(f"  {row['why']}")
    return {
        "route": "skills_gaps",
        "source": "handler:skills_gaps",
        "tools": ["read_fixture:gaussiq/fixtures/skills.json"],
        "answer": "\n".join(lines),
        "metrics": {
            "high_impact_gaps": bundle["high_impact_gaps"],
            "skills": [r["skill"] for r in bundle["items"]],
        },
        "ui": "skills",
        "caveat": caveat(),
    }


def service_health(_question: str = "") -> dict[str, Any]:
    bundle = _services()
    rows = bundle["services"]
    unhealthy = [s for s in rows if s.get("status") != "Running" or not s.get("ready")]
    lines = [
        f"24x7 health of GaussIQ 1.0 demo services on `{bundle['tenant']}` ({bundle['note']}).",
        f"{len(unhealthy)} of {len(rows)} services are not ready:",
    ]
    for s in rows:
        lines.append(
            f"- `{s['id']}` ({s['product']}): status={s['status']} restarts={s['restarts']} "
            f"CPU {s['cpu_pct']}% of limit · memory {s['memory_mib']}/{s['memory_limit_mib']} MiB. {s['probe']}"
        )
    report = rca_engine.evaluate()
    lines.append("")
    lines.append(format_engine_report(report))
    return {
        "route": "service_health",
        "source": "handler:service_health",
        "tools": ["read_fixture:gaussiq/fixtures/services.json"],
        "answer": "\n".join(lines),
        "metrics": {
            "unhealthy": len(unhealthy),
            "service_count": len(rows),
            "cpu": {s["id"]: s["cpu_pct"] for s in rows},
        },
        "ui": "health",
        "rca": report,
        "caveat": caveat(),
    }


def platform_perf(_question: str = "") -> dict[str, Any]:
    bundle = _services()
    rows = bundle["services"]
    report = rca_engine.evaluate()
    rec = next((s for s in rows if s["id"] == "rec-engine"), rows[0])
    pct = memory_pct(rec)
    hottest_cpu = max(rows, key=lambda s: float(s.get("cpu_pct") or 0))
    lines = [
        "Platform performance (pods), not ops MTTR. CPU and memory are % of each service limit. "
        "Fixtures, not a live cluster, not GaussIQ production.",
        f"`{rec['id']}` memory {rec['memory_mib']}/{rec['memory_limit_mib']} MiB ({pct}% of limit) "
        f"restarts={rec.get('restarts') or 0} last_reason={rec.get('last_reason') or '-'}.",
        f"Hottest CPU in this snapshot: `{hottest_cpu['id']}` at {hottest_cpu['cpu_pct']}% of its limit "
        "(under the 80% CPU-HOT threshold).",
        "Fire / skip: MEM-PRESSURE fires. CPU-HOT is skipped. CONNECTOR-LAG is the crash-looping "
        "signal-connector — a different problem from rec-engine memory.",
        "",
        format_engine_report(report),
    ]
    return {
        "route": "platform_perf",
        "source": "handler:platform_perf",
        "tools": [
            "read_fixture:gaussiq/fixtures/services.json",
            "rule_rca:gaussiq/rca_engine.py",
        ],
        "answer": "\n".join(lines),
        "metrics": {
            "rec_engine_memory_pct": pct,
            "rec_engine_cpu_pct": rec["cpu_pct"],
            "hottest_cpu_id": hottest_cpu["id"],
            "hottest_cpu_pct": hottest_cpu["cpu_pct"],
            "fired": [r["id"] for r in report["fired"]],
            "skipped": [r["id"] for r in report["skipped"]],
        },
        "ui": "rca",
        "rca": report,
        "caveat": caveat(),
    }


def evidence_timing(question: str = "", session: dict[str, Any] | None = None) -> dict[str, Any]:
    pack = _evidence()
    ladder = pack["ladder"]
    session = session or {}
    rung = _evidence_rung(session)
    blob = (question or "").lower()
    if any(token in blob for token in ("create", "large", "huge")):
        rung = max(rung, int(pack.get("large_rung") or 2))
    rung = max(0, min(rung, len(ladder) - 1))
    row = ladder[rung]
    saturated = rec_engine_saturated()
    lines = _format_evidence_row(row, saturated)
    lines.append(
        "Say “add more evidence” to append the next ladder step to this page session, then ask timing again."
    )
    return {
        "route": "evidence_timing",
        "source": "handler:evidence_timing",
        "tools": [
            "read_fixture:gaussiq/fixtures/evidence.json",
            "read_fixture:gaussiq/fixtures/services.json",
        ],
        "answer": "\n".join(lines),
        "metrics": {
            "case_id": pack["case_id"],
            "attachments_mb": row["attachments_mb"],
            "similar_tickets": row["similar_tickets"],
            "p50_seconds": row["p50_seconds"],
            "p95_seconds": row["p95_seconds"],
            "engineer_wait_seconds": row["engineer_wait_seconds"],
            "rec_engine_saturated": saturated,
            "evidence_rung": rung,
        },
        "ui": "evidence",
        "session_update": {"evidence_rung": rung},
        "caveat": caveat(),
    }


def add_evidence(_question: str = "", session: dict[str, Any] | None = None) -> dict[str, Any]:
    pack = _evidence()
    ladder = pack["ladder"]
    session = session or {}
    rung = _evidence_rung(session)
    nxt = min(rung + 1, len(ladder) - 1)
    capped = nxt == rung
    row = ladder[nxt]
    prev = ladder[rung]
    saturated = rec_engine_saturated()
    added_mb = row["attachments_mb"] - prev["attachments_mb"]
    added_sim = row["similar_tickets"] - prev["similar_tickets"]
    lines = [
        (
            "Evidence snapshot is already at the last fixture rung. Timing below is unchanged."
            if capped
            else (
                f"Appended +{added_mb} MB attachments and +{added_sim} similar tickets to the in-memory "
                "snapshot (not written to disk, gone on refresh)."
            )
        ),
    ]
    lines.extend(_format_evidence_row(row, saturated))
    lines.append("Re-ask “how long for RCA on a huge evidence case?” to read this snapshot again.")
    return {
        "route": "add_evidence",
        "source": "handler:add_evidence",
        "tools": ["read_fixture:gaussiq/fixtures/evidence.json"],
        "answer": "\n".join(lines),
        "metrics": {
            "case_id": pack["case_id"],
            "attachments_mb": row["attachments_mb"],
            "similar_tickets": row["similar_tickets"],
            "p50_seconds": row["p50_seconds"],
            "p95_seconds": row["p95_seconds"],
            "engineer_wait_seconds": row["engineer_wait_seconds"],
            "rec_engine_saturated": saturated,
            "evidence_rung": nxt,
            "capped": capped,
        },
        "ui": "evidence",
        "session_update": {"evidence_rung": nxt},
        "caveat": caveat(),
    }


def perf_rca(_question: str = "") -> dict[str, Any]:
    report = rca_engine.evaluate()
    return {
        "route": "perf_rca",
        "source": "handler:perf_rca",
        "tools": ["rule_rca:gaussiq/rca_engine.py"],
        "answer": format_engine_report(report),
        "metrics": {
            "fired": [r["id"] for r in report["fired"]],
            "skipped": [r["id"] for r in report["skipped"]],
            "counts": report["counts"],
            "unhealthy": report["unhealthy"],
        },
        "ui": "rca",
        "rca": report,
        "caveat": caveat(),
    }


def security_rca(_question: str = "") -> dict[str, Any]:
    report = security_engine.evaluate()
    return {
        "route": "security_rca",
        "source": "handler:security_rca",
        "tools": ["rule_rca:gaussiq/security_engine.py", "read_fixture:gaussiq/fixtures/security.json"],
        "answer": format_engine_report(report),
        "metrics": {
            "fired": [r["id"] for r in report["fired"]],
            "skipped": [r["id"] for r in report["skipped"]],
            "counts": report["counts"],
        },
        "ui": "security",
        "security": report,
        "caveat": caveat(),
    }


def login_api(question: str = "") -> dict[str, Any]:
    creds = extract_credentials(question)
    username, password = creds["username"], creds["password"]
    accounts = _users()["accounts"]
    if not username or not password:
        return {
            "route": "login_api",
            "source": "handler:login_api",
            "tools": ["read_fixture:gaussiq/fixtures/users.json"],
            "answer": (
                "This lab will not invent credentials. Say: test the login with username as giquser "
                "and password as giqpass (fictional lab user)."
            ),
            "metrics": {"status": 400, "ok": False},
            "ui": "api_result",
            "caveat": caveat(),
        }
    row = next((a for a in accounts if a["username"] == username), None)
    if not row or row["password"] != password:
        return {
            "route": "login_api",
            "source": "handler:login_api",
            "tools": ["read_fixture:gaussiq/fixtures/users.json"],
            "answer": (
                f"POST `/lab/login` username=`{username}` → 401 invalid credentials.\n"
                "RCA — login rejected\nSymptom: session was not created.\n"
                "Evidence: compared the payload to gaussiq/fixtures/users.json.\n"
                "Cause: username missing from the lab roster, or password did not match.\n"
                "Fix: use the documented lab pair giquser / giqpass. Do not retry with invented users."
            ),
            "metrics": {"ok": False, "status": 401, "username": username},
            "ui": "api_result",
            "caveat": caveat(),
        }
    return {
        "route": "login_api",
        "source": "handler:login_api",
        "tools": ["http:POST /lab/login", "read_fixture:gaussiq/fixtures/users.json"],
        "answer": (
            f"POST `/lab/login` → 200 OK.\nActor `{row['displayName']}` ({row['role']}).\n"
            "Fictional lab user only. This is not a GaussIQ employee account."
        ),
        "metrics": {"ok": True, "status": 200, "username": username},
        "ui": "api_result",
        "caveat": caveat(),
    }


def kb_retrieve(question: str = "") -> dict[str, Any]:
    entries = _kb()["entries"]
    q = (question or "").lower()

    def score(entry: dict[str, Any]) -> int:
        n = 0
        for kw in entry.get("keywords") or []:
            if kw.lower() in q:
                n += 4
        for token in re.findall(r"[a-z0-9]+", q):
            hay = " ".join(
                [entry["id"], entry["title"], entry["summary"], " ".join(entry.get("keywords") or [])]
            ).lower()
            if token in hay:
                n += 1
        return n

    ranked = sorted(((score(e), e) for e in entries), key=lambda x: x[0], reverse=True)
    best_score, best = ranked[0]
    if best_score <= 0:
        return {
            "route": "kb_retrieve",
            "source": "kb:none",
            "tools": ["kb_search:gaussiq/fixtures/kb.json"],
            "answer": "The catalog has no matching public-concept entry. No number was generated.",
            "metrics": None,
            "ui": None,
            "caveat": caveat(),
        }
    return {
        "route": "kb_retrieve",
        "source": f"kb:{best['id']}",
        "tools": ["kb_search:gaussiq/fixtures/kb.json", f"read_doc:{best['citation']}"],
        "answer": f"{best['title']}.\n{best['summary']}\nCitation: `{best['citation']}`.",
        "metrics": None,
        "citations": [best["citation"]],
        "match": {"id": best["id"], "score": best_score},
        "ui": None,
        "caveat": caveat(),
    }


def build_product_checks() -> list[dict[str, Any]]:
    """Ingest AJ18991 golden data, then assert Case Intelligence outcomes."""
    aj = next(c for c in _cases()["items"] if c["id"] == "AJ18991")
    tls = next(g for g in _skills()["items"] if "certificate" in g["skill"].lower())
    report = rca_engine.evaluate()
    fired = {row["id"]: row for row in (report.get("fired") or [])}
    skipped = {row["id"]: str(row.get("why") or "") for row in (report.get("skipped") or [])}

    rca_ok = "CERT-MISMATCH" in fired and "not the cause" in skipped.get(
        "APP-CODE-500", ""
    ).lower()
    rca_actual = str(aj.get("likely_cause") or "unknown") + ". Ruled out: application code."

    people = int(tls.get("people") or 0)
    assign_ok = people == 0 and str(tls.get("demand") or "") == "High"
    assign_actual = (
        f"{tls['skill']} — {people} people this shift. Gap flagged; pairing with a "
        "cert-experienced engineer recommended. Not auto-assigned."
    )

    expected_details = (
        "AJ18991 · George Jetson · Rocket Pack Express · "
        "Spaceley Sprocket migration tool · Business Critical · EMEA"
    )
    actual_details = (
        f"{aj['id']} · {aj['customer']} · {aj['org']} · {aj['product']} · "
        f"{aj['severity']} · {aj['region']}"
    )
    details_ok = actual_details == expected_details

    expected_similar = ["AJ18268", "AJ18600"]
    actual_similar = [str(x) for x in (aj.get("similar") or [])]
    similar_ok = actual_similar == expected_similar

    return [
        {
            "id": "rca",
            "check": "RCA",
            "ingested": f"{aj['id']} · {aj['symptom']}",
            "expected": "Certificate SAN mismatch. Ruled out: application code.",
            "actual": rca_actual,
            "status": "pass" if rca_ok else "fail",
        },
        {
            "id": "assignment",
            "check": "Assignment",
            "ingested": f"{aj['id']} needs {tls['skill']}; {people} people this shift",
            "expected": "Human-approved TLS / certificate skill. Flag the gap; do not auto-assign.",
            "actual": assign_actual,
            "status": "pass" if assign_ok else "fail",
        },
        {
            "id": "details",
            "check": "Case details",
            "ingested": expected_details,
            "expected": "Case record matches the ingested golden fields.",
            "actual": actual_details,
            "status": "pass" if details_ok else "fail",
        },
        {
            "id": "similar",
            "check": "Similar history",
            "ingested": ", ".join(expected_similar),
            "expected": "Return those ticket IDs.",
            "actual": ", ".join(actual_similar) if actual_similar else "none",
            "status": "pass" if similar_ok else "fail",
        },
    ]


def format_product_suite(summary: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    failed_n = sum(1 for c in checks if c.get("status") != "pass")
    passed_n = len(checks) - failed_n
    verb = "passed" if failed_n == 0 else "failed"
    ms = int(summary.get("duration_ms") or 0)
    approx = f"~{round(ms / 10) * 10} ms" if ms >= 50 else f"{ms} ms"
    lines = [
        f"Golden-case product suite {verb} ({passed_n}/{len(checks)}) in {approx}",
        "",
        "Ingested fixture AJ18991 — George Jetson / Rocket Pack Express / "
        "Spaceley Sprocket migration tool (HTTP 500 in the EMEA sandbox).",
        "",
    ]
    for row in checks:
        mark = "PASS" if row.get("status") == "pass" else "FAIL"
        lines.append(f"{row['check']} — {mark}")
        lines.append(f"  Ingested: {row['ingested']}")
        lines.append(f"  Expected: {row['expected']}")
        lines.append(f"  Actual: {row['actual']}")
        lines.append("")
    if failed_n == 0:
        lines.append(
            "Verdict: Case Intelligence matched the golden record on RCA, assignment, "
            "details, and similar-history IDs."
        )
    else:
        lines.append("Verdict: Golden record did not match on every check.")
    links = allure_links({"suite": "product", "layer": "api", "cases": summary.get("cases") or []})
    if links:
        lines.append("")
        for link in links:
            lines.append(link["label"])
    lines.append("")
    lines.append(SUITE_FOOTNOTE)
    return "\n".join(lines)


def product_suite(_question: str = "") -> dict[str, Any]:
    summary = run_suite("product")
    checks = build_product_checks()
    failed = [c for c in checks if c.get("status") != "pass"]
    passed_n = len(checks) - len(failed)
    verdict = "FAIL" if failed else "PASS"
    summary = dict(summary)
    summary["verdict"] = verdict
    summary["failed"] = len(failed)
    summary["passed"] = passed_n
    summary["total"] = len(checks)
    return {
        "route": "product_suite",
        "source": "handler:run_suite:product",
        "tools": [
            "read_fixture:gaussiq/fixtures/cases.json",
            "read_fixture:gaussiq/fixtures/skills.json",
            "read_fixture:gaussiq/fixtures/suites.json",
        ],
        "answer": format_product_suite(summary, checks),
        "metrics": {
            "suite": "product",
            "layer": "api",
            "passed": passed_n,
            "failed": len(failed),
            "total": len(checks),
            "verdict": verdict,
            "failed_ids": [c["id"] for c in failed],
            "case_id": "AJ18991",
        },
        "ui": "product_suite",
        "report": summary,
        "checks": checks,
        "allure": allure_links(
            {"suite": "product", "layer": "api", "cases": summary.get("cases") or []}
        ),
        "session_update": {"awaiting_regression": False},
        "awaiting_regression": False,
        "caveat": caveat(),
    }


def run_named_suite(question: str, suite: str | None = None, layer: str | None = None) -> dict[str, Any]:
    if not suite:
        suite, layer = infer_suite(question)
    if suite == "product":
        return product_suite(question)
    if not suite and layer:
        suite = "sanity"
    if not suite:
        return fallback(question)
    summary = run_suite(suite, layer)
    return {
        "route": "run_suite",
        "source": "handler:run_suite:" + suite + (f":{layer}" if layer else ""),
        "tools": ["read_fixture:gaussiq/fixtures/suites.json"],
        "answer": format_suite(summary),
        "metrics": {
            "suite": suite,
            "layer": layer,
            "passed": summary["passed"],
            "failed": summary["failed"],
            "total": summary["total"],
            "verdict": summary["verdict"],
            "failed_ids": summary["failed_ids"],
        },
        "ui": "suite_report",
        "report": summary,
        "allure": allure_links(summary),
        "session_update": {"awaiting_regression": False},
        "awaiting_regression": False,
        "caveat": caveat(),
    }


def suite_explain(question: str) -> dict[str, Any]:
    suite, layer = infer_suite(question)
    if not suite:
        suite = "sanity"
    summary = run_suite(suite, layer)
    return {
        "route": "suite_explain",
        "source": "handler:suite_explain",
        "tools": ["read_fixture:gaussiq/fixtures/suites.json"],
        "answer": format_suite(summary),
        "metrics": {
            "suite": suite,
            "layer": layer,
            "passed": summary["passed"],
            "failed": summary["failed"],
            "total": summary["total"],
            "verdict": summary["verdict"],
            "mode": "read",
        },
        "ui": "suite_explain",
        "report": summary,
        "allure": allure_links(summary),
        "caveat": caveat(),
    }


def email_report(_question: str = "") -> dict[str, Any]:
    snapshot = compute_app_health(last_smoke=run_suite("smoke"), last_sanity=run_suite("sanity"))
    return {
        "route": "email_report",
        "source": "handler:email_report",
        "tools": ["ui:email-report-tab"],
        "answer": (
            "Simulated email report — no SMTP host is contacted.\n"
            "To: sanket.dhamke@gmail.com\n"
            f"Subject would include quality {snapshot['health']} "
            "(this fixture is DEGRADED).\n"
            "Schedule options: every 1h / 3h / 6h / 12h / 24h. "
            "On new issue is on by default; duplicate signatures are skipped.\n"
            "SMTP=none. Open the Email report tab and click Send preview now "
            "to see the HTML body (service health, platform performance, security, "
            "plain-language RCA with Ruled out / not the cause, smoke).\n"
            "Cited source: docs/gaussiq.html Email report tab. "
            "Not affiliated with GaussIQ. Fixtures only, not live production."
        ),
        "metrics": {
            "health": snapshot["health"],
            "smtp": "none",
            "to": "sanket.dhamke@gmail.com",
        },
        "ui": "email",
        "caveat": caveat(),
    }


def fallback(_question: str = "") -> dict[str, Any]:
    return {
        "route": "fallback",
        "source": "fallback:deterministic",
        "tools": [],
        "answer": (
            "No handler or catalog entry matched that question. This sample does not call a language model, "
            "so it will not invent MTTR, CPU, memory, or RCA times. Try: current quality of GaussIQ 1.0, "
            "why CPU/memory is high, how long for RCA on a huge evidence case, add more evidence, "
            "any security issues, why AJ18991 returned HTTP 500, run golden-case product suite, "
            "run smoke, run sanity, run regression, or send an email preview."
        ),
        "metrics": None,
        "ui": None,
        "caveat": caveat(),
    }
