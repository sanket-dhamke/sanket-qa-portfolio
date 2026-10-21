"""The API and UI folder maps on GitHub Pages must match the repo."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

API_PATHS = [
    "pytest.ini",
    "requirements.txt",
    "requirements-api.txt",
    "tests/conftest.py",
    "config/.env.example",
    "config/settings.py",
    "tests/helpers/auth.py",
    "tests/helpers/graphql.py",
    "tests/helpers/reporting.py",
    "tests/payloads/login.json",
    "tests/payloads/create_ingestion_source.json",
    "tests/payloads/postgres_recipe.yml",
    "tests/payloads/list_incidents.json",
    "tests/payloads/ingest_proposal.json",
    "tests/api/conftest.py",
    "tests/api/smoke/test_health.py",
    "tests/api/smoke/test_login.py",
    "tests/api/smoke/test_list_sources.py",
    "tests/api/smoke/test_live_requests.py",
    "tests/api/sanity/test_ingestion.py",
    "tests/api/sanity/test_incidents.py",
    "tests/api/sanity/test_aspects.py",
    "tests/api/regression/test_login_failures.py",
    "tests/api/regression/test_graphql_unknown.py",
    "utils/http.py",
    "utils/gms.py",
    "reports/README.md",
    "reports/allure-results/.gitkeep",
    "docs/API.md",
    "docs/api-framework.html",
    "docs/reports/allure-api/index.html",
    "scripts/generate_allure.sh",
]

UI_PATHS = [
    "ui/pytest.ini",
    "ui/conftest.py",
    "ui/requirements.txt",
    "ui/config/.env.example",
    "ui/config/settings.py",
    "ui/utils/waits.py",
    "ui/utils/screenshots.py",
    "ui/pages/home_page.py",
    "ui/pages/console_page.py",
    "ui/pages/architecture_page.py",
    "ui/pages/api_page.py",
    "ui/pages/ui_framework_page.py",
    "ui/tests/ui/test_home.py",
    "ui/tests/ui/test_console.py",
    "ui/tests/ui/test_architecture.py",
    "ui/tests/ui/test_framework_pages.py",
    "ui/AI-AGENT.md",
    "ui/SKILLS.md",
    "ui/README.md",
    "ui/reports/README.md",
    "ui/reports/allure-results/.gitkeep",
    ".cursor/skills/ui-automation/SKILL.md",
    "docs/ui-framework.html",
    "docs/reports/allure-ui/index.html",
]


def test_api_tree_is_real() -> None:
    missing = [p for p in API_PATHS if not (ROOT / p).exists()]
    assert missing == [], missing


def test_ui_tree_is_real() -> None:
    missing = [p for p in UI_PATHS if not (ROOT / p).exists()]
    assert missing == [], missing


def test_api_page_does_not_document_playwright() -> None:
    text = (ROOT / "docs" / "api-framework.html").read_text(encoding="utf-8")
    assert "Playwright" not in text
    assert "tests/ui/" not in text
    assert "pages/home_page.py" not in text
    assert "pytest-html" not in text
    assert "tests/api/smoke/" in text
    assert "tests/payloads/" in text
    assert "tests/helpers/" in text
    assert "allure-results" in text
    assert 'href="reports/allure-api/index.html">Allure report</a>' in text


def test_ui_page_does_not_document_api_payloads() -> None:
    text = (ROOT / "docs" / "ui-framework.html").read_text(encoding="utf-8")
    assert "tests/payloads/" not in text
    assert "tests/api/smoke" not in text
    assert "pages/" in text
    assert "Playwright" in text
    assert "AI-AGENT.md" in text
    assert "SKILLS.md" in text
    assert "pytest-html" not in text
    assert 'href="reports/allure-ui/index.html">Allure report</a>' in text


def test_home_cards_split_api_and_ui() -> None:
    text = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    cards = text.split('class="cards"', 1)[1]
    hybrid = cards.split("Hybrid AI Agent for performance testing", 1)[1].split("</a>", 1)[0]
    api_card = cards.split("API Automation", 1)[1].split("</a>", 1)[0]
    ui_card = cards.split("UI Automation", 1)[1].split("</a>", 1)[0]
    assert 'href="api-framework.html"' in cards
    assert 'href="ui-framework.html"' in cards
    assert "not an LLM inventing metrics" in hybrid
    assert "Playwright" not in hybrid
    assert "Playwright" not in api_card
    assert "tests/api/" in api_card
    assert "Playwright" in ui_card
    assert "ui/" in ui_card
    assert "tests/payloads" not in ui_card
    assert "Open the Hybrid AI Agent for performance testing" in text


def test_api_allure_report_is_api_only() -> None:
    report = (ROOT / "docs" / "reports" / "allure-api" / "index.html").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "allure-report-uuid" in report
    assert "<title>API automation</title>" in report
    assert "Playwright" not in report
    assert "playwright" not in report.lower()
    assert "tests/ui/" not in report
    assert "test_portfolio" not in report


def test_ui_allure_report_is_separate() -> None:
    report = (ROOT / "docs" / "reports" / "allure-ui" / "index.html").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "allure-report-uuid" in report
    assert "<title>UI automation</title>" in report
    assert "tests/payloads" not in report
