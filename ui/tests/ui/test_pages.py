"""Regression: public pages and suite-result strips."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect

from pages.about_page import AboutPage
from pages.api_page import ApiFrameworkPage
from pages.architecture_page import ArchitecturePage
from pages.home_page import HomePage
from pages.ui_framework_page import UiFrameworkPage

pytestmark = pytest.mark.ui


@pytest.mark.regression
def test_ui_framework_shows_suite_strip(page, site_url: str) -> None:
    view = UiFrameworkPage(page)
    view.open(site_url)
    view.expect_suite_strip()
    strip = page.locator('[data-testid="suite-strip"]')
    smoke = int(strip.locator('[data-suite="smoke"] [data-count]').inner_text())
    sanity = int(strip.locator('[data-suite="sanity"] [data-count]').inner_text())
    regression = int(strip.locator('[data-suite="regression"] [data-count]').inner_text())
    assert smoke < sanity < regression


@pytest.mark.regression
def test_api_framework_shows_suite_strip(page, site_url: str) -> None:
    view = ApiFrameworkPage(page)
    view.open(site_url)
    view.expect_suite_strip()
    strip = page.locator('[data-testid="suite-strip"]')
    smoke = int(strip.locator('[data-suite="smoke"] [data-count]').inner_text())
    sanity = int(strip.locator('[data-suite="sanity"] [data-count]').inner_text())
    regression = int(strip.locator('[data-suite="regression"] [data-count]').inner_text())
    assert smoke < sanity < regression


@pytest.mark.regression
def test_about_page_is_not_a_live_cluster(page, site_url: str) -> None:
    about = AboutPage(page)
    about.open(site_url)
    about.expect_lab_disclaimer()


@pytest.mark.regression
def test_home_nav_to_console(page, site_url: str) -> None:
    HomePage(page).open(site_url)
    page.get_by_role("link", name="Open the Hybrid AI Agent for performance testing").click()
    expect(page).to_have_url(re.compile(r"console\.html"))
    expect(page.locator("#connect-gate")).to_be_visible()


@pytest.mark.regression
def test_architecture_footer_simulated(page, site_url: str) -> None:
    ArchitecturePage(page).open(site_url)
    expect(page.locator("footer")).to_contain_text("simulated")
    expect(page.locator("main")).to_contain_text("Does not set RCA")


@pytest.mark.regression
def test_ui_framework_allure_link_separate(page, site_url: str) -> None:
    UiFrameworkPage(page).open(site_url)
    expect(page.get_by_role("link", name="Allure report")).to_have_attribute(
        "href", "reports/allure-ui/index.html"
    )
    expect(page.locator("main")).not_to_contain_text("reports/allure-api")
