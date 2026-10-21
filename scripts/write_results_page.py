#!/usr/bin/env python3
"""Compact static results page from pytest JUnit XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JUNIT = ROOT / "docs" / "reports" / "junit.xml"
OUT = ROOT / "docs" / "reports" / "results.html"


def main() -> None:
    tree = ET.parse(JUNIT)
    suite = tree.getroot()
    if suite.tag != "testsuite":
        suite = suite.find("testsuite")
    cases = list(suite.iter("testcase"))
    rows = []
    for case in cases:
        name = f"{case.get('classname', '')}::{case.get('name')}"
        status = "passed"
        if case.find("failure") is not None:
            status = "failed"
        elif case.find("skipped") is not None:
            status = "skipped"
        rows.append(
            f"<tr><td>{name}</td><td>{status}</td><td>{case.get('time')}</td></tr>"
        )
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Lab pytest snapshot</title>
<style>
body {{ font-family: sans-serif; background:#f3efe6; color:#1a2332; padding:24px; }}
table {{ border-collapse: collapse; width:100%; background:#fff; }}
td,th {{ border:1px solid #d8d0c2; padding:6px 8px; font-size:13px; }}
.note {{ font-size:13px; color:#5c6675; }}
</style></head><body>
<h1>pytest snapshot</h1>
<p class="note">Static file generated after pytest. Not a live Allure server.
tests={suite.get('tests')} failures={suite.get('failures')} skipped={suite.get('skipped')} time={suite.get('time')}s</p>
<table><tr><th>Test</th><th>Status</th><th>Time s</th></tr>
{''.join(rows)}
</table>
</body></html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
