"""Allure steps + JSON attachments around FastAPI TestClient calls."""

from __future__ import annotations

import json
from typing import Any

import allure
from fastapi.testclient import TestClient


class ReportingClient:
    def __init__(self, inner: TestClient) -> None:
        self._inner = inner

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        with allure.step(f"{method} {url}"):
            response = self._inner.request(method, url, **kwargs)
            payload = kwargs.get("json")
            if payload is not None:
                allure.attach(
                    json.dumps(payload, indent=2),
                    name="request.json",
                    attachment_type=allure.attachment_type.JSON,
                )
            try:
                body = json.dumps(response.json(), indent=2)
                kind = allure.attachment_type.JSON
            except Exception:
                body = response.text
                kind = allure.attachment_type.TEXT
            allure.attach(
                body,
                name=f"{response.status_code} response",
                attachment_type=kind,
            )
            return response

    def get(self, url: str, **kwargs: Any) -> Any:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        return self.request("POST", url, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
