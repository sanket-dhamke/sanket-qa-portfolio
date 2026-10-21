from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from pages.architecture_page import ArchitecturePage

pytestmark = pytest.mark.ui


@pytest.mark.sanity
def test_architecture_states_model_does_not_choose_tools(page, site_url: str) -> None:
    view = ArchitecturePage(page)
    view.open(site_url)
    view.expect_ai_boundary()
