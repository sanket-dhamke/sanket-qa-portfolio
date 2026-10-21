from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from api.app import app, reset_state  # noqa: E402
from config.settings import PAYLOADS  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    reset_state()
    return TestClient(app)


@pytest.fixture
def payloads() -> Path:
    return PAYLOADS
