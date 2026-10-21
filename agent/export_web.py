"""Dump router rules, fixtures, recipes, and KB entries for the in-browser demo."""

from __future__ import annotations

import json
from pathlib import Path

from agent.handlers import FIXTURES, RECIPES
from agent.kb import load_endpoints
from agent.router import CANNED_CHIPS, rules_for_export

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "js" / "demo-data.json"


def _json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build() -> dict:
    return {
        "canned": CANNED_CHIPS,
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
        },
        "recipes": {
            "postgres": (RECIPES / "postgres.yml").read_text(encoding="utf-8"),
            "oracle": (RECIPES / "oracle.yml").read_text(encoding="utf-8"),
        },
        "endpoints": load_endpoints(),
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
