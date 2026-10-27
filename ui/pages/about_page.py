from __future__ import annotations

import allure
from playwright.sync_api import Page, expect


class AboutPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    @allure.step("Open about page")
    def open(self, site_url: str) -> None:
        self.page.goto(site_url + "/about.html")

    @allure.step("Expect about copy is a lab, not a live cluster")
    def expect_lab_disclaimer(self) -> None:
        expect(self.page.get_by_role("heading", name="About")).to_be_visible()
        main = self.page.locator("main")
        expect(main).to_contain_text("Not a hosted DataHub cloud")
        expect(main).to_contain_text("Not an LLM demo")
        expect(self.page.locator("footer")).to_contain_text("no live cluster")
        resume = self.page.locator('[data-testid="download-resume"]')
        cover = self.page.locator('[data-testid="download-cover-letter"]')
        expect(resume).to_have_text("Download resume")
        expect(cover).to_have_text("Download cover letter")
        expect(resume).to_have_attribute(
            "href", "Sanket_Dhamke_AI_Quality_Automation_Engineer_Resume.pdf"
        )
        expect(cover).to_have_attribute(
            "href", "Sanket_Dhamke_AI_Quality_Automation_Engineer_Cover_Letter.pdf"
        )
