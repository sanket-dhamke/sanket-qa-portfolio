"""Allure attachments for the DataHub lab fixture. DataHub OSS names only."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import allure

REPO = Path(__file__).resolve().parents[2]
# Append so ui/utils stays the local `utils` package.
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))

from agent.executor import load  # noqa: E402
from agent.rca_engine import evaluate, format_report  # noqa: E402


def pod_log_lines(cluster: dict[str, Any] | None = None) -> list[str]:
    cluster = cluster or load("cluster.json")
    lines: list[str] = []
    for pod in cluster.get("pods") or []:
        if pod.get("status") == "Running" and not pod.get("last_reason"):
            continue
        bits = [
            f"[{pod.get('component')}]",
            str(pod.get("status") or ""),
            f"restarts={pod.get('restarts')}",
        ]
        if pod.get("last_reason"):
            bits.append(f"last_reason={pod['last_reason']}")
        if pod.get("last_exit_code") is not None:
            bits.append(f"exit={pod['last_exit_code']}")
        if pod.get("probe"):
            bits.append(str(pod["probe"]))
        lines.append(" ".join(bits))
    return lines


def component_pod(name: str, cluster: dict[str, Any] | None = None) -> dict[str, Any]:
    cluster = cluster or load("cluster.json")
    for pod in cluster.get("pods") or []:
        if pod.get("component") == name:
            return pod
    raise AssertionError(f"no pod named {name} in the DataHub lab cluster fixture")


def attach_lab_rca(heading: str = "DataHub lab evidence") -> tuple[dict[str, Any], dict[str, Any]]:
    cluster = load("cluster.json")
    report = evaluate(cluster=cluster)
    with allure.step(heading):
        allure.attach(
            json.dumps(cluster, indent=2),
            name="cluster.json",
            attachment_type=allure.attachment_type.JSON,
        )
        allure.attach(
            "\n".join(pod_log_lines(cluster)) or "none",
            name="pod-error-log.txt",
            attachment_type=allure.attachment_type.TEXT,
        )
        allure.attach(
            json.dumps(report, indent=2),
            name="rca-report.json",
            attachment_type=allure.attachment_type.JSON,
        )
        allure.attach(
            format_report(report),
            name="rca-report.txt",
            attachment_type=allure.attachment_type.TEXT,
        )
    return cluster, report
