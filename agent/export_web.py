"""Dump router rules, fixtures, recipes, and KB entries for the in-browser demo."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agent.handlers import FIXTURES, RECIPES
from agent.kb import load_endpoints
from agent.rca_engine import evaluate as evaluate_rca
from agent.router import CANNED_CHIPS, CHILD_QUESTIONS, QUESTION_BANK, rules_for_export
from agent.security_engine import evaluate as evaluate_security

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "js" / "demo-data.json"


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _pipeline() -> dict:
    row = _json("pipeline.json")
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        if sha:
            row["last_sha"] = sha
            row["last_sha_short"] = sha[:7]
    except (OSError, subprocess.CalledProcessError):
        pass
    return row


def build() -> dict:
    return {
        "canned": CANNED_CHIPS,
        "questions": QUESTION_BANK,
        "child_questions": CHILD_QUESTIONS,
        "rules": rules_for_export(),
        "fixtures": {
            "cluster": _json("cluster.json"),
            "metrics": _json("metrics.json"),
            "ingestion": _json("ingestion.json"),
            "rca": _json("rca.json"),
            "alerts": _json("alerts.json"),
            "users": _json("users.json"),
            "app_config": _json("app_config.json"),
            "suites": _json("suites.json"),
            "tools": _json("tools.json"),
            "security": _json("security.json"),
            "pipeline": _pipeline(),
        },
        "recipes": {
            "postgres": (RECIPES / "postgres.yml").read_text(encoding="utf-8"),
            "oracle": (RECIPES / "oracle.yml").read_text(encoding="utf-8"),
        },
        "endpoints": load_endpoints(),
        "pipeline": _pipeline(),
        "rca_report": evaluate_rca(),
        "security_report": evaluate_security(),
        "caveat": (
            "In-browser demo is a vanilla JS port of the Python router. "
            "Python plus tests/test_routing.py are the source of truth. "
            "Fictional DataHub demo tenant. Not a live cluster."
        ),
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
