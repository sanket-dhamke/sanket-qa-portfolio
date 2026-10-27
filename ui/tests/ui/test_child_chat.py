"""API and UI pages host scoped child agents of the lab console router."""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect

from pages.api_page import ApiFrameworkPage
from pages.ui_framework_page import UiFrameworkPage

pytestmark = pytest.mark.ui


def _ask(page, text: str) -> None:
    box = page.locator('[data-testid="child-q"]')
    box.fill(text)
    box.press("Enter")


@pytest.mark.regression
def test_api_and_ui_child_chats_scoped_pipeline(page, site_url: str) -> None:
    ApiFrameworkPage(page).open(site_url)
    chat = page.locator('[data-testid="child-chat"]')
    expect(chat).to_be_visible()
    expect(chat).to_have_attribute("data-layer", "api")
    log = page.locator('[data-testid="child-log"]')
    expect(log).to_contain_text("API agent ready")
    expect(log).not_to_contain_text("source handler")
    expect(log).not_to_contain_text("route hello")
    expect(log).not_to_contain_text("git_pull")
    expect(log).not_to_contain_text("Jenkins")
    page.locator('[data-testid="qbank-toggle"]').click()
    bank = page.locator('[data-testid="qbank"]')
    expect(bank).to_be_visible()
    expect(bank).to_contain_text("Run API smoke")
    expect(bank).to_contain_text("Why did API sanity fail?")
    copy = bank.locator('[data-testid="qbank-copy"]').first
    copy.click()
    expect(copy).to_contain_text("Copied")
    expect(page.locator('[data-testid="child-q"]')).to_have_value("")

    _ask(page, "Why did API sanity fail?")
    expect(log).to_contain_text("API sanity failed (11/12)")
    expect(log).to_contain_text("mae-consumer")
    expect(log).to_contain_text("Catalog replay")
    expect(log).not_to_contain_text("Catalog read")
    expect(log).not_to_contain_text("git_pull")
    expect(page.locator('[data-testid="allure-link"]').first).to_have_attribute(
        "href", "reports/allure-api-sanity/index.html"
    )
    expect(page.locator('[data-testid="allure-link"]').first).to_contain_text(
        "Open Allure report"
    )

    _ask(page, "Run API smoke")
    expect(log).to_contain_text("API smoke passed (6/6)")
    expect(log).to_contain_text("GMS GET /health")
    expect(log).to_contain_text("Open Allure report")
    expect(log).to_contain_text("Catalog replay")
    expect(log).not_to_contain_text("Pipeline job")
    expect(log).not_to_contain_text("git_pull")
    expect(log).not_to_contain_text("Jenkins")
    expect(log).not_to_contain_text("handler:run_suite")
    expect(log).not_to_contain_text("GitHub Pages does not spawn")
    expect(page.locator('[data-testid="child-job"]')).to_contain_text("Open Allure report")
    expect(page.locator('[data-testid="child-job"]')).not_to_contain_text("git_pull")
    expect(page.locator('[data-testid="child-job"] a[data-testid="allure-link"]')).to_have_attribute(
        "href", "reports/allure-api-smoke/index.html"
    )

    _ask(page, "any security issues?")
    expect(log).to_contain_text("child agent only answers API")
    expect(log).to_contain_text("lab console")
    expect(log).not_to_contain_text("Jenkins")

    UiFrameworkPage(page).open(site_url)
    chat = page.locator('[data-testid="child-chat"]')
    expect(chat).to_be_visible()
    expect(chat).to_have_attribute("data-layer", "ui")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text("UI agent ready")
    _ask(page, "Why did UI sanity fail?")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text("UI sanity failed")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text("search")
    expect(page.locator('[data-testid="allure-link"]').first).to_have_attribute(
        "href", "reports/allure-ui-sanity/index.html"
    )
    _ask(page, "Run UI smoke")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text("UI smoke passed")
    expect(page.locator('[data-testid="child-job"]')).to_contain_text("Open Allure report")
    expect(page.locator('[data-testid="child-job"]')).not_to_contain_text("git_pull")
    expect(page.locator('[data-testid="child-job"] a[data-testid="allure-link"]')).to_have_attribute(
        "href", "reports/allure-ui-smoke/index.html"
    )
    _ask(page, "Run API sanity suite")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text(
        "child agent only answers UI"
    )
