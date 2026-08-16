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
    HEADER_API_KEY,
    PRODUCTION_BASE_URL,
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
            "Content-Type": CONTENT_TYPE_JSON,
            "Accept": CONTENT_TYPE_JSON,
            "User-Agent": USER_AGENT,
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
            base_url if base_url else env.get(ENV_BASE_URL) or PRODUCTION_BASE_URL
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
        default_headers=dict(default_headers or {}),
    )


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
