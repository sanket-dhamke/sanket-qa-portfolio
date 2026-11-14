"""Playwright checks against the GaussIQ Pages lab (fixtures only)."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.ui


def _connect(page, site_url: str) -> None:
    page.goto(site_url + "/gaussiq.html?v=chat11", wait_until="networkidle")
    page.get_by_role("button", name="Connect").click()
    page.locator("#chat-panel").wait_for(state="visible")


@pytest.mark.smoke
def test_gaussiq_lab_loads_without_forbidden_brands(page, site_url: str) -> None:
    page.goto(site_url + "/gaussiq.html?v=chat11", wait_until="networkidle")
    expect(page.locator("#connect-gate")).to_be_visible()
    body = page.locator("body").inner_text()
    assert "Not affiliated with GaussIQ" in body
    assert "github.com/sanket-dhamke" not in body
    assert "BMC" not in body
    assert "Beacon" not in body


@pytest.mark.smoke
def test_gaussiq_connect_opens_cases_tab(page, site_url: str) -> None:
    _connect(page, site_url)
    expect(page.locator("#monitor")).to_be_visible()
    expect(page.locator('.extra .tab[data-tab="cases"]')).to_have_attribute("aria-selected", "true")
    expect(page.locator("#tab-cases")).to_be_visible()


@pytest.mark.sanity
def test_open_cases_kpi_selects_cases_tab(page, site_url: str) -> None:
    _connect(page, site_url)
    page.locator('[data-testid="kpi-last-suite"]').click()
    expect(page.locator('.extra .tab[data-tab="suites"]')).to_have_attribute("aria-selected", "true")
    page.locator('[data-testid="kpi-open-cases"]').click()
    expect(page.locator('.extra .tab[data-tab="cases"]')).to_have_attribute("aria-selected", "true")
    expect(page.locator("#tab-cases")).to_be_visible()


@pytest.mark.sanity
def test_golden_case_chip_shows_product_table(page, site_url: str) -> None:
    _connect(page, site_url)
    page.locator("#canned button").filter(has_text="golden-case").click()
    card = page.locator('[data-testid="product-card"]')
    expect(card).to_be_visible()
    expect(page.locator('[data-testid="product-headline"]')).to_contain_text(
        "Golden-case product suite passed (4/4)"
    )
    table = page.locator('[data-testid="product-table"]')
    expect(table).to_contain_text("RCA")
    expect(table).to_contain_text("Assignment")
    expect(table).to_contain_text("PASS")
    expect(page.locator('[data-testid="product-details"]')).to_contain_text("AJ18268")
    expect(page.locator('[data-testid="product-verdict"]')).to_contain_text(
        "matched the golden record"
    )
    link = page.locator('[data-testid="allure-link"]')
    expect(link).to_have_attribute("href", "reports/allure-gaussiq-api-product/index.html?v=a3")
    log = page.locator("#log")
    expect(log.locator(".msg").first).to_contain_text("Golden-case product suite")


@pytest.mark.sanity
def test_api_smoke_chip_opens_smoke_only_allure(page, site_url: str) -> None:
    _connect(page, site_url)
    page.locator("#canned button").filter(has_text="API smoke").click()
    link = page.locator('[data-testid="allure-link"]')
    expect(link).to_be_visible()
    expect(link).to_have_attribute("href", "reports/allure-gaussiq-api-smoke/index.html?v=a2")
    expect(link).to_contain_text("Open Allure report")
    expect(page.locator('[data-testid="suite-headline"]')).to_contain_text("API smoke passed (3/3)")


@pytest.mark.regression
def test_api_smoke_allure_is_real_allure_ui(page, site_url: str) -> None:
    _connect(page, site_url)
    page.locator("#canned button").filter(has_text="API smoke").click()
    with page.expect_popup() as pop:
        page.locator('[data-testid="allure-link"]').click()
    report = pop.value
    report.wait_for_load_state("domcontentloaded")
    html = report.content()
    assert "allureVersion" in html
    assert "__allureCoreLoaded" in html
    assert "<title>GaussIQ API smoke</title>" in html
    assert "This page stands in for an Allure slice" not in html
    assert "github.com/sanket-dhamke" not in html
    report.locator("text=Suites").first.wait_for(timeout=15000)
