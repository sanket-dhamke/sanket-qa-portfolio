"""API-lab settings. Defaults talk to the bundled mock GMS, not a live cluster."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GMS_BASE_URL = os.getenv("GMS_BASE_URL", "http://127.0.0.1:8080")
LAB_USER = os.getenv("LAB_USER", "emuser")
LAB_PASSWORD = os.getenv("LAB_PASSWORD", "empass")
PAYLOADS = ROOT / "tests" / "payloads"
REPORTS = ROOT / "reports"
