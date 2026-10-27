"""The API and UI folder maps on GitHub Pages must match the repo."""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _allure_decoded(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    parts = [raw]
    for blob in re.findall(r"[A-Za-z0-9+/]{120,}={0,2}", raw):
        try:
            parts.append(base64.b64decode(blob).decode("utf-8", "ignore"))
        except Exception:
            continue
    return "\n".join(parts)

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
    "tests/api/sanity/test_mae_search_index.py",
    "tests/api/sanity/test_search_and_pods.py",
    "tests/api/smoke/test_gms_pod.py",
    "tests/helpers/lab_evidence.py",
    "tests/test_app_health.py",
    "tests/test_security.py",
    "tests/security/smoke/test_fixture.py",
    "tests/security/sanity/test_findings.py",
    "agent/security_engine.py",
    "agent/fixtures/security.json",
    "agent/fixtures/pipeline.json",
    "docs/js/child-chat.js",
    "tests/api/regression/test_login_failures.py",
    "tests/api/regression/test_graphql_unknown.py",
    "tests/api/regression/test_mock_gms_catalog.py",
    "utils/http.py",
    "utils/gms.py",
    "reports/README.md",
    "reports/allure-results/.gitkeep",
    "docs/API.md",
    "docs/api-framework.html",
    "docs/reports/allure-api/index.html",
    "scripts/generate_allure.sh",
    "scripts/write_suite_results.py",
    "scripts/write_suites_catalog.py",
    "docs/js/suite-results.json",
    "docs/js/suite-strip.js",
]

