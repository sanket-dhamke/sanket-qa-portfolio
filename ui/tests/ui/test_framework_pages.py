from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from pages.api_page import ApiFrameworkPage
from pages.ui_framework_page import UiFrameworkPage

pytestmark = pytest.mark.ui


@pytest.mark.sanity
def test_api_page_is_api_only(page, site_url: str) -> None:
    api = ApiFrameworkPage(page)
    api.open(site_url)
    api.expect_api_only()


@pytest.mark.sanity
def test_ui_page_shows_ui_tree_not_api_payloads(page, site_url: str) -> None:
    ui = UiFrameworkPage(page)
    ui.open(site_url)
    ui.expect_ui_tree()
