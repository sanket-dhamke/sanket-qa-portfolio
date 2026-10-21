from __future__ import annotations

from playwright.sync_api import Page, expect


class ApiFrameworkPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/api-framework.html")

    def expect_api_only(self) -> None:
        expect(self.page.get_by_role("heading", name="API automation")).to_be_visible()
        expect(self.page.locator("main")).not_to_contain_text("Playwright")
        expect(self.page.locator("main")).not_to_contain_text("pages/home_page.py")
        expect(self.page.locator("pre.folder")).to_contain_text("tests/api/smoke/")
