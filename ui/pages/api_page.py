from __future__ import annotations

import allure
from playwright.sync_api import Page, expect


class ApiFrameworkPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    @allure.step("Open API automation page")
    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/api-framework.html")

    @allure.step("Expect API-only folder map and Allure link")
    def expect_api_only(self) -> None:
        expect(self.page.get_by_role("heading", name="API automation")).to_be_visible()
        expect(self.page.locator("main")).not_to_contain_text("Playwright")
        expect(self.page.locator("main")).not_to_contain_text("pages/home_page.py")
        expect(self.page.locator("pre.folder")).to_contain_text("tests/api/smoke/")
        expect(self.page.get_by_role("link", name="Allure report")).to_have_attribute(
            "href", "reports/allure-api/index.html"
        )
        expect(self.page.locator("main")).not_to_contain_text("pytest-html")
