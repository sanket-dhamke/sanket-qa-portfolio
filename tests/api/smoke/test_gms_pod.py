"""Smoke: GMS itself must be Running. mae-consumer OOM is a sanity/DEGRADED story."""

from __future__ import annotations

import json

import allure
import pytest

from tests.helpers.lab_evidence import attach_lab_rca, component_pod


@allure.severity(allure.severity_level.NORMAL)
@allure.description(
    "Smoke stays green while datahub-gms is Running. App health is CRITICAL only "
    "when smoke fails. mae-consumer OOMKilled belongs on sanity (DEGRADED), not here."
)
@pytest.mark.smoke
def test_gms_pod_running_matches_health_api() -> None:
    with allure.step("Read DataHub cluster fixture and rule RCA"):
        cluster, report = attach_lab_rca("GMS pod vs MEM-PRESSURE")
        gms = component_pod("datahub-gms", cluster)
        allure.attach(
            json.dumps(gms, indent=2),
            name="datahub-gms-pod.json",
            attachment_type=allure.attachment_type.JSON,
        )
        fired = [row["id"] for row in report["fired"]]
        assert "MEM-PRESSURE" in fired
    with allure.step("Expect datahub-gms Running and ready"):
        assert gms["status"] == "Running"
        assert gms["ready"] is True
        assert "oom" not in str(gms.get("last_reason") or "").lower()
        assert "crashloop" not in str(gms.get("status") or "").lower()
