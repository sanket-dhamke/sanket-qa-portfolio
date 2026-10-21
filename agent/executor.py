"""Replay mock APIs and pytest-marker suites from fixtures.

GitHub Pages cannot spawn pytest. The console and `python -m agent` both read
the same JSON catalog. Live checks remain in tests/api and tests/ui.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent / "fixtures"

_USER = re.compile(
    r"user(?:name)?(?:\s+as)?\s*[:=]?\s*['\"]?([A-Za-z0-9._-]+)",
    re.I,
)
_PASS = re.compile(
    r"pass(?:word)?(?:\s+as)?\s*[:=]?\s*['\"]?([A-Za-z0-9._-]+)",
    re.I,
)
_TARGET = re.compile(
    r"(10\s*(?:m|million)|1\s*(?:m|million)|10,000,000|1,000,000|10000000|1000000)",
    re.I,
)


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def extract_credentials(question: str) -> tuple[str | None, str | None]:
    user = _USER.search(question or "")
    password = _PASS.search(question or "")
    return (
        user.group(1) if user else None,
        password.group(1) if password else None,
    )


def parse_asset_targets(question: str) -> list[int]:
    found: list[int] = []
    pattern = re.compile(
        r"10\s*(?:m|million)|10,000,000|10000000|1\s*(?:m|million)|1,000,000|1000000",
        re.I,
    )
    for match in pattern.finditer(question or ""):
        token = re.sub(r"[\s,]", "", match.group(0)).lower()
        n = 10_000_000 if token.startswith("10") else 1_000_000
        if n not in found:
            found.append(n)
    return found


def login(username: str | None, password: str | None) -> dict[str, Any]:
    accounts = {row["username"]: row for row in load("users.json")["accounts"]}
    if not username or not password:
        return {
            "ok": False,
            "status": 400,
            "path": "/logIn",
            "method": "POST",
            "error": "username and password are required. This lab will not invent credentials.",
            "body": None,
        }
    row = accounts.get(username)
    if row is None or row["password"] != password:
        return {
            "ok": False,
            "status": 401,
            "path": "/logIn",
            "method": "POST",
            "username": username,
            "error": "invalid credentials",
            "body": {"message": "Unauthorized", "username": username},
        }
    return {
        "ok": True,
        "status": 200,
        "path": "/logIn",
        "method": "POST",
        "username": username,
        "body": {
            "actor": row["urn"],
            "displayName": row["displayName"],
            "role": row["role"],
            "session": "PLAY_SESSION=lab-mock",
        },
    }


def run_api(endpoint_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    params = params or {}
    if endpoint_id == "rest.logIn":
        result = login(params.get("username"), params.get("password"))
        result["endpoint"] = endpoint_id
        return result
    if endpoint_id == "rest.health":
        return {
            "ok": True,
            "status": 200,
            "method": "GET",
            "path": "/health",
            "endpoint": endpoint_id,
            "body": {"ok": True, "component": "datahub-gms", "mode": "lab-mock"},
        }
    if endpoint_id == "rest.config":
        return {
            "ok": True,
            "status": 200,
            "method": "GET",
            "path": "/config",
            "endpoint": endpoint_id,
            "body": {
                "managedIngestion": {"enabled": True, "defaultCliVersion": "0.14.1"},
            },
        }
    if endpoint_id == "graphql.listIncidents":
        alerts = load("alerts.json")
        return {
            "ok": True,
            "status": 200,
            "method": "POST",
            "path": "/api/graphql",
            "endpoint": endpoint_id,
            "body": {
                "open": alerts["open"],
                "total": alerts["total"],
                "resolved": alerts["resolved"],
                "incidents": [
                    {k: item[k] for k in ("urn", "title", "state", "severity", "entity")}
                    for item in alerts["items"]
                    if item["state"] == "ACTIVE"
                ],
            },
        }
    if endpoint_id == "graphql.listIngestionSources":
        bundle = load("ingestion.json")
        return {
            "ok": True,
            "status": 200,
            "method": "POST",
            "path": "/api/graphql",
            "endpoint": endpoint_id,
            "body": {
                "total": len(bundle["sources"]),
                "sources": [
                    {"name": s["name"], "type": s["type"], "assets": s["assets"]}
                    for s in bundle["sources"]
                ],
            },
        }
    if endpoint_id == "graphql.searchAcrossEntities":
        totals = load("ingestion.json")["totals"]
        return {
            "ok": True,
            "status": 200,
            "method": "POST",
            "path": "/api/graphql",
            "endpoint": endpoint_id,
            "body": totals,
        }
    if endpoint_id == "rest.ingestProposal":
        return {
            "ok": True,
            "status": 200,
            "method": "POST",
            "path": "/aspects?action=ingestProposal",
            "endpoint": endpoint_id,
            "body": {"success": True},
        }
    return {
        "ok": False,
        "status": 404,
        "endpoint": endpoint_id,
        "error": "no executable mock for that catalog id",
        "body": None,
    }


def _cases(suite: str, layer: str | None) -> list[dict[str, Any]]:
    rows = load("suites.json")["cases"]
    picked = [c for c in rows if suite in c.get("suites", [])]
    if layer:
        picked = [c for c in picked if c.get("layer") == layer]
    return picked


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [c for c in cases if c["status"] == "pass"]
    failed = [c for c in cases if c["status"] == "fail"]
    skipped = [c for c in cases if c["status"] not in {"pass", "fail"}]
    rcas = [c["rca"] | {"id": c["id"], "name": c["name"]} for c in failed if c.get("rca")]
    return {
        "total": len(cases),
        "passed": len(passed),
        "failed": len(failed),
        "skipped": len(skipped),
        "duration_ms": sum(int(c.get("duration_ms") or 0) for c in cases),
        "failed_ids": [c["id"] for c in failed],
        "rcas": rcas,
        "cases": cases,
        "verdict": "PASS" if not failed else "FAIL",
    }


def run_suite(suite: str, layer: str | None = None) -> dict[str, Any]:
    suite = suite.lower().strip()
    layer = layer.lower().strip() if layer else None
    if suite not in {"smoke", "sanity", "regression"}:
        return {"error": f"unknown suite '{suite}'", "suite": suite, "layer": layer}
    if layer and layer not in {"api", "ui", "performance"}:
        return {"error": f"unknown layer '{layer}'", "suite": suite, "layer": layer}
    cases = _cases(suite, layer)
    summary = summarize_cases(cases)
    summary.update({"suite": suite, "layer": layer})
    return summary


def _suite_fail(summary: dict[str, Any] | None) -> bool:
    return bool(summary) and summary.get("verdict") == "FAIL"


def _suite_pass(summary: dict[str, Any] | None) -> bool:
    return bool(summary) and summary.get("verdict") == "PASS"


def compute_app_health(
    cluster: dict[str, Any],
    rca_report: dict[str, Any] | None,
    smoke: dict[str, Any] | None,
    sanity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """HEALTHY / DEGRADED / CRITICAL from pods, RCA, smoke, and sanity if run.

    CRITICAL only when smoke failed (GMS-level outage). Green smoke next to
    CRITICAL would mean the suite is wrong.
    DEGRADED: mae-consumer CrashLoop/OOM, restarts, log errors, sanity fail,
    HIGH or CRITICAL component RCA, or a pod that is not Running.
    HEALTHY only if every pod is Running, smoke passed, no CrashLoop/OOM,
    and no CRITICAL RCA (sanity pass if it ran).
    Never returns unknown.
    """
    pods = list(cluster.get("pods") or [])
    fired = list((rca_report or {}).get("fired") or [])
    reasons: list[str] = []

    def blob(pod: dict[str, Any]) -> str:
        return f"{pod.get('status') or ''} {pod.get('last_reason') or ''}".lower()

    crashloop = any("crashloop" in str(pod.get("status") or "").lower() for pod in pods)
    oom = any("oom" in blob(pod) for pod in pods)
    smoke_fail = _suite_fail(smoke)
    sanity_fail = _suite_fail(sanity)
    critical_rca = any(str(row.get("severity") or "").upper() == "CRITICAL" for row in fired)
    high_rca = any(str(row.get("severity") or "").upper() == "HIGH" for row in fired)
    restarts = any(int(pod.get("restarts") or 0) > 0 for pod in pods)
    errors = any(
        bool(pod.get("last_reason")) and "oom" not in str(pod.get("last_reason")).lower()
        for pod in pods
    )
    all_running = bool(pods) and all(
        pod.get("status") == "Running" and pod.get("ready") for pod in pods
    )
    smoke_passed = _suite_pass(smoke)

    if smoke_fail:
        reasons.append("smoke FAIL")
        health = "CRITICAL"
    else:
        if crashloop:
            reasons.append("CrashLoopBackOff")
        if oom:
            reasons.append("OOMKilled")
        if sanity_fail:
            reasons.append("sanity FAIL")
        if critical_rca:
            reasons.append("CRITICAL RCA")
        if high_rca:
            reasons.append("HIGH RCA")
        if restarts:
            reasons.append("restarts")
        if errors:
            reasons.append("pod errors")
        if not all_running:
            reasons.append("pod not ready")
        healthy_ok = (
            all_running
            and smoke_passed
            and not crashloop
            and not oom
            and not critical_rca
            and not high_rca
            and not restarts
            and not errors
            and not sanity_fail
        )
        if healthy_ok:
            health = "HEALTHY"
            reasons.append("pods Running, smoke PASS, no CRITICAL RCA")
        else:
            health = "DEGRADED"

    return {
        "health": health,
        "reasons": reasons,
        "crashloop": crashloop,
        "oom": oom,
        "smoke_fail": smoke_fail,
        "sanity_fail": sanity_fail,
        "critical_rca": critical_rca,
        "high_rca": high_rca,
        "restarts": restarts,
        "errors": errors,
        "all_running": all_running,
        "smoke_passed": smoke_passed,
        "sanity_ran": sanity is not None,
    }


def app_health(*, run_sanity: bool = True) -> dict[str, Any]:
    from agent.rca_engine import evaluate as evaluate_rca

    cluster = load("cluster.json")
    rca = load("rca.json")
    alerts = load("alerts.json")
    pods = cluster["pods"]
    unhealthy = [p for p in pods if p["status"] != "Running" or not p["ready"]]
    smoke = run_suite("smoke")
    sanity = run_suite("sanity") if run_sanity else None
    rules = evaluate_rca(cluster=cluster)
    snapshot = compute_app_health(cluster, rules, smoke, sanity)
    payload: dict[str, Any] = {
        "cluster": cluster["cluster"],
        "namespace": cluster["namespace"],
        "pod_count": len(pods),
        "unhealthy": len(unhealthy),
        "unhealthy_names": [p["component"] for p in unhealthy],
        "open_incidents": alerts["open"],
        "assets": load("ingestion.json")["totals"]["assets"],
        "smoke": {k: smoke[k] for k in ("passed", "failed", "total", "verdict")},
        "rca_titles": [
            f"{row['severity']} {row['id']}: {row['title']}" for row in rules["fired"]
        ],
        "health": snapshot["health"],
        "health_reasons": snapshot["reasons"],
        "smoke_report": smoke,
        "rca": rules,
        "rca_notes": rca.get("principle"),
        "snapshot": snapshot,
    }
    if sanity is not None:
        payload["sanity"] = {k: sanity[k] for k in ("passed", "failed", "total", "verdict")}
        payload["sanity_report"] = sanity
    else:
        payload["sanity"] = None
        payload["sanity_report"] = None
    return payload


def capacity_plan(targets: list[int]) -> dict[str, Any]:
    cfg = load("app_config.json")
    if not targets:
        targets = [1_000_000, 10_000_000]
    plans = []
    for n in targets:
        key = str(n)
        block = cfg["targets"].get(key)
        if not block:
            continue
        plans.append({"assets": n, **block})
    return {
        "current_assets": cfg["current_assets"],
        "current": cfg["current"],
        "blockers": cfg["blockers"],
        "plans": plans,
    }


def infer_suite(question: str) -> tuple[str | None, str | None]:
    q = question.lower()
    layer = None
    if re.search(r"\bui\b", q):
        layer = "ui"
    elif re.search(r"\bapi\b", q):
        layer = "api"
    elif "performance" in q:
        layer = "performance"
    suite = None
    if "regression" in q:
        suite = "regression"
    elif "sanity" in q:
        suite = "sanity"
    elif "smoke" in q:
        suite = "smoke"
    return suite, layer


def infer_api(question: str) -> str | None:
    q = question.lower()
    if any(w in q for w in ("alert", "incident")):
        return "graphql.listIncidents"
    if "log in" in q or "login" in q:
        return "rest.logIn"
    if "/health" in q or "gms health" in q or "health api" in q:
        return "rest.health"
    if "list ingestion" in q or "list sources" in q:
        return "graphql.listIngestionSources"
    if "searchacross" in q or "search datasets" in q:
        return "graphql.searchAcrossEntities"
    return None
