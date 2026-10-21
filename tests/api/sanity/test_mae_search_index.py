"""Sanity fails on the live mae-consumer OOM fixture — same RCA as App health."""

from __future__ import annotations

import json

import allure
import pytest

from tests.helpers.lab_evidence import attach_lab_rca, component_pod


@allure.severity(allure.severity_level.CRITICAL)
@allure.description(
    "Search index freshness depends on datahub-mae-consumer applying MetadataAuditEvent_v4. "
    "This DataHub lab fixture has mae-consumer CrashLoopBackOff / OOMKilled. "
    "MEM-PRESSURE fires; PROBE-KILL is skipped because last_reason is OOMKilled. "
    "App health is DEGRADED. GMS /health (smoke) still passes — do not treat that as an all-clear."
)
@pytest.mark.sanity
@pytest.mark.lab_issue
def test_mae_consumer_ready_so_search_index_is_current() -> None:
    with allure.step("Load DataHub cluster fixture, pod logs, and rule RCA"):
        cluster, report = attach_lab_rca()
        mae = component_pod("datahub-mae-consumer", cluster)
        allure.attach(
            json.dumps(mae, indent=2),
            name="datahub-mae-consumer-pod.json",
            attachment_type=allure.attachment_type.JSON,
        )
    with allure.step("MEM-PRESSURE must fire; PROBE-KILL must be skipped"):
        fired = {row["id"]: row for row in report["fired"]}
        skipped = {row["id"]: row["why"] for row in report["skipped"]}
        assert "MEM-PRESSURE" in fired
        assert fired["MEM-PRESSURE"]["severity"] == "CRITICAL"
        assert "OOMKilled" in " ".join(fired["MEM-PRESSURE"].get("evidence") or []) or (
            "OOMKilled" in fired["MEM-PRESSURE"]["observation"]
        )
        assert "PROBE-KILL" in skipped
        assert "OOMKilled" in skipped["PROBE-KILL"]
    with allure.step("Expect mae-consumer Running so search documents stay current"):
        assert mae["status"] == "Running", (
            "datahub-mae-consumer is "
            f"{mae.get('status')} last_reason={mae.get('last_reason')} "
            f"restarts={mae.get('restarts')} (MEM-PRESSURE). "
            "App health is DEGRADED; UI/API search cannot be treated as current."
        )
        assert mae.get("ready") is True
        assert not str(mae.get("last_reason") or "").lower().startswith("oom")
