"""Tiny HTTP helpers for pytest + requests / TestClient."""

from __future__ import annotations

import time
from typing import Any, Callable


def elapsed_ms(fn: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - started) * 1000.0


def assert_fast(elapsed_seconds: float, budget: float = 1.0) -> None:
    assert elapsed_seconds < budget, f"{elapsed_seconds:.3f}s exceeded {budget}s"
