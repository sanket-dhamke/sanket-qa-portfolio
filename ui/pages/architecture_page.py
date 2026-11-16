from __future__ import annotations

import allure
from playwright.sync_api import Page, expect


class ArchitecturePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    @allure.step("Open architecture page")
    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/architecture.html?v=arch1")

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
        expect(self.page.locator('[data-testid="try-this"]')).to_have_attribute(
            "href", "console.html"
        )
        expect(self.page.locator('[data-testid="try-this"]')).to_have_text(
            "Try this out — click here to see how it works."
        )
        diagram = self.page.locator('[data-testid="architecture-diagram"]')
        expect(diagram).to_be_visible()
        expect(diagram).to_contain_text("Model never picks the tool or the metric.")
        expect(diagram).to_contain_text("User question / chat")
        expect(diagram).to_contain_text("Keyword / hybrid router")
        expect(diagram).to_contain_text("Handlers + fixture JSON")
        expect(diagram).to_contain_text("KB + API catalog")
        expect(diagram).to_contain_text("Suite executor")
        expect(diagram).to_contain_text("Rule RCA + security engine")
        expect(diagram).to_contain_text("Deterministic fallback")
        expect(diagram).to_contain_text("ask before full regression")
        expect(diagram).to_contain_text("Child API agent")
        expect(diagram).to_contain_text("Child UI agent")
        expect(diagram).to_contain_text("Source chips on every answer")
        expect(diagram).to_contain_text("Optional model last hop")
        expect(diagram).to_contain_text("Email notification")
        expect(diagram).not_to_contain_text("GaussIQ")
