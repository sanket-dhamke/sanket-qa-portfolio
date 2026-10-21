from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect

from pages.console_page import ConsolePage

pytestmark = pytest.mark.ui


@pytest.mark.smoke
def test_console_starts_on_connect_hides_monitoring(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url, connect=False)
    expect(page.locator("#connect-gate")).to_be_visible()
    expect(page.locator("#monitor")).to_be_hidden()
    expect(
        page.get_by_text(
            "Click Connect to see the performance monitoring result for the DataHub application deployed on the production environment."
        )
    ).to_be_visible()
    expect(page.locator("#c-cluster")).to_have_value("datahub-lab-us-west-2")
    expect(page.locator("body")).not_to_contain_text("smtp.gmail.com")
    expect(page.locator("#cpu-chart")).to_be_hidden()


@pytest.mark.smoke
def test_console_connect_then_refresh_returns_to_connect(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    expect(page.locator("#monitor")).to_be_visible()
    page.reload()
    expect(page.locator("#connect-gate")).to_be_visible()
    expect(page.locator("#monitor")).to_be_hidden()


@pytest.mark.sanity
def test_console_email_preview_default_to_sanket(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.open_email_tab()
    expect(page.locator("#email-to")).to_have_value("sanket.dhamke@gmail.com")
    console.send_email_preview()
    expect(page.locator("#email-to-view")).to_have_text("sanket.dhamke@gmail.com")
    expect(page.locator("#email-body")).to_contain_text("smoke")
    expect(page.locator("#email-body")).to_contain_text("RCA")
    expect(page.locator("#email-log")).to_contain_text("preview sent")
    expect(page.locator("#email-log")).to_contain_text("SMTP=none")
    console.send_email_preview()
    expect(page.locator("#email-log")).to_contain_text("deduped On new issue")


@pytest.mark.sanity
def test_console_canned_oom_shows_handler_source(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.click_canned("Which pods are crashing or restarting after OOM?")
    console.expect_handler_chip("handler:pod_status")
    expect(page.locator("#log")).to_contain_text("OOMKilled")


@pytest.mark.sanity
def test_console_graphql_chip_is_knowledge_base(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.click_canned("What GraphQL mutation creates an ingestion source?")
    console.expect_kb_chip()


@pytest.mark.sanity
def test_console_enter_clears_question(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.ask("How many assets are there?")
    expect(page.locator("#q")).to_have_value("")
    expect(page.locator("#log")).to_contain_text("140")


@pytest.mark.sanity
def test_console_login_chip_shows_emuser(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.click_canned(
        "Test the login with username as emuser and password as empass"
    )
    expect(page.locator("#q")).to_have_value("")
    expect(page.locator("#log")).to_contain_text("urn:li:corpuser:emuser")
    console.expect_handler_chip("handler:login_api")


@pytest.mark.regression
def test_console_tools_tab_and_cpu_limit_label(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.expect_tools_tab()
    console.click_canned("List the lab tools")
    expect(page.locator('[data-testid="result-source"]').last).to_contain_text(
        "handler:tool_catalog"
    )
    expect(page.locator("#tab-tools")).to_be_visible()


@pytest.mark.regression
def test_console_postgres_ingest_opens_recipe_and_run_id(page, site_url: str) -> None:
    console = ConsolePage(page)
    console.open(site_url)
    console.submit_postgres_recipe()
    expect(page.locator("#gql-create")).to_contain_text("createIngestionSource")
    expect(page.locator("#cpu-chart")).to_be_visible()
