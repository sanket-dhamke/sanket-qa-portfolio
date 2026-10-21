"""UI lab settings. Pages are the static GitHub Pages tree under docs/."""

from __future__ import annotations

import os
from pathlib import Path

UI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = UI_ROOT.parent
DOCS = REPO_ROOT / "docs"
REPORTS = UI_ROOT / "reports"
HEADLESS = os.getenv("UI_HEADLESS", "1") != "0"
BASE_PATH = os.getenv("UI_BASE_PATH", "")
