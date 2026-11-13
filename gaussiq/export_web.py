"""Dump GaussIQ-lab router rules, fixtures, and RCA for the in-browser demo."""

from __future__ import annotations

import json
from pathlib import Path

from gaussiq.load import load
from gaussiq.rca_engine import evaluate as evaluate_rca
from gaussiq.router import CANNED_CHIPS, QUESTION_BANK, rules_for_export
from gaussiq.security_engine import evaluate as evaluate_security

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "js" / "gaussiq-data.json"


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


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print("Allure HTML is produced by scripts/generate_gaussiq_allure.sh (allure generate --single-file).")


if __name__ == "__main__":
    main()
