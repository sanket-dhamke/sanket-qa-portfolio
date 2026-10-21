"""Mock datahub-gms: /health, /config, /api/graphql, a few REST actions.

This is a fictional demo tenant. It does not proxy a real cluster.
GraphQL is dispatched by operation name, not a full GraphQL engine.
"""

from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
INGESTION = json.loads(
    (ROOT / "agent" / "fixtures" / "ingestion.json").read_text(encoding="utf-8")
)
USERS = json.loads((ROOT / "agent" / "fixtures" / "users.json").read_text(encoding="utf-8"))
ALERTS = json.loads((ROOT / "agent" / "fixtures" / "alerts.json").read_text(encoding="utf-8"))

app = FastAPI(title="DataHub lab mock GMS", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: dict[str, Any] = {}


def reset_state() -> None:
    _state["sources"] = deepcopy(INGESTION["sources"])
    _state["totals"] = deepcopy(INGESTION["totals"])
    _state["executions"] = {}
    _state["seq"] = 2000


reset_state()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _op(query: str) -> str:
    blob = query or ""
    for name in (
        "createIngestionSource",
        "updateIngestionSource",
        "createIngestionExecutionRequest",
        "listIngestionSources",
        "listExecutionRequests",
        "ingestionSource",
        "searchAcrossEntities",
        "aggregateAcrossEntities",
        "assetCounts",
        "dataset",
        "listIncidents",
    ):
        if name in blob:
            return name
    return ""


def _list_sources() -> dict[str, Any]:
    rows = []
    for src in _state["sources"]:
        last = src.get("last_execution_urn")
        execs = []
        if last and last in _state["executions"]:
            execs.append(_state["executions"][last])
        elif last:
            execs.append(
                {
                    "urn": last,
                    "result": {
                        "status": src.get("last_run_status", "SUCCESS"),
                        "startTimeMs": _now_ms() - 60_000,
                        "durationMs": 18_400,
                    },
                }
            )
        rows.append(
            {
                "urn": src["urn"],
                "name": src["name"],
                "type": src["type"],
                "config": {
                    "executorId": src.get("executor_id", "default"),
                    "recipe": json.dumps({"pipeline_name": src.get("pipeline_name")}),
                },
                "schedule": None,
                "executions": {
                    "start": 0,
                    "count": len(execs),
                    "total": len(execs),
                    "executionRequests": execs,
                },
                "assets": src["assets"],
            }
        )
    return {
        "start": 0,
        "count": len(rows),
        "total": len(rows),
        "ingestionSources": rows,
    }


def _create_source(variables: dict[str, Any], query: str) -> str:
    inp = (variables or {}).get("input") or {}
    if not inp:
        inp = _inline_input(query)
    name = inp.get("name") or "adhoc-source"
    typ = inp.get("type") or "postgres"
    _state["seq"] += 1
    uid = f"lab-{_state['seq']}"
    urn = f"urn:li:dataHubIngestionSource:{uid}"
    recipe_raw = (inp.get("config") or {}).get("recipe") or "{}"
    try:
        recipe = json.loads(recipe_raw) if isinstance(recipe_raw, str) else recipe_raw
    except json.JSONDecodeError:
        recipe = {"raw": recipe_raw}
    source = {
        "urn": urn,
        "name": name,
        "type": typ,
        "pipeline_name": recipe.get("pipeline_name") or name,
        "executor_id": (inp.get("config") or {}).get("executorId") or "default",
        "host_port": (recipe.get("source") or {}).get("config", {}).get("host_port"),
        "database": (recipe.get("source") or {}).get("config", {}).get("database"),
        "service_name": (recipe.get("source") or {}).get("config", {}).get("service_name"),
        "assets": 0,
        "datasets": 0,
        "containers": 0,
        "dataJobs": 0,
        "last_run_status": "PENDING",
        "last_execution_urn": None,
        "recipe": recipe,
    }
    _state["sources"].append(source)
    return urn


def _inline_input(query: str) -> dict[str, Any]:
    name = _first(r'name:\s*"([^"]+)"', query)
    typ = _first(r'type:\s*"([^"]+)"', query)
    recipe = _first(r'recipe:\s*"((?:\\.|[^"\\])*)"', query)
    if recipe:
        recipe = recipe.replace('\\"', '"').replace("\\n", "\n")
    executor = _first(r'executorId:\s*"([^"]+)"', query) or "default"
    config: dict[str, Any] = {"executorId": executor}
    if recipe:
        config["recipe"] = recipe
    return {"name": name, "type": typ, "config": config}


def _first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def _create_execution(variables: dict[str, Any], query: str) -> str:
    inp = (variables or {}).get("input") or {}
    urn = inp.get("ingestionSourceUrn") or _first(
        r'ingestionSourceUrn:\s*"([^"]+)"', query
    )
    _state["seq"] += 1
    exec_urn = f"urn:li:dataHubExecutionRequest:exec-{_state['seq']}"
    _state["executions"][exec_urn] = {
        "urn": exec_urn,
        "ingestionSourceUrn": urn,
        "polls": 0,
        "input": {"requestedAt": _now_ms(), "actor": {"urn": "urn:li:corpuser:lab"}},
        "result": {
            "status": "PENDING",
            "startTimeMs": None,
            "durationMs": None,
        },
    }
    for src in _state["sources"]:
        if src["urn"] == urn:
            src["last_execution_urn"] = exec_urn
            src["last_run_status"] = "PENDING"
    return exec_urn


def _advance(exec_urn: str) -> dict[str, Any]:
    item = _state["executions"].get(exec_urn)
    if not item:
        return {
            "urn": exec_urn,
            "result": {"status": "FAILURE", "startTimeMs": None, "durationMs": None},
        }
    item["polls"] += 1
    if item["polls"] == 1:
        item["result"] = {
            "status": "PENDING",
            "startTimeMs": None,
            "durationMs": None,
        }
    elif item["polls"] == 2:
        item["result"] = {
            "status": "RUNNING",
            "startTimeMs": _now_ms(),
            "durationMs": None,
        }
    else:
        src_urn = item.get("ingestionSourceUrn")
        added = 14
        for src in _state["sources"]:
            if src["urn"] == src_urn:
                src["assets"] = src.get("assets", 0) + added
                src["datasets"] = src.get("datasets", 0) + added
                src["last_run_status"] = "SUCCESS"
                _state["totals"]["assets"] += added
                _state["totals"]["datasets"] += added
        item["result"] = {
            "status": "SUCCESS",
            "startTimeMs": item["result"].get("startTimeMs") or _now_ms() - 18_000,
            "durationMs": 18420,
            "report": {"datasets": added, "containers": 2},
        }
    return item


def _graphql(query: str, variables: dict[str, Any] | None) -> dict[str, Any]:
    variables = variables or {}
    op = _op(query)
    if op == "listIngestionSources":
        return {"data": {"listIngestionSources": _list_sources()}}
    if op == "createIngestionSource":
        return {"data": {"createIngestionSource": _create_source(variables, query)}}
    if op == "createIngestionExecutionRequest":
        return {
            "data": {
                "createIngestionExecutionRequest": _create_execution(variables, query)
            }
        }
    if op == "listExecutionRequests":
        urn = (variables or {}).get("urn") or _first(r'urn:\s*"([^"]+)"', query)
        if urn:
            return {
                "data": {
                    "listExecutionRequests": {
                        "start": 0,
                        "count": 1,
                        "total": 1,
                        "executionRequests": [_advance(urn)],
                    }
                }
            }
        rows = [_advance(key) for key in list(_state["executions"])]
        return {
            "data": {
                "listExecutionRequests": {
                    "start": 0,
                    "count": len(rows),
                    "total": len(rows),
                    "executionRequests": rows,
                }
            }
        }
    if op in {"searchAcrossEntities", "aggregateAcrossEntities", "assetCounts"}:
        totals = _state["totals"]
        return {
            "data": {
                "assetCounts": totals,
                "searchAcrossEntities": {
                    "total": totals["datasets"],
                    "searchResults": [],
                },
            }
        }
    if op == "listIncidents":
        active = [item for item in ALERTS["items"] if item["state"] == "ACTIVE"]
        return {
            "data": {
                "listIncidents": {
                    "total": ALERTS["total"],
                    "open": ALERTS["open"],
                    "incidents": active,
                }
            }
        }
    if op == "ingestionSource":
        urn = (variables or {}).get("urn") or _first(r'urn:\s*"([^"]+)"', query)
        for src in _state["sources"]:
            if src["urn"] == urn:
                return {"data": {"ingestionSource": src}}
        return {"data": {"ingestionSource": None}}
    return {
        "errors": [
            {
                "message": (
                    "This mock GMS only implements listIngestionSources, "
                    "createIngestionSource, createIngestionExecutionRequest, "
                    "listExecutionRequests, and assetCounts."
                )
            }
        ]
    }


@app.post("/logIn")
async def login(request: Request) -> JSONResponse:
    username = None
    password = None
    ctype = request.headers.get("content-type", "")
    if "application/json" in ctype:
        body = await request.json()
        username = body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
    accounts = {row["username"]: row for row in USERS["accounts"]}
    row = accounts.get(str(username or ""))
    if row is None or row["password"] != password:
        return JSONResponse({"message": "Unauthorized"}, status_code=401)
    return JSONResponse(
        {
            "actor": row["urn"],
            "displayName": row["displayName"],
            "role": row["role"],
        }
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "component": "datahub-gms", "mode": "lab-mock"}


@app.get("/config")
def config() -> dict[str, Any]:
    return {
        "statefulIngestionCapable": True,
        "managedIngestion": {"enabled": True, "defaultCliVersion": "0.14.1"},
        "datahub": {"server": "http://datahub-gms:8080", "mode": "lab-mock"},
    }


@app.post("/api/graphql")
async def graphql(request: Request) -> JSONResponse:
    body = await request.json()
    payload = _graphql(body.get("query") or "", body.get("variables"))
    status = 200 if "data" in payload else 400
    return JSONResponse(payload, status_code=status)


@app.post("/aspects")
async def aspects(request: Request) -> dict[str, Any]:
    action = request.query_params.get("action")
    body = await request.json()
    if action != "ingestProposal":
        return {"success": False, "error": "unsupported action"}
    return {
        "success": True,
        "urn": (body.get("proposal") or {}).get("entityUrn")
        or "urn:li:dataset:(urn:li:dataPlatform:postgres,analytics.public.orders,PROD)",
    }


@app.post("/reset")
def reset() -> dict[str, str]:
    reset_state()
    return {"status": "reset"}
