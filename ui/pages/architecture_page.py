from __future__ import annotations

import allure
from playwright.sync_api import Page, expect


class ArchitecturePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    @allure.step("Open architecture page")
    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/architecture.html")

    @allure.step("Expect AI boundary and performance-agent title")
    def expect_ai_boundary(self) -> None:
        expect(
            self.page.get_by_role(
                "heading", name="Hybrid AI Agent for performance testing"
            )
        ).to_be_visible()
        main = self.page.locator("main")
        expect(main).to_contain_text("Does not choose tools")
        expect(main).to_contain_text("Does not collect metrics")
        expect(main).to_contain_text("Does not set RCA")
        expect(main).to_contain_text("not an LLM inventing metrics")
