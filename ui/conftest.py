from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import allure
import pytest

ROOT = Path(__file__).resolve().parent
DOCS = ROOT.parent / "docs"

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


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    allure.dynamic.epic("UI automation")
    allure.dynamic.suite("ui/tests/ui")
    for mark in ("smoke", "sanity", "regression", "ui"):
        if item.get_closest_marker(mark):
            allure.dynamic.feature(mark)
            allure.dynamic.tag(mark)
    allure.dynamic.story(item.name)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return
    page = item.funcargs.get("page")
    if page is None:
        return
    png = page.screenshot(full_page=True)
    allure.attach(png, name=item.name, attachment_type=allure.attachment_type.PNG)
    if report.failed:
        from utils.screenshots import save

        save(page, item.name)
