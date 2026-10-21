"""Deterministic handlers. They only emit numbers that exist in fixture JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent import executor, rca_engine

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RECIPES = Path(__file__).resolve().parent / "recipes"

COMPONENT_ALIASES = [
    ("datahub-mae-consumer", ["datahub-mae-consumer", "mae-consumer", "mae consumer"]),
    ("datahub-mce-consumer", ["datahub-mce-consumer", "mce-consumer", "mce consumer"]),
    ("datahub-frontend", ["datahub-frontend", "frontend"]),
    ("datahub-actions", ["datahub-actions", "actions executor", "datahub actions"]),
    ("datahub-gms", ["datahub-gms", "gms"]),
]


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _recipe(name: str) -> str:
    return (RECIPES / name).read_text(encoding="utf-8")


def _base() -> dict[str, Any]:
    return {
        "question": "",
        "route": "",
        "source": "",
        "tools": [],
        "answer": "",
        "metrics": None,
        "citations": [],
        "ui": None,
        "caveat": (
            "Keyword/rule router. Numbers come from checked-in fixtures, not a model. "
            "Fictional DataHub demo tenant — not a live cluster."
        ),
    }


def _named_component(question: str) -> str | None:
    blob = question.lower()
    for canonical, aliases in COMPONENT_ALIASES:
        if any(alias in blob for alias in aliases):
            return canonical
    return None


def pod_status(question: str) -> dict[str, Any]:
    cluster = _load("cluster.json")
    rca = _load("rca.json")
    pods = cluster["pods"]
    unhealthy = [pod for pod in pods if pod["status"] != "Running" or not pod["ready"]]
    oom = [pod for pod in pods if "oom" in str(pod.get("last_reason", "")).lower()]
    lines = [
        f"Namespace `{cluster['namespace']}` on `{cluster['cluster']}` "
        f"({cluster['note']}). Snapshot `{cluster['generated_at']}`.",
        f"{len(unhealthy)} of {len(pods)} pods are not ready:",
    ]
    for pod in unhealthy:
        lines.append(
            f"- `{pod['name']}` ({pod['component']}): status={pod['status']}, "
            f"restarts={pod['restarts']}, last_reason={pod.get('last_reason') or '-'}, "
            f"probe={pod.get('probe') or '-'}"
        )
    if oom:
        lines.append(
            f"OOMKilled in this fixture: {', '.join('`' + p['component'] + '`' for p in oom)}."
        )
    lines.append(rca_engine.evaluate()["principle"])
    lines.append("Root-cause notes from the RCA fixture:")
    for finding in rca["findings"]:
        rid = finding.get("id")
        tag = f"{rid} " if rid else ""
        lines.append(
            f"- [{finding['severity']}] {tag}{finding['component']}: {finding['title']}"
        )
    result = _base()
    result.update(
        {
            "route": "pod_status",
            "source": "handler:pod_status",
            "tools": [
                "read_fixture:agent/fixtures/cluster.json",
                "read_fixture:agent/fixtures/rca.json",
            ],
            "answer": "\n".join(lines),
            "metrics": {
                "cluster": cluster["cluster"],
                "pod_count": len(pods),
                "not_ready": len(unhealthy),
                "crashing_pods": len(unhealthy),
                "oomkilled": len(oom),
                "generated_at": cluster["generated_at"],
            },
            "citations": ["agent/fixtures/cluster.json", "agent/fixtures/rca.json"],
            "ui": "highlight_pods",
        }
    )
    return result


def resource_metrics(question: str) -> dict[str, Any]:
    payload = _load("metrics.json")
    named = _named_component(question)
    workers = payload["workers"]
    selected = [row for row in workers if row["component"] == named] if named else workers
    if not selected:
        selected = workers
    lines = [
        f"Simulated {payload['window']} window from `{payload['generated_at']}` "
        f"({payload['note']}).",
    ]
    if named:
        lines.append(f"Filter: `{named}`.")
    for row in selected:
        mem_pct = round(100.0 * row["memory_mib"] / row["memory_limit_mib"], 1)
        lines.append(
            f"- `{row['component']}` (`{row['pod']}`): CPU {row['cpu_pct']}% · "
            f"memory {row['memory_mib']} MiB / {row['memory_limit_mib']} MiB ({mem_pct}%)"
        )
    hottest = max(selected, key=lambda row: row["cpu_pct"])
    lines.append(
        f"Highest CPU in this selection: `{hottest['component']}` at {hottest['cpu_pct']}%."
    )
    result = _base()
    result.update(
        {
            "route": "resource_metrics",
            "source": "handler:resource_metrics",
            "tools": ["read_fixture:agent/fixtures/metrics.json"],
            "answer": "\n".join(lines),
            "metrics": {
                "window": payload["window"],
                "generated_at": payload["generated_at"],
                "filter": named,
                "workers": selected,
                "highest_cpu_name": hottest["component"],
                "highest_cpu_pct": hottest["cpu_pct"],
            },
            "citations": ["agent/fixtures/metrics.json"],
            "ui": "highlight_metrics",
        }
    )
    return result


def ingestion_assets(question: str) -> dict[str, Any]:
    bundle = _load("ingestion.json")
    sources = bundle["sources"]
    totals = bundle["totals"]
    lines = [
        f"Ingestion sources on fictional tenant `{bundle['tenant']}` "
        f"({bundle['note']}). Snapshot `{bundle['generated_at']}`.",
    ]
    for src in sources:
        lines.append(
            f"- `{src['name']}` type={src['type']} pipeline=`{src['pipeline_name']}` "
            f"urn=`{src['urn']}` assets={src['assets']} last_run={src['last_run_status']}"
        )
        lines.append(
            f"  host_port={src['host_port']} "
            + (
                f"database={src['database']}"
                if src.get("database")
                else f"service_name={src.get('service_name')}"
            )
        )
    lines.append(
        f"Total assets in this fixture: {totals['assets']} "
        f"(datasets={totals['datasets']}, containers={totals['containers']}, "
        f"dataJobs={totals['dataJobs']}, lineage_edges={totals['lineage_edges']})."
    )
    result = _base()
    result.update(
        {
            "route": "ingestion_assets",
            "source": "handler:ingestion_assets",
            "tools": ["read_fixture:agent/fixtures/ingestion.json"],
            "answer": "\n".join(lines),
            "metrics": {
                "tenant": bundle["tenant"],
                "generated_at": bundle["generated_at"],
                "source_count": len(sources),
                "total_assets": totals["assets"],
                "datasets": totals["datasets"],
                "containers": totals["containers"],
                "dataJobs": totals["dataJobs"],
                "lineage_edges": totals["lineage_edges"],
                "postgres_assets": next(s["assets"] for s in sources if s["type"] == "postgres"),
                "oracle_assets": next(s["assets"] for s in sources if s["type"] == "oracle"),
            },
            "citations": ["agent/fixtures/ingestion.json"],
            "ui": "highlight_sources",
        }
    )
    return result


def ingest_recipe(question: str) -> dict[str, Any]:
    recipe = _recipe("postgres.yml")
    result = _base()
    result.update(
        {
            "route": "ingest_recipe",
            "source": "handler:ingest_recipe",
            "tools": ["read_recipe:agent/recipes/postgres.yml"],
            "answer": (
                "I will not invent a postgres recipe. Fill the starter YAML "
                "(DataHub `type: postgres` shape: host_port, username, database, "
                "schema_pattern / table_pattern allow lists, sink datahub-rest → "
                "datahub-gms). On submit this lab simulates GraphQL "
                "`createIngestionSource` then `createIngestionExecutionRequest`, "
                "returns a run id, and plays a fake execution while CPU/memory "
                "for `datahub-actions` and `datahub-gms` tick.\n\n"
                f"```yaml\n{recipe.strip()}\n```"
            ),
            "metrics": None,
            "citations": [
                "agent/recipes/postgres.yml",
                "https://datahubproject.io/docs/generated/ingestion/sources/postgres/",
            ],
            "ui": "recipe_editor",
            "recipe": recipe,
        }
    )
    return result


def fallback(question: str) -> dict[str, Any]:
    result = _base()
    result.update(
        {
            "route": "fallback",
            "source": "fallback:deterministic",
            "tools": [],
            "answer": (
                "No handler or catalog entry matched that question. This sample "
                "does not call a language model, so it will not invent pod counts, "
                "CPU, or asset totals. Try: crashing/OOM pods, CPU of datahub-gms, "
                "how many assets, how many alerts, login with emuser/empass, "
                "run API sanity, check UI sanity, current state of the application, "
                "or what config to upgrade for 1M / 10M assets."
            ),
            "metrics": None,
            "citations": [],
        }
    )
    return result


def _format_rca_block(rca: dict[str, Any], heading: str | None = None) -> str:
    title = heading or rca.get("name") or rca.get("id") or "Failure"
    lines = [
        f"RCA — {title}",
        f"Symptom: {rca.get('symptom')}",
        "Evidence:",
    ]
    for item in rca.get("evidence") or []:
        lines.append(f"  - {item}")
    lines.append(f"Cause: {rca.get('cause')}")
    lines.append(f"Fix: {rca.get('fix')}")
    return "\n".join(lines)


def _format_suite(summary: dict[str, Any]) -> str:
    label = summary.get("suite", "suite")
    layer = summary.get("layer") or "api+ui+performance"
    lines = [
        f"Suite `{label}` layer={layer} → {summary['verdict']} "
        f"({summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['total']} total, {summary['duration_ms']} ms).",
        "This is a replay of the checked-in suite catalog — the same smoke/sanity/"
        "regression markers as pytest. GitHub Pages does not spawn pytest.",
    ]
    for case in summary.get("cases") or []:
        mark = "PASS" if case["status"] == "pass" else "FAIL"
        lines.append(
            f"- [{mark}] {case['layer']} {case['id']}: {case['name']} "
            f"({case['duration_ms']} ms)"
        )
        if case["status"] == "fail":
            lines.append(f"    expected: {case.get('expected')}")
            lines.append(f"    actual:   {case.get('actual')}")
    for rca in summary.get("rcas") or []:
        lines.append("")
        lines.append(_format_rca_block(rca, rca.get("name")))
    return "\n".join(lines)


def login_api(question: str) -> dict[str, Any]:
    username, password = executor.extract_credentials(question)
    run = executor.login(username, password)
    result = _base()
    if not username or not password:
        result.update(
            {
                "route": "login_api",
                "source": "handler:login_api",
                "tools": ["kb:rest.logIn"],
                "answer": (
                    "POST `/logIn` is in the catalog, but this lab will not invent "
                    "credentials. Say: test the login with username as emuser and "
                    "password as empass (fictional lab user)."
                ),
                "metrics": {"status": 400, "ok": False},
                "ui": "api_result",
                "api": run,
                "citations": ["agent/fixtures/users.json", "agent/kb/endpoints.json"],
            }
        )
        return result
    if run["ok"]:
        body = run["body"]
        answer = (
            f"POST `/logIn` → {run['status']} OK.\n"
            f"Actor `{body['actor']}` ({body['displayName']}, {body['role']}).\n"
            f"Session cookie: `{body['session']}`.\n"
            "Fictional lab user only."
        )
    else:
        answer = (
            f"POST `/logIn` username=`{username}` → {run['status']} {run.get('error')}.\n"
            "RCA — login rejected\n"
            "Symptom: UI/API session was not created.\n"
            "Evidence: mock GMS compared the payload to agent/fixtures/users.json.\n"
            "Cause: username missing from the lab roster, or password did not match.\n"
            "Fix: use the documented lab pair emuser / empass. Do not retry with invented users."
        )
    result.update(
        {
            "route": "login_api",
            "source": "handler:login_api",
            "tools": ["http:POST /logIn", "read_fixture:agent/fixtures/users.json"],
            "answer": answer,
            "metrics": {
                "ok": run["ok"],
                "status": run["status"],
                "username": username,
            },
            "ui": "api_result",
            "api": run,
            "citations": ["agent/fixtures/users.json"],
        }
    )
    return result


def run_named_suite(question: str, suite: str | None = None, layer: str | None = None) -> dict[str, Any]:
    if suite is None:
        suite, layer = executor.infer_suite(question)
    if suite is None and layer:
        suite = "sanity"
    if suite is None:
        return fallback(question)
    summary = executor.run_suite(suite, layer)
    result = _base()
    result.update(
        {
            "route": "run_suite",
            "source": f"handler:run_suite:{suite}" + (f":{layer}" if layer else ""),
            "tools": [
                "read_fixture:agent/fixtures/suites.json",
                f"pytest -m {suite}" + (f" and {layer}" if layer else ""),
            ],
            "answer": _format_suite(summary),
            "metrics": {
                "suite": suite,
                "layer": layer,
                "passed": summary.get("passed"),
                "failed": summary.get("failed"),
                "total": summary.get("total"),
                "verdict": summary.get("verdict"),
                "failed_ids": summary.get("failed_ids"),
            },
            "ui": "suite_report",
            "report": summary,
            "citations": ["agent/fixtures/suites.json"],
        }
    )
    return result


def execute_catalog_api(question: str) -> dict[str, Any]:
    endpoint_id = executor.infer_api(question)
    if endpoint_id == "rest.logIn":
        return login_api(question)
    if endpoint_id is None:
        return fallback(question)
    run = executor.run_api(endpoint_id)
    result = _base()
    body = run.get("body")
    if endpoint_id == "graphql.listIncidents" and isinstance(body, dict):
        lines = [
            f"POST `/api/graphql` listIncidents (DataHub incidents; the lab maps “alerts” here).",
            f"Open: {body['open']} · resolved: {body.get('resolved')} · total: {body['total']}.",
        ]
        for item in body.get("incidents") or []:
            lines.append(
                f"- [{item['severity']}] {item['title']} ({item['entity']})"
            )
        answer = "\n".join(lines)
        metrics = {"open": body["open"], "total": body["total"]}
    else:
        answer = (
            f"{run.get('method')} `{run.get('path')}` → {run.get('status')}.\n"
            f"{json.dumps(body, indent=2) if body is not None else run.get('error')}"
        )
        metrics = {"status": run.get("status"), "ok": run.get("ok")}
    result.update(
        {
            "route": "execute_api",
            "source": f"handler:execute_api:{endpoint_id}",
            "tools": [f"kb_exec:{endpoint_id}", f"http:{run.get('method')} {run.get('path')}"],
            "answer": answer,
            "metrics": metrics,
            "ui": "api_result",
            "api": run,
            "citations": ["agent/kb/endpoints.json", "agent/fixtures/alerts.json"],
        }
    )
    return result


def app_status(question: str) -> dict[str, Any]:
    health = executor.app_health()
    lines = [
        f"Application verdict: {health['health']} on `{health['cluster']}` "
        f"ns `{health['namespace']}` (simulated).",
        f"Pods: {health['unhealthy']} / {health['pod_count']} not ready "
        f"({', '.join(health['unhealthy_names']) or 'none'}).",
        f"Open DataHub incidents (alerts): {health['open_incidents']}. Assets: {health['assets']}.",
        "Root cause (from fixtures):",
    ]
    for title in health["rca_titles"]:
        lines.append(f"- {title}")
    smoke, sanity = health["smoke"], health["sanity"]
    lines.append(
        f"Auto-ran smoke: {smoke['verdict']} {smoke['passed']}/{smoke['total']} "
        f"and sanity: {sanity['verdict']} {sanity['passed']}/{sanity['total']}."
    )
    if health["sanity_report"].get("rcas"):
        lines.append("")
        lines.append(_format_rca_block(health["sanity_report"]["rcas"][0]))
    lines.append("")
    lines.append(
        "Full regression is heavier (API + UI + performance, including lineage and "
        "MAE memory). Say yes to run it, or no to stop here."
    )
    result = _base()
    result.update(
        {
            "route": "app_status",
            "source": "handler:app_status",
            "tools": [
                "read_fixture:agent/fixtures/cluster.json",
                "read_fixture:agent/fixtures/rca.json",
                "run_suite:smoke",
                "run_suite:sanity",
            ],
            "answer": "\n".join(lines),
            "metrics": {
                "health": health["health"],
                "unhealthy": health["unhealthy"],
                "open_incidents": health["open_incidents"],
                "assets": health["assets"],
                "smoke_verdict": smoke["verdict"],
                "sanity_verdict": sanity["verdict"],
            },
            "ui": "verdict",
            "awaiting_regression": True,
            "session_update": {"awaiting_regression": True},
            "health": health,
            "citations": [
                "agent/fixtures/cluster.json",
                "agent/fixtures/rca.json",
                "agent/fixtures/suites.json",
            ],
        }
    )
    return result


def skip_regression(question: str) -> dict[str, Any]:
    result = _base()
    result.update(
        {
            "route": "skip_regression",
            "source": "handler:app_status",
            "tools": [],
            "answer": (
                "Regression skipped. Current quality verdict stays at the smoke + sanity "
                "read: application is DEGRADED until datahub-mae-consumer is off OOMKilled "
                "and UI search/lineage are green."
            ),
            "metrics": {"regression": "skipped"},
            "ui": "verdict",
            "awaiting_regression": False,
            "session_update": {"awaiting_regression": False},
        }
    )
    return result


def perf_rca(question: str) -> dict[str, Any]:
    report = rca_engine.evaluate()
    result = _base()
    result.update(
        {
            "route": "perf_rca",
            "source": "handler:perf_rca",
            "tools": [
                "rule_rca:agent/rca_engine.py",
                "read_fixture:agent/fixtures/cluster.json",
                "read_fixture:agent/fixtures/metrics.json",
            ],
            "answer": rca_engine.format_report(report),
            "metrics": {
                "fired": [row["id"] for row in report["fired"]],
                "skipped": [row["id"] for row in report["skipped"]],
                "counts": report["counts"],
                "unhealthy": report["unhealthy"],
            },
            "ui": "rca",
            "rca": report,
            "citations": [
                "agent/rca_engine.py",
                "agent/fixtures/cluster.json",
                "agent/fixtures/metrics.json",
            ],
        }
    )
    return result


def capacity_plan(question: str) -> dict[str, Any]:
    targets = executor.parse_asset_targets(question)
    plan = executor.capacity_plan(targets)
    current = plan["current_assets"]
    lines = [
        f"Current ingested assets in this fixture: {current} "
        "(postgres 86 + oracle 54).",
        "Blockers before any scale-up:",
    ]
    for b in plan["blockers"]:
        lines.append(f"- {b}")
    for block in plan["plans"]:
        lines.append("")
        lines.append(
            f"To ingest {block['label']} ({block['scale_vs_current']}):"
        )
        for change in block["changes"]:
            lines.append(
                f"- `{change['component']}`: {change['from']} → {change['to']}"
            )
            lines.append(f"  why: {change['why']}")
    if not plan["plans"]:
        lines.append("Ask for 1 million or 10 million assets to see the upgrade table.")
    result = _base()
    result.update(
        {
            "route": "capacity_plan",
            "source": "handler:capacity_plan",
            "tools": [
                "read_fixture:agent/fixtures/app_config.json",
                "read_fixture:agent/fixtures/ingestion.json",
                "read_fixture:agent/fixtures/rca.json",
            ],
            "answer": "\n".join(lines),
            "metrics": {
                "current_assets": current,
                "targets": [p["assets"] for p in plan["plans"]],
            },
            "ui": "capacity",
            "capacity": plan,
            "citations": [
                "agent/fixtures/app_config.json",
                "agent/fixtures/metrics.json",
                "agent/fixtures/rca.json",
            ],
        }
    )
    return result

