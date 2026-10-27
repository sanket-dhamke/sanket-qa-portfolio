"""Question bank copy + security chat on the lab console."""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect

from pages.console_page import ConsolePage

pytestmark = pytest.mark.ui


@pytest.mark.sanity
def test_question_bank_copies_without_auto_ask(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    page.locator('[data-testid="qbank-toggle"]').click()
    bank = page.locator('[data-testid="qbank"]')
    expect(bank).to_be_visible()
    expect(bank).to_contain_text("App health")
    expect(bank).to_contain_text("Security")
    expect(bank).to_contain_text("any security issues?")
    expect(bank).to_contain_text("Email / schedule")
    copy = bank.locator('[data-testid="qbank-copy"]').first
    copy.click()
    expect(copy).to_contain_text("Copied")
    expect(page.locator("#q")).to_have_value("")
    expect(page.locator("#log .msg.user")).to_have_count(0)


@pytest.mark.regression
def test_security_chat_and_tab(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.ask("any security issues?")
    log = page.locator("#log")
    expect(log).to_contain_text("AUTH-OPEN")
    expect(log).to_contain_text("SECRET-IN-LOG")
    expect(log).to_contain_text("Checked — not the cause")
    expect(log).to_contain_text("dh_lab_****redacted****")
    expect(page.locator('[data-testid="result-source"]').last).to_contain_text(
        "handler:security_rca"
    )
    expect(log).not_to_contain_text("not fired")
    expect(log).not_to_contain_text("HTTP 000")
    expect(log).not_to_contain_text("CVE-20")
    expect(page.locator("#tab-security")).to_be_visible()
    findings = page.locator('[data-testid="sec-findings"]')
    rca = page.locator('[data-testid="sec-rca"]')
    expect(findings).to_contain_text("AUTH-OPEN")
    expect(rca).to_contain_text("Checked — not the cause")
    box_f = findings.bounding_box()
    box_r = rca.bounding_box()
    assert box_f and box_r
    assert box_f["y"] < box_r["y"]
    console.ask("why is GMS exposed?")
    expect(log).to_contain_text("GMS is reachable without signing in")
