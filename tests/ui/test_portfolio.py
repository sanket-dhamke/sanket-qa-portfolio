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
    expect(page.locator('[data-testid="result-source"]').last).to_contain_text("handler:pod_status")
    expect(page.locator("#log")).to_contain_text("OOMKilled")


def test_console_postgres_ingest_opens_recipe_and_run_id(page, site_url: str) -> None:
    page.goto(site_url + "/console.html")
    page.get_by_role("button", name="Ingest a postgres source").click()
    expect(page.locator("#ingest-panel")).to_be_visible()
    expect(page.locator("#recipe-yaml")).to_have_value(re.compile(r"type:\s*postgres"))
    page.get_by_role("button", name="Submit recipe (simulated GraphQL)").click()
    expect(page.locator("#run-id")).to_contain_text("urn:li:dataHubExecutionRequest:")
    expect(page.locator("#gql-create")).to_contain_text("createIngestionSource")
    expect(page.locator("#cpu-chart")).to_be_visible()
