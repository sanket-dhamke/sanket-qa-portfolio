"""Playwright waits used by page objects."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


def wait_visible(locator: Locator) -> None:
    expect(locator).to_be_visible()


def wait_source_kind(page: Page, text: str) -> None:
    expect(page.locator('[data-testid="source-kind"]').last).to_contain_text(text)
