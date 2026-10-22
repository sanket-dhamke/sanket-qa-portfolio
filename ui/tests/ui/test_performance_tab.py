"""Regression: Performance tab copy, table order, and no probe jargon."""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect

from pages.console_page import ConsolePage

pytestmark = pytest.mark.ui


@pytest.mark.regression
def test_performance_table_is_above_rca(page, site_url: str) -> None:
    ConsolePage(page).open(site_url)
    table = page.locator("#pod-table").bounding_box()
    rca = page.locator("#perf-rca").bounding_box()
    assert table and rca
    assert table["y"] < rca["y"]
    expect(page.locator("#pod-table")).to_contain_text("datahub-mae-consumer")
    expect(page.locator("#pod-table")).to_contain_text("CrashLoopBackOff")


@pytest.mark.regression
def test_performance_error_log_plain_language_no_http_000(page, site_url: str) -> None:
    ConsolePage(page).open(site_url)
    log = page.locator("#error-log")
    expect(log).to_contain_text(
        "datahub-mae-consumer — 7 restarts, killed for out of memory. "
        "Health check got no response because the process was already down."
    )
    expect(log).to_contain_text(
        "datahub-mce-consumer — 2 restarts (error). Health check is answering OK now."
    )
    expect(log).not_to_contain_text("HTTP 000")
    expect(log).not_to_contain_text("liveness probe")
    expect(page.locator("#tab-perf")).not_to_contain_text("HTTP 000")
    expect(page.locator("#tab-perf")).not_to_contain_text("HTTP/000")


@pytest.mark.regression
def test_performance_checked_not_the_cause(page, site_url: str) -> None:
    ConsolePage(page).open(site_url)
    rca = page.locator("#perf-rca")
    expect(rca).to_contain_text("Checked — not the cause")
    expect(rca).to_contain_text("Not a probe timeout")
    expect(rca).to_contain_text("datahub-mae-consumer ran out of memory")
    expect(rca).not_to_contain_text("not fired")
    expect(rca).not_to_contain_text("Evaluated, not fired")
    expect(rca).not_to_contain_text("A skipped rule is still a diagnosis")


@pytest.mark.regression
def test_console_rca_tab_plain_language(page, site_url: str) -> None:
    ConsolePage(page).open(site_url)
    page.get_by_role("button", name="RCA", exact=True).click()
    expect(page.locator("#tab-rca")).to_be_visible()
    expect(page.locator("#rca-list")).to_contain_text("Checked — not the cause")
    expect(page.locator("#rca-list")).to_contain_text("MEM-PRESSURE")
    expect(page.locator("#rca-list")).not_to_contain_text("HTTP 000")
    expect(page.locator("#rca-list")).not_to_contain_text("not fired")


@pytest.mark.regression
def test_console_capacity_tab(page, site_url: str) -> None:
    ConsolePage(page).open(site_url)
    page.get_by_role("button", name="Capacity").click()
    expect(page.locator("#tab-capacity")).to_be_visible()
    expect(page.locator("#tab-capacity")).to_contain_text("140-asset fixture")


@pytest.mark.regression
def test_console_email_subject_degraded(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.open_email_tab()
    console.send_email_preview()
    expect(page.locator("#email-subject")).to_contain_text("DEGRADED")
    expect(page.locator("#email-body")).not_to_contain_text("HTTP 000")
    expect(page.locator("#email-body")).to_contain_text("killed for out of memory")


@pytest.mark.regression
def test_console_suites_tab_after_sanity(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.ask("Run API sanity suite")
    expect(page.locator("#tab-suites")).to_be_visible()
    expect(page.locator("#suite-hint")).to_contain_text("sanity")
    expect(page.locator("#suite-hint")).to_contain_text("FAIL")


@pytest.mark.regression
def test_console_app_health_not_unknown_on_kpi(page, site_url: str) -> None:
    ConsolePage(page).open(site_url)
    expect(page.locator("#health-live")).to_have_text("DEGRADED")
    expect(page.locator("#health-live")).not_to_have_text("unknown")
    expect(page.locator("#health-live")).not_to_have_text("UNKNOWN")
