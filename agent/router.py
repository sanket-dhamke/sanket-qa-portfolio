"""Keyword / rule intent router.

This is deliberately not an LLM. The first matching rule wins. Numbers in
answers always come from handlers (fixture JSON) or from cited KB files.
"""

from __future__ import annotations

from typing import Any

from agent import handlers, kb
from agent.summarizer import maybe_rephrase

CANNED_QUESTIONS = [
    "Which pods are crashing or restarting after OOM?",
    "Show CPU and memory of datahub-gms",
    "Show postgres and oracle ingestion sources and total assets",
    "Ingest a postgres source",
    "What GraphQL mutation creates an ingestion source?",
]

# Order is the contract. Recipe / handlers sit in front of KB retrieval.
RULES: list[dict[str, Any]] = [
    {
        "route": "ingest_recipe",
        "source": "handler:ingest_recipe",
        "handler": handlers.ingest_recipe,
        "any": [
            "ingest a postgres",
            "ingest postgres source",
            "ingest a postgres source",
            "recipe yaml",
            "starter recipe",
            "ask for recipe",
            "run postgres ingestion",
            "create ingestion source from recipe",
            "postgres recipe",
        ],
    },
    {
        "route": "pod_status",
        "source": "handler:pod_status",
        "handler": handlers.pod_status,
        "any": [
            "crash",
            "crashing",
            "crashloop",
            "oom",
            "oomkilled",
            "failing pod",
            "which pod",
            "pod status",
            "pods are",
            "restarting",
            "restarts",
            "probe fail",
            "liveness",
            "readiness probe",
        ],
    },
    {
        "route": "resource_metrics",
        "source": "handler:resource_metrics",
        "handler": handlers.resource_metrics,
        "any": [
            "cpu",
            "memory",
            " ram",
            "utilization",
            "resource usage",
            "datahub-gms",
            "datahub-mae-consumer",
            "datahub-mce-consumer",
            "datahub-frontend",
            "datahub-actions",
            "mae-consumer",
            "mce-consumer",
        ],
    },
    {
        "route": "ingestion_assets",
        "source": "handler:ingestion_assets",
        "handler": handlers.ingestion_assets,
        "any": [
            "ingestion sources",
            "data sources",
            "oracle",
            "total assets",
            "asset count",
            "how many dataset",
            "dataset count",
            "postgres and oracle",
        ],
    },
    {
        "route": "kb_retrieve",
        "source": "kb",
        "handler": kb.retrieve,
        "any": [
            "graphql",
            "mutation",
            "createingestionsource",
            "createingestionexecutionrequest",
            "listingestionsources",
            "rest call",
            "which endpoint",
            "what rest",
            "api call",
            "which api",
            "ingestproposal",
            "aspect",
        ],
    },
]


def _normalize(question: str) -> str:
    return " ".join(question.lower().split())


def _match_rule(question: str) -> dict[str, Any] | None:
    blob = _normalize(question)
    padded = f" {blob} "
    for rule in RULES:
        for token in rule["any"]:
            needle = token.lower()
            if needle.startswith(" ") or needle.endswith(" "):
                if needle in padded:
                    return rule
            elif needle in blob:
                return rule
    return None


def route(question: str, *, model_available: bool = False) -> dict[str, Any]:
    """Return a structured answer with a visible source field."""
    text = (question or "").strip()
    if not text:
        result = handlers.fallback("")
        result["answer"] = maybe_rephrase(result["answer"], model_available=model_available)
        return result

    rule = _match_rule(text)
    if rule is None:
        result = handlers.fallback(text)
    else:
        result = rule["handler"](text)
        result["route"] = rule["route"]
        if rule["route"] != "kb_retrieve":
            result["source"] = rule["source"]

    result["question"] = text
    result["model_available"] = model_available
    result["answer"] = maybe_rephrase(result["answer"], model_available=model_available)
    return result


def rules_for_export() -> list[dict[str, Any]]:
    return [
        {"route": rule["route"], "source": rule["source"], "any": list(rule["any"])}
        for rule in RULES
    ]
