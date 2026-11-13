"""Handlers read fixtures only. A model never invents a number."""

from __future__ import annotations

import re
from typing import Any

from gaussiq.load import load
from gaussiq import rca_engine, security_engine

YES = re.compile(
    r"^\s*(y|yes|yeah|yep|ok|okay|sure|do it|go ahead|please run|run it|run them|run regression)\b",
    re.I,
)
NO = re.compile(r"^\s*(n|no|nope|skip|not now|later|don't|dont)\b", re.I)


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
    if "regression" in q:
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
    lines.append("")
    lines.append("Catalog replay — not a live pytest run.")
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
    lines.append("Checked — not the cause: APP-CODE-500 (the 500 is the cert), CPU-HOT, INSIGHTS-DOWN.")
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


def run_named_suite(question: str, suite: str | None = None, layer: str | None = None) -> dict[str, Any]:
    if not suite:
        suite, layer = infer_suite(question)
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
        "caveat": caveat(),
    }


def fallback(_question: str = "") -> dict[str, Any]:
    return {
        "route": "fallback",
        "source": "fallback:deterministic",
        "tools": [],
        "answer": (
            "No handler or catalog entry matched that question. This sample does not call a language model, "
            "so it will not invent MTTR, skill counts, or case totals. Try: current state of GaussIQ 1.0 demo "
            "services, why AJ18991 returned HTTP 500, gross MTTR, skill gaps, any security issues, login with "
            "giquser/giqpass, run smoke, run sanity, or run regression."
        ),
        "metrics": None,
        "ui": None,
        "caveat": caveat(),
    }
