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
        resume_pdf = "Sanket_Dhamke_AI_Quality_Automation_Engineer_Resume.pdf"
        cover_pdf = "Sanket_Dhamke_AI_Quality_Automation_Engineer_Cover_Letter.pdf"
        view_resume = self.page.locator('[data-testid="view-resume"]')
        view_cover = self.page.locator('[data-testid="view-cover-letter"]')
        resume = self.page.locator('[data-testid="download-resume"]')
        cover = self.page.locator('[data-testid="download-cover-letter"]')
        expect(view_resume).to_have_text("View resume")
        expect(view_cover).to_have_text("View cover letter")
        expect(view_resume).to_have_attribute("href", resume_pdf)
        expect(view_cover).to_have_attribute("href", cover_pdf)
        expect(view_resume).to_have_attribute("target", "_blank")
        expect(view_cover).to_have_attribute("target", "_blank")
        expect(view_resume).to_have_attribute("rel", "noopener")
        expect(view_cover).to_have_attribute("rel", "noopener")
        expect(view_resume).not_to_have_attribute("download")
        expect(view_cover).not_to_have_attribute("download")
        expect(resume).to_have_text("Download resume")
        expect(cover).to_have_text("Download cover letter")
        expect(resume).to_have_attribute("href", resume_pdf)
        expect(cover).to_have_attribute("href", cover_pdf)
        expect(resume).to_have_attribute("download", resume_pdf)
        expect(cover).to_have_attribute("download", cover_pdf)
