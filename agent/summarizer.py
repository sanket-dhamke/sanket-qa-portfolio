"""Optional language-model hook.

This public sample ships with the model off. Handlers and the KB already
produced the answer. If a model is unavailable, return that text unchanged.
A model is never asked to produce a metric.
"""


def maybe_rephrase(answer: str, *, model_available: bool = False) -> str:
    if not model_available:
        return answer
    # Intentionally no vendor API in this repository.
    return answer
