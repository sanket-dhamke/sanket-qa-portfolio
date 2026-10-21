"""Deterministic handlers. They only emit numbers that exist in fixture JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
    lines.append("Root-cause notes from the RCA fixture:")
    for finding in rca["findings"]:
        lines.append(f"- [{finding['severity']}] {finding['component']}: {finding['title']}")
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
                "postgres/oracle sources and total assets, ingest a postgres source, "
                "or which GraphQL mutation creates an ingestion source."
            ),
            "metrics": None,
            "citations": [],
        }
    )
    return result
