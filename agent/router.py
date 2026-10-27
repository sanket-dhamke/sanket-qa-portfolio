"""Keyword / rule intent router.

This is deliberately not an LLM. The first matching rule wins. Numbers in
answers always come from handlers (fixture JSON), the suite catalog, or cited KB files.
"""

from __future__ import annotations

import re
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

QUESTION_BANK = [
    {
        "id": "health",
        "title": "App health",
        "questions": [
            "What is the current state of the application?",
            "What is the health of the application?",
        ],
    },
    {
        "id": "pods",
        "title": "Pods / OOM / RCA",
        "questions": [
            "Which pods are crashing or restarting after OOM?",
            "Why is DataHub slow?",
        ],
    },
    {
        "id": "suites",
        "title": "Smoke / sanity / regression",
        "questions": [
            "Run smoke suite",
            "Run API sanity suite",
            "Check UI sanity",
            "Run security smoke",
        ],
    },
    {
        "id": "email",
        "title": "Email / schedule",
        "questions": [
            "How does the email report schedule work?",
            "Send an email preview",
        ],
    },
    {
        "id": "performance",
        "title": "Performance",
        "questions": [
            "Show CPU and memory of datahub-gms",
            "Why is DataHub slow?",
            "What configuration needs to be upgraded to ingest 10m or 1m assets?",
        ],
    },
    {
        "id": "security",
        "title": "Security",
        "questions": [
            "any security issues?",
            "why is GMS exposed?",
            "Is there a secret in the logs?",
            "Is TLS the cause?",
        ],
    },
]

CHILD_QUESTIONS = {
    "api": [
        {
            "id": "read",
            "title": "Look up",
            "questions": [
                "Why did API sanity fail?",
                "How many API smoke tests are there?",
                "What is the last pipeline SHA?",
            ],
        },
        {
            "id": "run",
            "title": "Run a suite",
            "questions": [
                "Run API smoke",
                "Run API sanity suite",
                "Run API regression",
            ],
        },
    ],
    "ui": [
        {
            "id": "read",
            "title": "Look up",
            "questions": [
                "Why did UI sanity fail?",
                "How many UI smoke tests are there?",
                "What is the last pipeline SHA?",
            ],
        },
        {
            "id": "run",
            "title": "Run a suite",
            "questions": [
                "Run UI smoke",
                "Check UI sanity",
                "Run UI regression",
            ],
        },
    ],
}

CANNED_CHIPS = CANNED_QUESTIONS + [
    "Test the login with username as emuser and password as empass",
    "Run API sanity suite",
    "Check UI sanity",
    "How many alerts are in DataHub?",
    "Why is DataHub slow?",
    "What is the current state of the application?",
    "What configuration needs to be upgraded to ingest 10m or 1m assets?",
    "List the lab tools",
]

_YES = re.compile(
    r"^\s*(y|yes|yeah|yep|ok|okay|sure|do it|go ahead|please run|run it|run them|run regression)\b",
    re.I,
)
_NO = re.compile(r"^\s*(n|no|nope|skip|not now|later|don't|dont)\b", re.I)

