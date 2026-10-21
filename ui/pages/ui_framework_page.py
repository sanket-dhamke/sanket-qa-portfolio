from __future__ import annotations

import allure
from playwright.sync_api import Page, expect


class UiFrameworkPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    @allure.step("Open UI automation page")
    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/ui-framework.html")

    @allure.step("Expect UI tree and Allure link")
    def expect_ui_tree(self) -> None:
        expect(self.page.get_by_role("heading", name="UI automation")).to_be_visible()
        folder = self.page.locator("pre.folder")
        expect(folder).to_contain_text("pages/")
        expect(folder).to_contain_text("tests/ui/")
        expect(folder).not_to_contain_text("tests/payloads/")
        expect(folder).not_to_contain_text("tests/api/smoke")
        expect(self.page.get_by_role("link", name="Allure report")).to_have_attribute(
            "href", "reports/allure-ui/index.html"
        )
        expect(self.page.locator("main")).not_to_contain_text("pytest-html")
