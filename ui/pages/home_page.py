from __future__ import annotations

import allure
from playwright.sync_api import Page, expect


class HomePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    @allure.step("Open home")
    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/index.html")

    @allure.step("Expect Lead SDET intro")
    def expect_lead_sdet(self) -> None:
        expect(self.page.get_by_role("heading", name="Sanket Dhamke")).to_be_visible()
        lede = self.page.locator(".lede")
        expect(lede).to_contain_text("Lead SDET")
        expect(lede).to_contain_text("AI-based, agentic QA")
        expect(lede).not_to_contain_text("Pune")
        expect(self.page.locator("main")).not_to_contain_text(
            "This site is an original public sample"
        )

    @allure.step("Expect home cards")
    def expect_cards(self) -> None:
        cards = self.page.locator("section.cards .card")
        expect(cards).to_have_count(3)
        expect(cards.nth(0).locator("h2")).to_have_text(
            "Hybrid AI Agent for performance testing"
        )
        expect(cards.nth(1).locator("h2")).to_have_text("API Automation")
        expect(cards.nth(2).locator("h2")).to_have_text("UI Automation")
        expect(cards.nth(0).locator("a.try-this")).to_have_attribute("href", "console.html")
        expect(cards.nth(1).locator("a.try-this")).to_have_attribute(
            "href", "api-framework.html"
        )
        expect(cards.nth(2).locator("a.try-this")).to_have_attribute(
            "href", "ui-framework.html"
        )
        expect(cards.nth(1)).not_to_contain_text("Playwright")
        expect(cards.nth(2)).to_contain_text("Playwright")
        cta = "Try this out — click here to see how it works."
        expect(cards.nth(0).get_by_role("link", name=cta)).to_be_visible()
        expect(cards.nth(1).get_by_role("link", name=cta)).to_be_visible()
        expect(cards.nth(2).get_by_role("link", name=cta)).to_be_visible()
        expect(
            self.page.get_by_role(
                "link", name="Open the Hybrid AI Agent for performance testing"
            )
        ).to_be_visible()
        about = self.page.locator('[data-testid="about-downloads"]')
        expect(about).to_be_visible()
        expect(about.get_by_role("heading", name="About")).to_be_visible()
        expect(about.locator('[data-testid="download-resume"]')).to_have_text(
            "Download resume"
        )
        expect(about.locator('[data-testid="download-cover-letter"]')).to_have_text(
            "Download cover letter"
        )
        expect(about.locator('[data-testid="download-resume"]')).to_have_attribute(
            "href", "Sanket_Dhamke_AI_Quality_Automation_Engineer_Resume.pdf"
        )
        expect(about.locator('[data-testid="download-cover-letter"]')).to_have_attribute(
            "href", "Sanket_Dhamke_AI_Quality_Automation_Engineer_Cover_Letter.pdf"
        )