# Order is the contract. Specific automation routes sit in front of generic metrics/KB.
RULES: list[dict[str, Any]] = [
    {
        "route": "login_api",
        "source": "handler:login_api",
        "handler": handlers.login_api,
        "any": [
            "test the login",
            "test login",
            "run login",
            "log in with",
            "login with",
            "username as",
            "password as",
        ],
    },
    {
        "route": "pipeline_status",
        "source": "handler:pipeline_status",
        "handler": handlers.pipeline_status,
        "any": [
            "last sha",
            "last pipeline",
            "pipeline sha",
            "jenkins",
            "github actions",
            "git pull",
            "git fetch",
        ],
    },
    {
        "route": "suite_explain",
        "source": "handler:suite_explain",
        "handler": handlers.suite_explain,
        "any": [
            "why did",
            "why does",
            "how many smoke",
            "how many sanity",
            "how many regression",
            "how many api",
            "how many ui",
            "suite pyramid",
            "test pyramid",
        ],
    },
    {
        "route": "run_suite",
        "source": "handler:run_suite",
        "handler": handlers.run_named_suite,
        "any": [
            "api sanity",
            "ui sanity",
            "sanity suite",
            "smoke suite",
            "run smoke",
            "run sanity",
            "run regression",
            "regression suite",
            "check ui sanity",
            "check api sanity",
            "run api tests",
            "run ui tests",
            "run api smoke",
            "run ui smoke",
            "api smoke",
            "ui smoke",
            "run api regression",
            "run ui regression",
            "security smoke",
            "security sanity",
            "run security smoke",
            "run security sanity",
        ],
    },
    {
        "route": "app_status",
        "source": "handler:app_status",
        "handler": handlers.app_status,
        "any": [
            "current state of the application",
            "current status of the application",
            "current state of application",
            "application status",
            "app status",
            "quality of the application",
            "application quality",
            "verdict on the application",
            "health of the application",
        ],
    },
    {
        "route": "capacity_plan",
        "source": "handler:capacity_plan",
        "handler": handlers.capacity_plan,
        "any": [
            "configuration needs",
            "config needs to be upgraded",
            "upgrade to ingest",
            "ingest 10m",
            "ingest 1m",
            "1 million assets",
            "10 million assets",
            "1m assets",
            "10m assets",
            "capacity",
            "scale to",
        ],
    },
    {
        "route": "tool_catalog",
        "source": "handler:tool_catalog",
        "handler": handlers.tool_catalog,
        "any": [
            "tool catalog",
            "list the lab tools",
            "list the tools",
            "list tools",
            "which tools",
            "what tools",
            "available tools",
            "show tools",
            "lab tools",
        ],
    },
    {
        "route": "email_report",
        "source": "handler:email_report",
        "handler": handlers.email_report,
        "any": [
            "email report",
            "email preview",
            "email schedule",
            "smtp",
            "on new issue",
            "send an email",
            "how does the email",
        ],
    },
    {
        "route": "perf_rca",
        "source": "handler:perf_rca",
        "handler": handlers.perf_rca,
        "any": [
            "why is it slow",
            "why is datahub slow",
            "why is the application slow",
            "root cause",
            "root-cause",
            "perf rca",
            "what is wrong",
            "what's wrong",
            "diagnose performance",
            "why search is empty",
        ],
    },
    {
        "route": "security_rca",
        "source": "handler:security_rca",
        "handler": handlers.security_rca,
        "any": [
            "any security issues",
            "security issues",
            "security",
            "secret",
            "cve",
            "exposed",
            "tls",
            "auth",
            "why is gms exposed",
        ],
    },
    {
        "route": "execute_api",
        "source": "handler:execute_api",
        "handler": handlers.execute_catalog_api,
        "any": [
            "how many alert",
            "how many alerts",
            "total no of alert",
            "total number of alert",
            "alerts in datahub",
            "list incidents",
            "gms health",
            "health api",
            "/health",
        ],
    },
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
            "how many assets",
            "how many asset",
            "number of assets",
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


def annotate_source(result: dict[str, Any]) -> dict[str, Any]:
    """Visible path: handler (fixtures), kb (cited file), suite (pytest catalog), fallback."""
    source = str(result.get("source") or "")
    route_name = str(result.get("route") or "")
    if source.startswith("kb:") or route_name == "kb_retrieve":
        kind, label = "kb", "Knowledge base · cited catalog"
    elif route_name == "run_suite" or source.startswith("handler:run_suite"):
        kind, label = "suite", "Suite catalog · pytest markers"
    elif source.startswith("fallback") or route_name == "fallback":
        kind, label = "fallback", "Fallback · no match"
    else:
        kind, label = "handler", "Handler · fixtures only"
    result["source_kind"] = kind
    result["source_label"] = label
    return result


def route(
    question: str,
    *,
    model_available: bool = False,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a structured answer with a visible source field."""
    text = (question or "").strip()
    session = session if session is not None else {}

    if session.get("awaiting_regression") and text:
        if _YES.search(text):
            result = handlers.run_named_suite(text, suite="regression", layer=None)
            result["question"] = text
            result["model_available"] = model_available
            result["session_update"] = {"awaiting_regression": False}
            result["awaiting_regression"] = False
            result["answer"] = maybe_rephrase(
                result["answer"], model_available=model_available
            )
            return annotate_source(result)
        if _NO.search(text):
            result = handlers.skip_regression(text)
            result["question"] = text
            result["model_available"] = model_available
            result["answer"] = maybe_rephrase(
                result["answer"], model_available=model_available
            )
            return annotate_source(result)

    if not text:
        result = handlers.fallback("")
        result["answer"] = maybe_rephrase(
            result["answer"], model_available=model_available
        )
        return annotate_source(result)

    rule = _match_rule(text)
    if rule is None:
        result = handlers.fallback(text)
    else:
        result = rule["handler"](text)
        result["route"] = rule["route"]
        if rule["route"] not in {"kb_retrieve", "run_suite", "execute_api", "login_api"}:
            result["source"] = rule["source"]

    result["question"] = text
    result["model_available"] = model_available
    result["answer"] = maybe_rephrase(result["answer"], model_available=model_available)
    return annotate_source(result)


def rules_for_export() -> list[dict[str, Any]]:
    return [
        {"route": rule["route"], "source": rule["source"], "any": list(rule["any"])}
        for rule in RULES
    ]
