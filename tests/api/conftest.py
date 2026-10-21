from __future__ import annotations

import sys
from pathlib import Path

import allure
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.app import app, reset_state  # noqa: E402
from config.settings import PAYLOADS  # noqa: E402
from tests.helpers.reporting import ReportingClient  # noqa: E402


@pytest.fixture
def client() -> ReportingClient:
    reset_state()
    return ReportingClient(TestClient(app))


@pytest.fixture
def payloads() -> Path:
    return PAYLOADS


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    allure.dynamic.epic("API automation")
    allure.dynamic.suite("tests/api")
    for mark in ("smoke", "sanity", "regression", "live"):
        if item.get_closest_marker(mark):
            allure.dynamic.feature(mark)
            allure.dynamic.tag(mark)
            allure.dynamic.story(item.name)
            break