UI_PATHS = [
    "ui/pytest.ini",
    "ui/conftest.py",
    "ui/requirements.txt",
    "ui/config/.env.example",
    "ui/config/settings.py",
    "ui/utils/waits.py",
    "ui/utils/screenshots.py",
    "ui/utils/lab_evidence.py",
    "ui/pages/home_page.py",
    "ui/pages/console_page.py",
    "ui/pages/architecture_page.py",
    "ui/pages/api_page.py",
    "ui/pages/ui_framework_page.py",
    "ui/pages/about_page.py",
    "ui/tests/ui/test_home.py",
    "ui/tests/ui/test_console.py",
    "ui/tests/ui/test_search_index.py",
    "ui/tests/ui/test_architecture.py",
    "ui/tests/ui/test_framework_pages.py",
    "ui/tests/ui/test_performance_tab.py",
    "ui/tests/ui/test_pages.py",
    "ui/tests/ui/test_security.py",
    "ui/tests/ui/test_child_chat.py",
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
    assert "test_mae_search_index.py" in text
    assert "test_search_and_pods.py" in text
    assert "test_mock_gms_catalog.py" in text
    assert 'data-testid="suite-strip"' in text
    assert "tests/payloads/" in text
    assert "tests/helpers/" in text
    assert "allure-results" in text
    assert 'href="reports/allure-api/index.html">Allure report</a>' in text
    assert "Try this out — click here to see how it works." in text
    assert 'data-testid="try-this"' in text


def test_ui_page_does_not_document_api_payloads() -> None:
    text = (ROOT / "docs" / "ui-framework.html").read_text(encoding="utf-8")
    assert "tests/payloads/" not in text
    assert "tests/api/smoke" not in text
    assert "pages/" in text
    assert "Playwright" in text
    assert "test_search_index.py" in text
    assert "test_performance_tab.py" in text
    assert "about_page.py" in text
    assert 'data-testid="suite-strip"' in text
    assert "Try this out — click here to see how it works." in text
    assert "AI-AGENT.md" in text
    assert "SKILLS.md" in text
    assert "pytest-html" not in text
    assert 'href="reports/allure-ui/index.html">Allure report</a>' in text


def test_home_cards_split_api_and_ui() -> None:
    text = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    cards = text.split('class="cards"', 1)[1]
    hybrid = cards.split("Hybrid AI Agent for performance testing", 1)[1].split("</article>", 1)[0]
    api_card = cards.split("API Automation", 1)[1].split("</article>", 1)[0]
    ui_card = cards.split("UI Automation", 1)[1].split("</article>", 1)[0]
    assert 'href="console.html"' in hybrid
    assert 'href="api-framework.html"' in api_card
    assert 'href="ui-framework.html"' in ui_card
    assert "not an LLM inventing metrics" in hybrid
    assert "Playwright" not in hybrid
    assert "Playwright" not in api_card
    assert "tests/api/" in api_card
    assert "Playwright" in ui_card
    assert "ui/" in ui_card
    assert "tests/payloads" not in ui_card
    assert "Open the Hybrid AI Agent for performance testing" in text
    cta = "Try this out — click here to see how it works."
    assert cta in hybrid
    assert cta in api_card
    assert cta in ui_card
    assert 'data-testid="try-this-hybrid"' in hybrid
    assert 'data-testid="try-this-api"' in api_card
    assert 'data-testid="try-this-ui"' in ui_card


def test_api_allure_report_is_api_only() -> None:
    path = ROOT / "docs" / "reports" / "allure-api" / "index.html"
    report = path.read_text(encoding="utf-8", errors="ignore")
    decoded = _allure_decoded(path)
    assert "allure-report-uuid" in report
    assert "<title>API automation</title>" in report
    assert "Playwright" not in report
    assert "playwright" not in report.lower()
    assert "tests/ui/" not in report
    assert "test_portfolio" not in report
    assert "OOMKilled" in decoded
    assert "MEM-PRESSURE" in decoded
    assert "datahub-mae-consumer" in decoded
    assert "test_mae_consumer_ready_so_search_index_is_current" in decoded


def test_console_has_connect_gate_and_email_tab() -> None:
    text = (ROOT / "docs" / "console.html").read_text(encoding="utf-8")
    assert 'id="connect-gate"' in text
    assert "AKIADEMOEXAMPLEKEY12" in text
    assert "datahub-lab-us-west-2" in text
    assert "tenant-lab-demo" in text
    assert "sanket.dhamke@gmail.com" in text
    assert 'data-tab="email"' in text
    assert "Send preview now" in text
    assert "On new issue" in text
    assert "smtp.gmail.com" not in text.lower()
    assert "Playwright" not in text
    assert "how performance monitoring is done" not in text
    assert (
        "Click Connect to see the performance monitoring result for the DataHub "
        "application deployed on the production environment."
    ) in text
    assert 'id="perf-rca"' in text
    assert 'data-tab="security"' in text
    assert 'data-testid="qbank-toggle"' in text
    assert "Questions you can ask" in text
    assert "MEM-PRESSURE" in text
    assert 'data-testid="try-this"' in text
    assert "Try this out — click here to see how it works." in text
    js = (ROOT / "docs" / "js" / "console.js").read_text(encoding="utf-8")
    assert 'textContent = "unknown"' not in js
    assert "computeAppHealth" in (ROOT / "docs" / "js" / "router.js").read_text(encoding="utf-8")


def test_ui_allure_report_is_separate() -> None:
    path = ROOT / "docs" / "reports" / "allure-ui" / "index.html"
    report = path.read_text(encoding="utf-8", errors="ignore")
    decoded = _allure_decoded(path)
    assert "allure-report-uuid" in report
    assert "<title>UI automation</title>" in report
    assert "tests/payloads" not in report
    assert "OOMKilled" in decoded
    assert "MEM-PRESSURE" in decoded
    assert "datahub-mae-consumer" in decoded
    assert "test_ui_dataset_search_empty_while_mae_oom" in decoded


def _collect(args: list[str], cwd: Path) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in {0, 1}, proc.stdout + proc.stderr
    return sum(1 for line in proc.stdout.splitlines() if "::" in line and not line.startswith("E "))


def _catalog_count(layer: str, suite: str) -> int:
    cases = json.loads((ROOT / "agent" / "fixtures" / "suites.json").read_text(encoding="utf-8"))[
        "cases"
    ]
    return sum(1 for row in cases if row.get("layer") == layer and suite in row.get("suites", []))


def test_performance_table_is_above_rca_in_html() -> None:
    html = (ROOT / "docs" / "console.html").read_text(encoding="utf-8")
    assert html.find('id="pod-table"') < html.find('id="perf-rca"')
    assert html.find('id="error-log"') < html.find('id="perf-rca"')
    assert html.find('id="pod-table"') < html.find('id="error-log"')
    assert "Current issues / root cause" in html
    assert "HTTP 000" not in html
    assert "liveness probe" not in html


def test_console_js_plain_language_no_probe_jargon() -> None:
    js = (ROOT / "docs" / "js" / "console.js").read_text(encoding="utf-8")
    assert "stripProbeJargon" in js
    assert "podPlainLine" in js
    assert "killed for out of memory" in js
    assert "Health check got no response because the process was already down" in js
    assert "Health check is answering OK now" in js
    assert "Checked — not the cause" in js
    assert "not fired" not in js
    assert "Evaluated, not fired" not in js
    assert "A skipped rule is still a diagnosis" not in js


def test_api_and_ui_pyramids_match_catalog_and_collection() -> None:
    api = {
        "smoke": _collect(["tests/api", "-m", "smoke and not live"], ROOT),
        "sanity": _collect(["tests/api", "-m", "sanity"], ROOT),
        "regression": _collect(["tests/api", "-m", "regression"], ROOT),
    }
    ui = {
        "smoke": _collect(["-m", "smoke"], ROOT / "ui"),
        "sanity": _collect(["-m", "sanity"], ROOT / "ui"),
        "regression": _collect(["-m", "regression"], ROOT / "ui"),
    }
    assert api["smoke"] < api["sanity"] < api["regression"], api
    assert ui["smoke"] < ui["sanity"] < ui["regression"], ui
    for suite, count in api.items():
        assert _catalog_count("api", suite) == count
    for suite, count in ui.items():
        assert _catalog_count("ui", suite) == count
    results = json.loads((ROOT / "docs" / "js" / "suite-results.json").read_text(encoding="utf-8"))
    for suite, count in api.items():
        assert results["api"][suite]["tests"] == count
    for suite, count in ui.items():
        assert results["ui"][suite]["tests"] == count
    api_html = (ROOT / "docs" / "api-framework.html").read_text(encoding="utf-8")
    ui_html = (ROOT / "docs" / "ui-framework.html").read_text(encoding="utf-8")
    assert f">{api['smoke']}<" in api_html
    assert f">{api['sanity']}<" in api_html
    assert f">{api['regression']}<" in api_html
    assert f">{ui['smoke']}<" in ui_html
    assert f">{ui['sanity']}<" in ui_html
    assert f">{ui['regression']}<" in ui_html
    sec = {
        "smoke": _collect(["tests/security", "-m", "smoke"], ROOT),
        "sanity": _collect(["tests/security", "-m", "sanity"], ROOT),
    }
    assert sec["smoke"] < sec["sanity"], sec
    assert _catalog_count("security", "smoke") == sec["smoke"]
    assert _catalog_count("security", "sanity") == sec["sanity"]
    api_page = (ROOT / "docs" / "api-framework.html").read_text(encoding="utf-8")
    ui_page = (ROOT / "docs" / "ui-framework.html").read_text(encoding="utf-8")
    assert 'data-testid="child-chat"' in api_page
    assert 'data-layer="api"' in api_page
    assert 'data-testid="child-chat"' in ui_page
    assert 'data-layer="ui"' in ui_page
    js = "\n".join(
        (ROOT / "docs" / "js" / name).read_text(encoding="utf-8")
        for name in ("router.js", "console.js", "child-chat.js")
    )
    assert "git pull origin" not in js
    assert "git fetch origin" not in js
    assert "gitPull(" not in js
    assert "Open Allure report" in js
    assert "GitHub Pages does not spawn pytest" not in js
    assert "Pipeline job (write)" not in js
    child = (ROOT / "docs" / "js" / "child-chat.js").read_text(encoding="utf-8")
    assert "git_pull=false" not in child
    assert "route hello" not in child
    assert "source handler" not in child
    assert "Jenkins" not in child
    assert "Jenkins" not in api_page.split("child-chat", 1)[1].split("Folder map", 1)[0]
    assert "Jenkins" not in ui_page.split("child-chat", 1)[1].split("Folder map", 1)[0]
