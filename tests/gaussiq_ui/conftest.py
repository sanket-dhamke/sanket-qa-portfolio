"""Playwright + Allure labels for GaussIQ lab UI slices."""

from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import allure
import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

socketserver.TCPServer.allow_reuse_address = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@pytest.fixture(scope="session")
def site_url() -> str:
    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()


@pytest.fixture
def page():
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": 1440, "height": 1100})
        yield pg
        browser.close()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    allure.dynamic.epic("GaussIQ UI")
    allure.dynamic.tag("gaussiq")
    allure.dynamic.tag("ui")
    for mark in ("smoke", "sanity", "regression"):
        if item.get_closest_marker(mark):
            allure.dynamic.feature(mark)
            allure.dynamic.suite(mark)
            allure.dynamic.tag(mark)
            allure.dynamic.story(item.name)
            break
