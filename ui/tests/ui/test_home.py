from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from pages.home_page import HomePage

pytestmark = pytest.mark.ui


@pytest.mark.smoke
def test_home_has_name_and_three_cards(page, site_url: str) -> None:
    home = HomePage(page)
    home.open(site_url)
    home.expect_lead_sdet()
    home.expect_cards()
    expect_footer = page.locator("footer .note")
    expect_footer.wait_for()
    assert "Not affiliated" in expect_footer.inner_text()
    assert "Pune" not in page.locator("body").inner_text()
