"""Allure labels so split_allure_by_suite.py can bucket GaussIQ API tests."""

from __future__ import annotations

import allure
import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    allure.dynamic.epic("GaussIQ API")
    allure.dynamic.tag("gaussiq")
    allure.dynamic.tag("api")
    for mark in ("smoke", "sanity", "regression", "product"):
        if item.get_closest_marker(mark):
            allure.dynamic.feature(mark)
            allure.dynamic.suite(mark)
            allure.dynamic.tag(mark)
            allure.dynamic.story(item.name)
            break
