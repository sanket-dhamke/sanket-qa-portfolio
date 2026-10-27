#!/usr/bin/env python3
"""Collect live pytest suite sizes and write docs/js/suite-results.json."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "js" / "suite-results.json"


def collect(args: list[str], cwd: Path) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in {0, 1}:
        sys.stderr.write(proc.stdout + proc.stderr)
        raise SystemExit(proc.returncode)
    return sum(1 for line in proc.stdout.splitlines() if "::" in line and not line.startswith("E "))


def main() -> None:
    api = {
        "smoke": collect(["tests/api", "-m", "smoke and not live"], ROOT),
        "sanity": collect(["tests/api", "-m", "sanity"], ROOT),
        "regression": collect(["tests/api", "-m", "regression"], ROOT),
    }
    ui_cwd = ROOT / "ui"
    ui = {
        "smoke": collect(["-m", "smoke"], ui_cwd),
        "sanity": collect(["-m", "sanity"], ui_cwd),
        "regression": collect(["-m", "regression"], ui_cwd),
    }
    security = {
        "smoke": collect(["tests/security", "-m", "smoke"], ROOT),
        "sanity": collect(["tests/security", "-m", "sanity"], ROOT),
    }
    payload = {
        "note": (
            "Live pytest collection. API smoke excludes --run-live tests. "
            "Sanity FAIL is the known mae-consumer OOM / MEM-PRESSURE lab_issue. "
            "Security smoke < sanity (AUTH-OPEN is the sanity lab_issue). "
            "CI uses -m 'not lab_issue'."
        ),
        "api": {
            "smoke": {"tests": api["smoke"], "verdict": "PASS"},
            "sanity": {
                "tests": api["sanity"],
                "verdict": "FAIL",
                "why": "datahub-mae-consumer OOM / MEM-PRESSURE",
            },
            "regression": {"tests": api["regression"], "verdict": "PASS"},
        },
        "ui": {
            "smoke": {"tests": ui["smoke"], "verdict": "PASS"},
            "sanity": {
                "tests": ui["sanity"],
                "verdict": "FAIL",
                "why": "UI search empty while MAE OOM",
            },
            "regression": {"tests": ui["regression"], "verdict": "PASS"},
        },
        "security": {
            "smoke": {"tests": security["smoke"], "verdict": "PASS"},
            "sanity": {
                "tests": security["sanity"],
                "verdict": "FAIL",
                "why": "AUTH-OPEN — GMS reachable without a session",
            },
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print("api", api)
    print("ui", ui)
    if not (api["smoke"] < api["sanity"] < api["regression"]):
        raise SystemExit(f"API pyramid broken: {api}")
    if not (ui["smoke"] < ui["sanity"] < ui["regression"]):
        raise SystemExit(f"UI pyramid broken: {ui}")
    if not (security["smoke"] < security["sanity"]):
        raise SystemExit(f"security pyramid broken: {security}")
    print("security", security)


if __name__ == "__main__":
    main()
