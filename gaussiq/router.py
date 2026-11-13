"""Keyword / rule intent router for the GaussIQ QA lab.

Deliberately not an LLM. First matching rule wins. Numbers always come from
handlers (fixture JSON), the suite catalog, or cited KB entries.
"""

from __future__ import annotations

from typing import Any

from gaussiq import handlers

CANNED_QUESTIONS = [
    "What is the current quality of GaussIQ 1.0?",
    "any security issues?",
    "Why is MTTR high?",
    "Run API smoke on case-plan APIs",
]

QUESTION_BANK = [
    {
        "id": "health",
        "title": "24x7 health",
        "questions": [
            "What is the current quality of GaussIQ 1.0?",
            "What is the current state of GaussIQ 1.0 demo services?",
            "Which GaussIQ 1.0 services are down?",
        ],
    },
    {
        "id": "cases",
        "title": "Case Intelligence / RCA",
        "questions": [
            "Why did AJ18991 return HTTP 500?",
            "Is AJ18991 a code defect?",
            "What is the likely root cause for AJ18991?",
        ],
    },
    {
        "id": "performance",
        "title": "Performance (MTTR / eng assist)",
        "questions": [
            "Why is MTTR high?",
            "What is gross MTTR in this fixture?",
            "What is net MTTR?",
            "How many engineer assist hours?",
        ],
    },
    {
        "id": "skills",
        "title": "Skills Intelligence",
        "questions": [
            "Which skill gaps are high impact?",
            "Who can troubleshoot certificates?",
        ],
    },
    {
        "id": "security",
        "title": "Security",
        "questions": [
            "any security issues?",
            "why is case-intel-api exposed?",
            "Is there a secret in the logs?",
            "Is TLS the cause?",
        ],
    },
    {
        "id": "suites",
        "title": "Smoke / sanity / regression",
        "questions": [
            "Run API smoke on case-plan APIs",
            "Run smoke suite",
            "Run sanity suite",
            "Run regression suite",
            "Run security regression",
        ],
    },
    {
        "id": "login",
        "title": "Lab login",
        "questions": [
            "Test the login with username as giquser and password as giqpass",
        ],
    },
    {
        "id": "kb",
        "title": "Public product concepts",
        "questions": [
            "What is Case Intelligence?",
            "What is Skills Intelligence?",
            "What is Management Insights?",
        ],
    },
]

CANNED_CHIPS = list(CANNED_QUESTIONS)

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
        "route": "suite_explain",
        "source": "handler:suite_explain",
        "handler": handlers.suite_explain,
        "any": [
            "why did smoke",
            "why did sanity",
            "why did regression",
            "how many smoke",
            "how many sanity",
            "how many regression",
        ],
    },
    {
        "route": "run_suite",
        "source": "handler:run_suite",
        "handler": handlers.run_named_suite,
        "any": [
            "sanity suite",
            "smoke suite",
            "run smoke",
            "run sanity",
            "run regression",
            "regression suite",
            "run api tests",
            "run api smoke",
            "api smoke",
            "case-plan",
            "case plan api",
            "security smoke",
            "security sanity",
            "run security",
            "security regression",
        ],
    },
    {
        "route": "app_status",
        "source": "handler:app_status",
        "handler": handlers.health_status,
        "any": [
            "current state of",
            "current status of",
            "application status",
            "app status",
            "health of",
            "current quality",
            "quality of gaussiq",
            "quality of 1.0",
            "demo services",
            "24x7",
            "24 x 7",
            "gaussiq 1.0",
        ],
    },
    {
        "route": "case_rca",
        "source": "handler:case_rca",
        "handler": handlers.case_rca,
        "any": [
            "aj18991",
            "http 500",
            "cert mismatch",
            "certificate",
            "jetson",
            "likely root cause",
            "code defect",
            "sfm wizard",
        ],
    },
    {
        "route": "skills_gaps",
        "source": "handler:skills_gaps",
        "handler": handlers.skills_gaps,
        "any": [
            "skill gap",
            "skill gaps",
            "skills intelligence",
            "who can",
            "coverage",
            "salesforce api",
        ],
    },
    {
        "route": "why_mttr",
        "source": "handler:why_mttr",
        "handler": handlers.why_mttr,
        "any": [
            "why is mttr",
            "why mttr",
            "mttr high",
            "mttr is high",
            "why is resolution",
        ],
    },
    {
        "route": "perf_metrics",
        "source": "handler:perf_metrics",
        "handler": handlers.perf_metrics,
        "any": [
            "gross mttr",
            "net mttr",
            "mttr",
            "eng assist",
            "engineer assist",
            "performance",
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
            "exposed",
            "tls",
            "auth",
            "why is case-intel",
            "unauthenticated",
        ],
    },
    {
        "route": "perf_rca",
        "source": "handler:perf_rca",
        "handler": handlers.perf_rca,
        "any": [
            "root cause",
            "root-cause",
            "what is wrong",
            "what's wrong",
            "diagnose",
            "why is the connector",
            "signal connector",
        ],
    },
    {
        "route": "service_health",
        "source": "handler:service_health",
        "handler": handlers.service_health,
        "any": [
            "which service",
            "services are down",
            "service health",
            "crashloop",
            "connector",
            "cpu",
            "memory",
        ],
    },
    {
        "route": "kb_retrieve",
        "source": "kb",
        "handler": handlers.kb_retrieve,
        "any": [
            "case intelligence",
            "skills intelligence",
            "management insights",
            "execution intelligence",
            "connect signals",
            "what is case",
            "what is skills",
            "what is management",
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
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = (question or "").strip()
    session = session if session is not None else {}

    if session.get("awaiting_regression") and text:
        if handlers.YES.search(text):
            result = handlers.run_named_suite(text, suite="regression", layer=None)
            result["question"] = text
            result["model_available"] = False
            result["session_update"] = {"awaiting_regression": False}
            result["awaiting_regression"] = False
            return annotate_source(result)
        if handlers.NO.search(text):
            result = handlers.skip_regression(text)
            result["question"] = text
            result["model_available"] = False
            return annotate_source(result)

    if not text:
        result = handlers.fallback("")
        result["question"] = ""
        result["model_available"] = False
        return annotate_source(result)

    rule = _match_rule(text)
    if rule is None:
        result = handlers.fallback(text)
    else:
        result = rule["handler"](text)
        result["route"] = rule["route"]
        if rule["route"] not in {"kb_retrieve", "run_suite", "login_api"}:
            result["source"] = rule["source"]

    result["question"] = text
    result["model_available"] = False
    return annotate_source(result)


def rules_for_export() -> list[dict[str, Any]]:
    return [
        {"route": rule["route"], "source": rule["source"], "any": list(rule["any"])}
        for rule in RULES
    ]
