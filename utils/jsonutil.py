"""Safe nested lookup for GraphQL/REST bodies."""

from __future__ import annotations

from typing import Any


def dig(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur
