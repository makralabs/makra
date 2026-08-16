"""Retry policy shared by the synchronous and asynchronous clients.

A request is retried only when repeating it is safe. GET requests always are.
A workflow submission is only safe because the SDK attaches an
``Idempotency-Key``: the gateway then replays the original run instead of
starting a second billable one.
"""

from __future__ import annotations

import random
from typing import Optional

from ._constants import DEFAULT_RETRY_BACKOFF, MAX_RETRY_BACKOFF

RETRYABLE_STATUS_CODES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})

# 409 is retryable only for the idempotent replay race, never for a genuine
# conflict such as reusing one key for two different bodies.
_NON_RETRYABLE_CODES = frozenset({"idempotency_key_reuse", "run_not_terminal"})


def is_retryable_status(status_code: int, code: Optional[str] = None) -> bool:
    if code in _NON_RETRYABLE_CODES:
        return False
    return status_code in RETRYABLE_STATUS_CODES


def retry_delay(
    attempt: int,
    *,
    backoff: float = DEFAULT_RETRY_BACKOFF,
    retry_after: Optional[float] = None,
) -> float:
    """Seconds to wait before attempt ``attempt`` (1-based).

    A server-supplied ``Retry-After`` always wins. Otherwise the delay grows
    exponentially with full jitter, which spreads out a fleet of clients that
    were all rejected at the same moment.
    """
    if retry_after is not None and retry_after >= 0:
        return min(retry_after, MAX_RETRY_BACKOFF)
    ceiling = min(backoff * (2 ** max(attempt - 1, 0)), MAX_RETRY_BACKOFF)
    return random.uniform(ceiling / 2, ceiling)


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    """Parse a ``Retry-After`` header expressed in seconds."""
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    return seconds if seconds >= 0 else None
