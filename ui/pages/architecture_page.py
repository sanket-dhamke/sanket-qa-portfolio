from __future__ import annotations

from playwright.sync_api import Page, expect


class ArchitecturePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/architecture.html")

    def expect_ai_boundary(self) -> None:
        main = self.page.locator("main")
        expect(main).to_contain_text("Does not choose tools")
        expect(main).to_contain_text("Does not collect metrics")
        expect(main).to_contain_text("Does not set RCA")
