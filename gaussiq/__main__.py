from __future__ import annotations

import json
import sys

from gaussiq.router import route


def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or "What is the current state of GaussIQ 1.0 demo services?"
    result = route(question)
    print(result["answer"])
    print()
    print("source=" + str(result.get("source")))
    print("route=" + str(result.get("route")))
    if result.get("metrics"):
        print("metrics=" + json.dumps(result["metrics"]))


if __name__ == "__main__":
    main()
