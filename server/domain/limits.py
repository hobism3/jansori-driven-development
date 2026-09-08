"""Configurable limits and thresholds (D-03).

Defaults follow approved decisions:
- Content length L = 10,000 chars (D-03; SPEC original example value, configurable).
- Normalization threshold = 3 (aidlc-state Q5=B; demo-aligned, configurable).

Values are read from environment at import time so `make run` / tests can override
without code changes, while keeping the defaults above.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class Limits:
    """Immutable snapshot of configurable limits."""

    max_content_length: int = 10_000  # L (I-09)
    normalization_threshold: int = 3  # corrections count that raises normalize_due (Q7)


def load_limits() -> Limits:
    """Load limits from environment (JANSORI_MAX_CONTENT_LENGTH, JANSORI_NORMALIZE_THRESHOLD)."""
    return Limits(
        max_content_length=_env_int("JANSORI_MAX_CONTENT_LENGTH", 10_000),
        normalization_threshold=_env_int("JANSORI_NORMALIZE_THRESHOLD", 3),
    )


# Module-level default instance (services import this; tests may pass their own Limits).
LIMITS = load_limits()
