"""Keyword retrieval over a small, file-backed API catalog."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

KB_DIR = Path(__file__).resolve().parent / "kb"
ENDPOINTS_PATH = KB_DIR / "endpoints.json"

_TOKEN = re.compile(r"[a-z0-9]+")


def load_endpoints() -> list[dict[str, Any]]:
    return json.loads(ENDPOINTS_PATH.read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def _score(question: str, entry: dict[str, Any]) -> int:
    q = question.lower()
    score = 0
    for kw in entry.get("keywords", []):
        if kw.lower() in q:
            score += 4
    haystack = _tokens(
        " ".join(
            [
                entry.get("id", ""),
                entry.get("title", ""),
                entry.get("method", ""),
                entry.get("path", ""),
                entry.get("summary", ""),
                " ".join(entry.get("keywords", [])),
            ]
        )
    )
    score += len(_tokens(question) & haystack)
    if "create" in q and entry.get("method") == "POST" and "create" in entry.get("id", ""):
        score += 3
    if "dataset" in q and "dataset" in entry.get("id", ""):
        score += 2
    if "ingestion" in q and "ingestion" in entry.get("id", "").lower():
        score += 2
    return score


def retrieve(question: str) -> dict[str, Any]:
    entries = load_endpoints()
    ranked = sorted(
        (( _score(question, entry), entry) for entry in entries),
        key=lambda pair: pair[0],
        reverse=True,
    )
    best_score, best = ranked[0]
    if best_score <= 0:
        return {
            "question": question,
            "route": "kb_retrieve",
            "source": "kb:none",
            "tools": ["kb_search:agent/kb/endpoints.json"],
            "answer": (
                "The catalog has no matching GraphQL/REST entry for that question. "
                "No number was generated. Browse agent/kb/endpoints.json or ask "
                "about createIngestionSource, recipes, aspects, or DataHub components."
            ),
            "metrics": None,
            "citations": ["agent/kb/endpoints.json"],
            "caveat": "Keyword/rule router. Numbers come from checked-in fixtures, not a model.",
        }

    citation = best["citation"]
    doc_path = KB_DIR / Path(citation.split("#")[0]).name
    snippet = ""
    if doc_path.exists():
        snippet = doc_path.read_text(encoding="utf-8").strip().split("\n\n")[0]

    answer = (
        f"{best['method']} `{best['path']}` — {best['title']}.\n"
        f"{best['summary']}\n"
        f"Citation: `{citation}`."
    )
    if snippet:
        answer += f"\n\nFrom {doc_path.name}:\n{snippet}"

    return {
        "question": question,
        "route": "kb_retrieve",
        "source": f"kb:{best['id']}",
        "tools": [
            "kb_search:agent/kb/endpoints.json",
            f"read_doc:{citation}",
        ],
        "answer": answer,
        "metrics": None,
        "citations": [citation],
        "match": {
            "id": best["id"],
            "method": best["method"],
            "path": best["path"],
            "score": best_score,
        },
        "caveat": "Keyword/rule router. Numbers come from checked-in fixtures, not a model.",
    }
