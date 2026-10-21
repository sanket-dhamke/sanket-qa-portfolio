from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from utils.waits import wait_source_kind


class ConsolePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/console.html")

    def click_canned(self, name: str) -> None:
        self.page.get_by_role("button", name=name).click()

    def ask(self, text: str) -> None:
        box = self.page.locator("#q")
        box.fill(text)
        box.press("Enter")

    def expect_handler_chip(self, source: str) -> None:
        wait_source_kind(self.page, "Handler")
        expect(self.page.locator('[data-testid="result-source"]').last).to_contain_text(
            source
        )

    def expect_kb_chip(self) -> None:
        wait_source_kind(self.page, "Knowledge base")
        expect(self.page.locator('[data-testid="result-source"]').last).to_contain_text(
            "kb:"
        )

    def expect_tools_tab(self) -> None:
        expect(self.page.get_by_text("CPU % of pod limit (not node)")).to_be_visible()
        self.page.get_by_role("button", name="Tools", exact=True).click()
        expect(self.page.locator("#tool-table")).to_contain_text("gms_heap")

    def submit_postgres_recipe(self) -> None:
        self.click_canned("Ingest a postgres source")
        expect(self.page.locator("#ingest-panel")).to_be_visible()
        expect(self.page.locator("#recipe-yaml")).to_have_value(re.compile(r"type:\s*postgres"))
        self.page.get_by_role("button", name="Submit recipe (simulated GraphQL)").click()
        expect(self.page.locator("#run-id")).to_contain_text(
            "urn:li:dataHubExecutionRequest:"
        )
