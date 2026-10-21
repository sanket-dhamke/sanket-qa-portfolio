from __future__ import annotations

import http.server
import socketserver
import threading
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[2] / "docs"


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
