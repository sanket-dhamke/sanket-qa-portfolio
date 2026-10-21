"""Deterministic RCA over fixtures.

Rules produce severity, observation, cause, and fix. A model never chooses
which rule fires and never invents a number. Exit 137 is SIGKILL — OOM only
when Kubernetes last_reason is OOMKilled; otherwise it is a probe kill.
"""

from __future__ import annotations

from typing import Any

from agent.executor import load

_RUNNING = {"running", "succeeded", "completed"}


def _pct(used: float, limit: float) -> float:
    if not limit:
        return 0.0
    return round(100.0 * used / limit, 1)


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
    cluster: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cluster = cluster or load("cluster.json")
    metrics = metrics or load("metrics.json")
    pods: list[dict[str, Any]] = cluster["pods"]
    platform: dict[str, Any] = cluster.get("platform") or {}
    workers = {row["component"]: row for row in metrics.get("workers") or []}

    fired: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def skip(rule_id: str, why: str) -> None:
        skipped.append({"id": rule_id, "why": why})

    oom = [
        p
        for p in pods
        if "oom" in str(p.get("last_reason") or "").lower()
        or str(p.get("status") or "").lower() == "evicted"
    ]
    if oom:
        names = ", ".join(p["component"] for p in oom)
        fired.append(
            _card(
                "MEM-PRESSURE",
                "CRITICAL",
                oom[0]["component"],
                "OOMKilled / evicted pod",
                f"{len(oom)} pod(s) hit the memory limit: {names}.",
                "Container working set reached the pod memory limit. Kubernetes SIGKILL (137) with reason OOMKilled.",
                "Raise that component's memory limit and heap, then confirm Kafka lag drains. Do not scale ingest until this is green.",
                [
                    f"{p['name']} status={p['status']} restarts={p['restarts']} "
                    f"last_reason={p.get('last_reason')} exit={p.get('last_exit_code')}"
                    for p in oom
                ],
            )
        )
    else:
        skip("MEM-PRESSURE", "No pod in this snapshot is OOMKilled or Evicted.")

    probe = [
        p
        for p in pods
        if p.get("last_exit_code") == 137
        and "oom" not in str(p.get("last_reason") or "").lower()
    ]
    if probe:
        names = ", ".join(p["component"] for p in probe)
        fired.append(
            _card(
                "PROBE-KILL",
                "CRITICAL",
                probe[0]["component"],
                "SIGKILL from a probe, not OOM",
                f"Exit 137 on {names} without last_reason=OOMKilled.",
                "137 means SIGKILL. A failing liveness probe also SIGKILLs. Memory limits would be the wrong knob.",
                "Lengthen the liveness timeout or fix the hung endpoint. Do not raise memory for a probe kill.",
                [
                    f"{p['name']} last_reason={p.get('last_reason')!r} probe={p.get('probe')}"
                    for p in probe
                ],
            )
        )
    else:
        oom137 = [
            p
            for p in pods
            if p.get("last_exit_code") == 137
            and "oom" in str(p.get("last_reason") or "").lower()
        ]
        if oom137:
            skip(
                "PROBE-KILL",
                "Exit 137 on "
                + ", ".join(p["component"] for p in oom137)
                + " has last_reason=OOMKilled, so this is memory pressure, not a probe timeout. Raising the probe delay would be the wrong fix.",
            )
        else:
            skip("PROBE-KILL", "No exit 137 without OOMKilled in this snapshot.")

    crashing = [
        p
        for p in pods
        if str(p.get("status") or "").lower() not in _RUNNING or not p.get("ready")
    ]
    if crashing:
        fired.append(
            _card(
                "POD-CRASH",
                "CRITICAL",
                crashing[0]["component"],
                "Pod not running / not ready",
                f"{len(crashing)} of {len(pods)} pods are not ready: "
                + ", ".join(p["component"] for p in crashing)
                + ".",
                "Phase or readiness failed. Combined with MEM-PRESSURE this is CrashLoopBackOff after OOM.",
                "Restore the crashing component before trusting search, lineage, or MAE-backed UI paths.",
                [
                    f"{p['name']} status={p['status']} ready={p.get('ready')} restarts={p['restarts']}"
                    for p in crashing
                ],
            )
        )
    else:
        skip("POD-CRASH", "Every pod is Running and ready.")

    hot_cpu = []
    hot_mem = []
    for row in workers.values():
        cpu = float(row.get("cpu_pct") or 0)
        mem_pct = _pct(row.get("memory_mib") or 0, row.get("memory_limit_mib") or 0)
        if cpu >= 90:
            hot_cpu.append((row, cpu, "CRITICAL"))
        elif cpu >= 80:
            hot_cpu.append((row, cpu, "HIGH"))
        if mem_pct >= 90:
            hot_mem.append((row, mem_pct, "CRITICAL"))
        elif mem_pct >= 80:
            hot_mem.append((row, mem_pct, "HIGH"))

    if hot_cpu:
        row, cpu, sev = max(hot_cpu, key=lambda item: item[1])
        fired.append(
            _card(
                "POD-CPU",
                sev,
                row["component"],
                "CPU at or above 80% of limit",
                f"`{row['component']}` CPU {cpu}% of its limit (percentage of the pod limit, not the node).",
                "Sustained CPU near the limit throttles that component.",
                "Raise the CPU limit or add a replica. A small limit at 95% can still be idle in absolute millicores.",
                [f"{r['component']} {c}%" for r, c, _ in hot_cpu],
            )
        )
    else:
        skip("POD-CPU", "No sampled worker is at ≥80% of its CPU limit.")

    if hot_mem:
        row, mem_pct, sev = max(hot_mem, key=lambda item: item[1])
        fired.append(
            _card(
                "POD-MEM",
                sev,
                row["component"],
                "Memory at or above 80% of limit",
                f"`{row['component']}` memory {mem_pct}% of its limit "
                f"({row['memory_mib']} / {row['memory_limit_mib']} MiB).",
                "Working set is against the cgroup limit; the next spike OOMKills.",
                "Raise the memory limit (and heap if this is a JVM) before adding ingest load.",
                [
                    f"{r['component']} {p}% ({r['memory_mib']}/{r['memory_limit_mib']} MiB)"
                    for r, p, _ in hot_mem
                ],
            )
        )
    else:
        skip("POD-MEM", "No sampled worker is at ≥80% of its memory limit.")

    restarty = [p for p in pods if int(p.get("restarts") or 0) >= 3]
    if restarty:
        fired.append(
            _card(
                "RESTARTS",
                "HIGH",
                restarty[0]["component"],
                "Repeated restarts",
                ", ".join(f"{p['component']} restarts={p['restarts']}" for p in restarty),
                "Kubernetes is crash-looping the container. Search/index lag follows MAE restarts.",
                "Fix the crash reason (see MEM-PRESSURE / PROBE-KILL) rather than deleting the pod on a loop.",
                [f"{p['name']} restarts={p['restarts']}" for p in restarty],
            )
        )
    else:
        skip("RESTARTS", "No pod has ≥3 restarts.")

    mae_conc = int(platform.get("mae_kafka_listener_concurrency") or 0)
    if mae_conc == 1:
        fired.append(
            _card(
                "INDEXING",
                "HIGH",
                "datahub-mae-consumer",
                "MAE Kafka listener concurrency is 1",
                "KAFKA_LISTENER_CONCURRENCY=1 on datahub-mae-consumer. One partition/listener cannot drain MetadataAuditEvent_v4 under ingest.",
                "Single-threaded apply plus an OOM loop is why UI search is empty while GMS counts still look fine.",
                "Raise MAE listener concurrency with partition count; only after memory headroom exists.",
                [f"mae_kafka_listener_concurrency={mae_conc}"],
            )
        )
    else:
        skip("INDEXING", f"MAE listener concurrency is {mae_conc or 'unset'}, not 1.")

    actions = workers.get("datahub-actions")
    if actions:
        mem_pct = _pct(actions["memory_mib"], actions["memory_limit_mib"])
        if mem_pct >= 80:
            fired.append(
                _card(
                    "EXECUTOR-MEM",
                    "HIGH",
                    "datahub-actions",
                    "Ingestion executor memory high",
                    f"datahub-actions {actions['memory_mib']} / {actions['memory_limit_mib']} MiB ({mem_pct}%).",
                    "UI ingestion recipes run in-process on the actions executor.",
                    "Stagger postgres and oracle recipes; avoid overlapping hourly runs.",
                    [f"{actions['memory_mib']} / {actions['memory_limit_mib']} MiB"],
                )
            )
        else:
            skip("EXECUTOR-MEM", f"datahub-actions memory {mem_pct}% is under 80%.")
    else:
        skip("EXECUTOR-MEM", "No datahub-actions row in the metrics fixture.")

    opts = str(platform.get("gms_java_opts") or "")
    if "-Xmx" not in opts:
        fired.append(
            _card(
                "GMS-HEAP",
                "MEDIUM",
                "datahub-gms",
                "GMS JVM has no -Xmx",
                "datahub-gms java opts do not set -Xmx, so the heap can grow into the pod limit.",
                "Default heap ergonomics plus ingestProposal traffic.",
                "Set -Xmx to ~75% of the GMS memory limit.",
                [opts or "(empty)"],
            )
        )
    else:
        skip("GMS-HEAP", f"datahub-gms already sets heap ({opts}).")

    if not platform.get("has_metrics", True):
        fired.append(
            _card(
                "METRICS",
                "WARN",
                "metrics-server",
                "No CPU/memory samples",
                "The cluster metrics API is unavailable, so percentages cannot be computed.",
                "Pod CPU and memory samples are missing in this snapshot.",
                "Restore the metrics API before trusting CPU/memory RCA.",
                ["has_metrics=false"],
            )
        )
    else:
        skip("METRICS", "metrics-server flag is true in this fixture; samples exist.")

    over_80 = bool(hot_cpu or hot_mem)
    if platform.get("has_metrics", True) and not over_80 and not oom and not crashing:
        fired.append(
            _card(
                "SIZING",
                "INFO",
                "cluster",
                "No pod above 80% of limit",
                "Metrics are present and nothing is above 80% of its limit.",
                "Current limits have headroom for this 140-asset fixture.",
                "Keep sampling during ingest; a single snapshot is not enough.",
                ["has_metrics=true", "no worker ≥80%"],
            )
        )
    else:
        skip(
            "SIZING",
            "Not an all-clear: at least one pressure, crash, or OOM finding is already firing.",
        )

    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "WARN": 3, "INFO": 4}
    fired.sort(key=lambda row: (order.get(row["severity"], 9), row["id"]))
    counts: dict[str, int] = {}
    for row in fired:
        counts[row["severity"]] = counts.get(row["severity"], 0) + 1

    return {
        "principle": (
            "Exit 137 is SIGKILL, not necessarily an OOM kill. Count memory pressure "
            "only when Kubernetes last_reason is OOMKilled. The rest is PROBE-KILL. "
            "Conflating them sends you to tune memory when the hang is a probe timeout."
        ),
        "fired": fired,
        "skipped": skipped,
        "counts": counts,
        "pod_count": len(pods),
        "unhealthy": len(crashing),
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
        lines.append(f"  Observation: {row['observation']}")
        for item in row.get("evidence") or []:
            lines.append(f"    - {item}")
        lines.append(f"  Cause: {row['cause']}")
        lines.append(f"  Fix: {row['recommendation']}")
        lines.append("")
    lines.append("Evaluated, not fired (this is part of the diagnosis):")
    for row in report["skipped"]:
        lines.append(f"- {row['id']}: {row['why']}")
    return "\n".join(lines).strip()
