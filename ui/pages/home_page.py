from __future__ import annotations

from playwright.sync_api import Page, expect


class HomePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/index.html")

    def expect_lead_sdet(self) -> None:
        expect(self.page.get_by_role("heading", name="Sanket Dhamke")).to_be_visible()
        lede = self.page.locator(".lede")
        expect(lede).to_contain_text("Lead SDET")
        expect(lede).to_contain_text("AI-based, agentic QA")
        expect(lede).not_to_contain_text("Pune")
        expect(self.page.locator("main")).not_to_contain_text(
            "This site is an original public sample"
        )

    def expect_cards(self) -> None:
        cards = self.page.locator("section.cards a.card")
        expect(cards).to_have_count(3)
        expect(cards.nth(0).locator("h2")).to_have_text("Hybrid Agent")
        expect(cards.nth(1).locator("h2")).to_have_text("API Automation")
        expect(cards.nth(2).locator("h2")).to_have_text("UI Automation")
        expect(cards.nth(0)).to_have_attribute("href", "console.html")
        expect(cards.nth(1)).to_have_attribute("href", "api-framework.html")
        expect(cards.nth(2)).to_have_attribute("href", "ui-framework.html")
        expect(cards.nth(1)).not_to_contain_text("Playwright")
        expect(cards.nth(2)).to_contain_text("Playwright")
