from __future__ import annotations

import json
import sys

from agent.router import route


def main(argv: list[str]) -> int:
    question = " ".join(argv[1:]).strip()
    if not question:
        print("Usage: python -m agent \"Which pods are crashing in the ingest cluster?\"")
        return 2
    print(json.dumps(route(question), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
