from __future__ import annotations

import re

import pytest

pytest.importorskip("playwright.sync_api")

from playwright.sync_api import expect

pytestmark = pytest.mark.ui


def test_home_has_name_and_three_cards(page, site_url: str) -> None:
    page.goto(site_url + "/index.html")
    expect(page.get_by_role("heading", name="Sanket Dhamke")).to_be_visible()
    expect(page.get_by_role("link", name="Hybrid Agent")).to_be_visible()
    expect(page.get_by_role("link", name="API Automation")).to_be_visible()
    expect(page.get_by_role("link", name="UI Automation")).to_be_visible()


def test_console_canned_oom_shows_handler_source(page, site_url: str) -> None:
    page.goto(site_url + "/console.html")
    page.get_by_role("button", name="Which pods are crashing or restarting after OOM?").click()
    expect(page.locator('[data-testid="source-kind"]').last).to_contain_text("Handler")
    expect(page.locator('[data-testid="result-source"]').last).to_contain_text("handler:pod_status")
    expect(page.locator("#log")).to_contain_text("OOMKilled")


def test_console_graphql_chip_is_knowledge_base(page, site_url: str) -> None:
    page.goto(site_url + "/console.html")
    page.get_by_role("button", name="What GraphQL mutation creates an ingestion source?").click()
    expect(page.locator('[data-testid="source-kind"]').last).to_contain_text("Knowledge base")
    expect(page.locator('[data-testid="result-source"]').last).to_contain_text("kb:")


def test_console_enter_clears_question(page, site_url: str) -> None:
    page.goto(site_url + "/console.html")
    box = page.locator("#q")
    box.fill("How many assets are there?")
    box.press("Enter")
    expect(box).to_have_value("")
    expect(page.locator("#log")).to_contain_text("How many assets are there?")
    expect(page.locator("#log")).to_contain_text("140")


def test_console_login_chip_shows_emuser(page, site_url: str) -> None:
    page.goto(site_url + "/console.html")
    page.get_by_role(
        "button",
        name="Test the login with username as emuser and password as empass",
    ).click()
    expect(page.locator("#q")).to_have_value("")
    expect(page.locator("#log")).to_contain_text("urn:li:corpuser:emuser")
    expect(page.locator('[data-testid="result-source"]').last).to_contain_text(
        "handler:login_api"
    )


def test_console_tools_tab_and_cpu_limit_label(page, site_url: str) -> None:
    page.goto(site_url + "/console.html")
    expect(page.get_by_text("CPU % of pod limit (not node)")).to_be_visible()
    page.get_by_role("button", name="Tools", exact=True).click()
    expect(page.locator("#tool-table")).to_contain_text("gms_heap")
    expect(page.locator("#tool-table")).to_contain_text("does not query GMS GraphQL")
    expect(page.locator("#tool-table")).to_contain_text("not node capacity")
    page.get_by_role("button", name="List the lab tools").click()
    expect(page.locator('[data-testid="result-source"]').last).to_contain_text(
        "handler:tool_catalog"
    )
    expect(page.locator("#tab-tools")).to_be_visible()


def test_architecture_states_model_does_not_choose_tools(page, site_url: str) -> None:
    page.goto(site_url + "/architecture.html")
    expect(page.locator("main")).to_contain_text("Does not choose tools")
    expect(page.locator("main")).to_contain_text("Does not collect metrics")
    expect(page.locator("main")).to_contain_text("Does not set RCA")


def test_console_postgres_ingest_opens_recipe_and_run_id(page, site_url: str) -> None:
    page.goto(site_url + "/console.html")
    page.get_by_role("button", name="Ingest a postgres source").click()
    expect(page.locator("#ingest-panel")).to_be_visible()
    expect(page.locator("#recipe-yaml")).to_have_value(re.compile(r"type:\s*postgres"))
    page.get_by_role("button", name="Submit recipe (simulated GraphQL)").click()
    expect(page.locator("#run-id")).to_contain_text("urn:li:dataHubExecutionRequest:")
    expect(page.locator("#gql-create")).to_contain_text("createIngestionSource")
    expect(page.locator("#cpu-chart")).to_be_visible()
