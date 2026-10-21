"""requests session aimed at the mock GMS (uvicorn), not TestClient."""

from __future__ import annotations

from typing import Any

import requests

from config.settings import GMS_BASE_URL, LAB_PASSWORD, LAB_USER


def _root() -> str:
    return GMS_BASE_URL.rstrip("/")


def session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"Accept": "application/json"})
    return sess


def health() -> requests.Response:
    return session().get(f"{_root()}/health", timeout=5)


def login(username: str = LAB_USER, password: str = LAB_PASSWORD) -> requests.Response:
    return session().post(
        f"{_root()}/logIn",
        json={"username": username, "password": password},
        timeout=5,
    )


def graphql(query: str, variables: dict[str, Any] | None = None) -> requests.Response:
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    return session().post(f"{_root()}/api/graphql", json=payload, timeout=5)
