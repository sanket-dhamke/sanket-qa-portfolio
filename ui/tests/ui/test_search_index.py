from __future__ import annotations

import json

import allure
import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect

from pages.console_page import ConsolePage
from utils.lab_evidence import attach_lab_rca, component_pod


pytestmark = pytest.mark.ui


@pytest.mark.sanity
def test_console_app_health_and_performance_rca(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    expect(page.locator("#health-live")).not_to_have_text("unknown")
    expect(page.locator("#health-live")).not_to_have_text("—")
    expect(page.locator("#health-live")).to_have_text("DEGRADED")
    expect(page.locator("#tab-perf")).to_be_visible()
    expect(page.locator("#perf-rca")).to_contain_text("MEM-PRESSURE")
    expect(page.locator("#perf-rca")).to_contain_text("OOMKilled")
    expect(page.locator("#perf-rca")).to_contain_text("PROBE-KILL")
    expect(page.locator("#pod-body")).to_contain_text("datahub-mae-consumer")
    expect(page.locator("#pod-body")).to_contain_text("CrashLoopBackOff")


@pytest.mark.sanity
@pytest.mark.lab_issue
def test_ui_dataset_search_empty_while_mae_oom(page, site_url: str) -> None:
    with allure.step("Attach DataHub cluster fixture and rule RCA"):
        cluster, report = attach_lab_rca()
        mae = component_pod("datahub-mae-consumer", cluster)
        allure.attach(
            json.dumps(mae, indent=2),
            name="datahub-mae-consumer-pod.json",
            attachment_type=allure.attachment_type.JSON,
        )
        fired = [row["id"] for row in report["fired"]]
        assert "MEM-PRESSURE" in fired
    console = ConsolePage(page)
    console.open(site_url)
    expect(page.locator("#health-live")).to_have_text("DEGRADED")
    expect(page.locator("#perf-rca")).to_contain_text("MEM-PRESSURE")
    png = page.locator("#tab-perf").screenshot()
    allure.attach(png, name="performance-tab-rca", attachment_type=allure.attachment_type.PNG)
    pytest.fail(
        "UI dataset search is empty while datahub-mae-consumer is "
        f"{mae.get('status')} last_reason={mae.get('last_reason')} restarts={mae.get('restarts')} "
        "(MEM-PRESSURE; PROBE-KILL skipped). App health is DEGRADED. "
        "GMS counts still look fine — this is not a frontend selector bug."
    )
