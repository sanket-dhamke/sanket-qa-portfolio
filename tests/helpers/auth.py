"""Login payloads for the mock DataHub GMS `/logIn` route."""

from __future__ import annotations

from typing import Any

from config.settings import LAB_PASSWORD, LAB_USER


def login_body(username: str | None = None, password: str | None = None) -> dict[str, str]:
    return {
        "username": username if username is not None else LAB_USER,
        "password": password if password is not None else LAB_PASSWORD,
    }


def assert_emuser_session(body: dict[str, Any]) -> None:
    assert body["actor"] == "urn:li:corpuser:emuser"
    assert body["role"] == "Admin"
