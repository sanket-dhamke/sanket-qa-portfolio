"""Optional screenshot dump into ui/reports/."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from config.settings import REPORTS


def save(page: Page, name: str) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return path
