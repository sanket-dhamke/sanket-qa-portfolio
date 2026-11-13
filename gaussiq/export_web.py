"""Dump GaussIQ-lab router rules, fixtures, and RCA for the in-browser demo."""

from __future__ import annotations

import html
import json
import uuid
from pathlib import Path

from gaussiq.handlers import ALLURE_LAYERS, ALLURE_SUITES, run_suite
from gaussiq.load import load
from gaussiq.rca_engine import evaluate as evaluate_rca
from gaussiq.router import CANNED_CHIPS, QUESTION_BANK, rules_for_export
from gaussiq.security_engine import evaluate as evaluate_security

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "js" / "gaussiq-data.json"
REPORTS = ROOT / "docs" / "reports"


def build() -> dict:
    return {
        "canned": CANNED_CHIPS,
        "questions": QUESTION_BANK,
        "rules": rules_for_export(),
        "fixtures": {
            "services": load("services.json"),
            "cases": load("cases.json"),
            "performance": load("performance.json"),
            "skills": load("skills.json"),
            "security": load("security.json"),
            "users": load("users.json"),
            "suites": load("suites.json"),
            "kb": load("kb.json"),
            "evidence": load("evidence.json"),
        },
        "rca_report": evaluate_rca(),
        "security_report": evaluate_security(),
        "caveat": (
            "In-browser demo is a vanilla JS port of the Python router. "
            "Python plus tests/test_gaussiq_routing.py are the source of truth. "
            "Fictional GaussIQ 1.0 demo tenant. Not affiliated with GaussIQ. Not their product."
        ),
    }


def _report_html(layer: str, suite: str, summary: dict) -> str:
    passed = int(summary.get("passed") or 0)
    failed = int(summary.get("failed") or 0)
    total = int(summary.get("total") or 0)
    verb = "passed" if failed == 0 else "failed"
    title = f"GaussIQ {layer.upper()} {suite}"
    uid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"gaussiq-{layer}-{suite}"))
    rows = []
    for case in summary.get("cases") or []:
        status = str(case.get("status") or "skip").upper()
        name = html.escape(str(case.get("name") or case.get("id") or "test"))
        klass = "pass" if status == "PASS" else "fail"
        rows.append(f"<tr class='{klass}'><td>{status}</td><td>{name}</td><td>{int(case.get('duration_ms') or 0)} ms</td></tr>")
    body = "\n".join(rows) or "<tr><td colspan='3'>No cases in this slice.</td></tr>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="allure-report-uuid" content="{uid}">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: IBM Plex Sans, system-ui, sans-serif; background: #12211c; color: #eef4ef; margin: 24px; }}
    h1 {{ font-size: 22px; font-weight: 600; }}
    .lede {{ color: #8aa297; max-width: 62ch; }}
    .ok {{ color: #3dba7a; }} .bad {{ color: #e05d4f; }}
    table {{ width: 100%; max-width: 880px; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #2f4a40; }}
    tr.fail td {{ color: #e05d4f; }}
    .note {{ margin-top: 24px; color: #8aa297; font-size: 12px; max-width: 68ch; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <p class="lede">{layer.upper()} {suite} {verb} ({passed}/{total}). Catalog replay for the GaussIQ 1.0 QA lab — not a live pytest spawn, not GaussIQ production.</p>
  <p class="{'ok' if failed == 0 else 'bad'}">{passed} passed · {failed} failed · {total} tests</p>
  <table>
    <thead><tr><th>Result</th><th>Case</th><th>Time</th></tr></thead>
    <tbody>
      {body}
    </tbody>
  </table>
  <p class="note">This is not GaussIQ’s product. Personal hybrid QA lab. Not affiliated. Not employment. Numbers are fixtures, not live production. This page stands in for an Allure slice so chat can link smoke, sanity, or regression without mixing suites.</p>
</body>
</html>
"""


def write_allure_pages() -> None:
    slices = []
    for layer in ALLURE_LAYERS:
        for suite in ALLURE_SUITES:
            summary = run_suite(suite, layer)
            slices.append((layer, suite, summary))
    for layer, suite, summary in slices:
        dest = REPORTS / f"allure-gaussiq-{layer}-{suite}" / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_report_html(layer, suite, summary), encoding="utf-8")
        print(f"Wrote {dest}")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    write_allure_pages()


if __name__ == "__main__":
    main()
