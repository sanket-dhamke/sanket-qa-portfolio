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
    expect(page.locator('[data-testid="child-log"]')).to_contain_text("child agent ready")
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
    log = page.locator('[data-testid="child-log"]')
    expect(log).to_contain_text("Catalog read")
    expect(log).to_contain_text("no git pull")
    expect(log).to_contain_text("mae-consumer")
    expect(page.locator('[data-testid="child-job"]')).to_contain_text("Read only")
    expect(page.locator('[data-testid="child-job"]')).to_contain_text("git-pull")

    _ask(page, "Run API smoke")
    expect(log).to_contain_text("Pipeline job (write)")
    expect(log).to_contain_text("git_pull=false")
    expect(log).to_contain_text("credentials=none")
    expect(page.locator('[data-testid="child-job"]')).to_contain_text("Job recorded")
    expect(page.locator('[data-testid="child-job"]')).to_contain_text("git_pull=false")

    _ask(page, "any security issues?")
    expect(log).to_contain_text("child agent only answers API")
    expect(log).to_contain_text("lab console")

    UiFrameworkPage(page).open(site_url)
    chat = page.locator('[data-testid="child-chat"]')
    expect(chat).to_be_visible()
    expect(chat).to_have_attribute("data-layer", "ui")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text("child agent ready")
    _ask(page, "Why did UI sanity fail?")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text("Catalog read")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text("search")
    _ask(page, "Run UI smoke")
    expect(page.locator('[data-testid="child-job"]')).to_contain_text("Job recorded")
    expect(page.locator('[data-testid="child-job"]')).to_contain_text("git_pull=false")
    _ask(page, "Run API sanity suite")
    expect(page.locator('[data-testid="child-log"]')).to_contain_text(
        "child agent only answers UI"
    )
