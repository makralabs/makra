"""Client configuration resolution.

Settings resolve in one fixed order — explicit argument, then environment
variable, then SDK default — so an application can be configured entirely from
code, entirely from the environment, or from any mix of the two.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional
from urllib.parse import urlparse

from ._constants import (
    CONTENT_TYPE_JSON,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF,
    DEFAULT_STREAM_IDLE_TIMEOUT,
    DEFAULT_TIMEOUT,
    DUMMY_API_KEY,
    ENV_API_KEY,
    ENV_BASE_URL,
    ENV_MAX_RETRIES,
    ENV_TIMEOUT,
    HEADER_ACCEPT,
    HEADER_API_KEY,
    HEADER_CONTENT_TYPE,
    HEADER_USER_AGENT,
    PRODUCTION_BASE_URL,
    RESERVED_REQUEST_HEADERS,
    USER_AGENT,
)


@dataclass(frozen=True)
class ClientConfig:
    """Fully resolved settings for one client instance."""

    api_key: str
    base_url: str
    timeout: float = DEFAULT_TIMEOUT
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    stream_idle_timeout: float = DEFAULT_STREAM_IDLE_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_backoff: float = DEFAULT_RETRY_BACKOFF
    default_headers: Mapping[str, str] = field(default_factory=dict)

    def headers(self) -> Dict[str, str]:
        """Headers sent on every request, including health checks."""
        headers = {
            HEADER_API_KEY: self.api_key,
            HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
            HEADER_ACCEPT: CONTENT_TYPE_JSON,
            HEADER_USER_AGENT: USER_AGENT,
        }
        headers.update(self.default_headers)
        return headers

    def url(self, path: str) -> str:
        return self.base_url + path


def resolve_config(
    api_key: Optional[str] = None,
    *,
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
    connect_timeout: Optional[float] = None,
    stream_idle_timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
    retry_backoff: Optional[float] = None,
    default_headers: Optional[Mapping[str, str]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> ClientConfig:
    """Resolve constructor arguments against the environment and defaults."""
    env = os.environ if environ is None else environ
    return ClientConfig(
        api_key=api_key or env.get(ENV_API_KEY) or DUMMY_API_KEY,
        base_url=_normalize_base_url(
            env.get(ENV_BASE_URL) or PRODUCTION_BASE_URL
            if base_url is None
            else base_url
        ),
        timeout=_positive(
            "timeout", timeout, env.get(ENV_TIMEOUT), DEFAULT_TIMEOUT
        ),
        connect_timeout=_positive(
            "connect_timeout", connect_timeout, None, DEFAULT_CONNECT_TIMEOUT
        ),
        stream_idle_timeout=_positive(
            "stream_idle_timeout",
            stream_idle_timeout,
            None,
            DEFAULT_STREAM_IDLE_TIMEOUT,
        ),
        max_retries=int(
            _non_negative(
                "max_retries",
                max_retries,
                env.get(ENV_MAX_RETRIES),
                DEFAULT_MAX_RETRIES,
            )
        ),
        retry_backoff=_positive(
            "retry_backoff", retry_backoff, None, DEFAULT_RETRY_BACKOFF
        ),
        default_headers=_validated_default_headers(default_headers),
    )


def _validated_default_headers(
    default_headers: Optional[Mapping[str, str]],
) -> Dict[str, str]:
    if default_headers is None:
        return {}
    if not isinstance(default_headers, Mapping):
        raise ValueError("default_headers must be a mapping of strings")
    resolved: Dict[str, str] = {}
    for key, value in default_headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("default_headers keys and values must be strings")
        reserved = key.lower()
        if reserved in RESERVED_REQUEST_HEADERS:
            raise ValueError(
                "default_headers must not include reserved header {!r}; {}".format(
                    key, _reserved_header_hint(reserved)
                )
            )
        resolved[key] = value
    return resolved


_RESERVED_HEADER_HINTS = {
    "api-key": "pass api_key to the Makra constructor",
    "content-type": "the SDK sets Content-Type automatically",
    "accept": "the SDK sets Accept automatically (text/event-stream for streaming methods)",
    "user-agent": "the SDK sets User-Agent automatically",
    "idempotency-key": "pass idempotency_key to the workflow method",
    "prefer": "use submit_extract or submit_schema for deferred runs",
    "last-event-id": "pass last_event_id to stream_run_events",
}


def _reserved_header_hint(name: str) -> str:
    return _RESERVED_HEADER_HINTS.get(name, "this header is owned by the SDK")


def _normalize_base_url(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("base_url must be an absolute HTTP or HTTPS URL")
    normalized = value.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base_url must be an absolute HTTP or HTTPS URL")
    return normalized


def _coerce(name: str, explicit: object, from_env: object, default: float) -> float:
    for value in (explicit, from_env):
        if value is None:
            continue
        if isinstance(value, bool):
            raise ValueError("{} must be a number".format(name))
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ValueError("{} must be a number".format(name)) from None
    return default


def _positive(name: str, explicit: object, from_env: object, default: float) -> float:
    value = _coerce(name, explicit, from_env, default)
    if value <= 0:
        raise ValueError("{} must be greater than 0".format(name))
    return value


def _non_negative(
    name: str, explicit: object, from_env: object, default: float
) -> float:
    value = _coerce(name, explicit, from_env, default)
    if value < 0:
        raise ValueError("{} must not be negative".format(name))
    return value
