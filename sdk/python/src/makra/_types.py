"""Typed shapes for Makra request configuration and response bodies.

These mirror the wire contract exactly: nested ``config`` keys keep their
snake_case names in Python because they are forwarded to the API unchanged.
The API rejects unknown ``config`` keys, so the TypedDicts double as
documentation of what a caller is allowed to override.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Mapping, Optional, TypedDict, Union

JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Union[JsonPrimitive, Mapping[str, Any], List[Any]]
JsonObject = Mapping[str, Any]
JsonSchema = Union[Mapping[str, Any], List[Any]]

SelectorChainVersion = Literal["v1", "v2"]
ProxyRegionScope = Literal["worldwide", "continent", "country"]
ValidationMode = Literal["observe", "repair"]
ExecutionMode = Literal["concurrent", "sequential"]
Feature = Literal["extract", "schema"]
RunState = Literal[
    "queued",
    "running",
    "cancel_requested",
    "completed",
    "failed",
    "cancelled",
    "budget_exhausted",
]

# --- Workflow configuration ------------------------------------------------


class ProxyRegionConfig(TypedDict, total=False):
    scope: ProxyRegionScope
    value: Optional[str]


class ProxyConfig(TypedDict, total=False):
    region: ProxyRegionConfig


class CrawlerRecoveryConfig(TypedDict, total=False):
    one_last_retry: bool
    one_last_retry_delay_ms: Optional[int]


class CrawlerConfig(TypedDict, total=False):
    post_ready_wait_ms: Optional[int]
    proxy: ProxyConfig
    recovery: CrawlerRecoveryConfig


class MemoryConfig(TypedDict, total=False):
    enabled: bool
    selector_chain_version: SelectorChainVersion


class AuditConfig(TypedDict, total=False):
    enabled: bool
    use_cache: bool


class PaginationConfig(TypedDict, total=False):
    enabled: bool
    additional_pages: int


class TitleConfig(TypedDict, total=False):
    enabled: bool


class CommonConfig(TypedDict, total=False):
    """Request-overridable config shared by the extract and schema workflows."""

    memory: MemoryConfig
    crawler: CrawlerConfig


class ExtractConfig(CommonConfig, total=False):
    """Extract workflow config: common keys plus extract-only controls."""

    validation_mode: Optional[ValidationMode]
    audit: AuditConfig
    pagination: PaginationConfig
    title: TitleConfig


class SchemaConfig(CommonConfig, total=False):
    """Schema workflow config: the common keys only."""


# --- Response bodies -------------------------------------------------------


class ResultSummary(TypedDict, total=False):
    """Metadata about a stored run result. Never the payload itself."""

    available: bool
    content_type: str
    size_bytes: int
    sha256: str
    href: str


class RunProgress(TypedDict, total=False):
    attempt_number: int
    phase: str


class RunView(TypedDict, total=False):
    """The body of ``GET /workflows/runs/{run_id}``."""

    id: str
    feature: Feature
    state: RunState
    sequence: int
    poll_after_ms: int
    result_available: bool
    progress: RunProgress
    response_mode: str
    success: bool
    upstream_status: int
    credits_charged: float
    credits_charged_str: str
    usage: Dict[str, Any]
    billing_state: str
    telemetry_run_id: str
    terminal_reason: str
    archived: bool
    created_at: str
    started_at: str
    terminal_at: str
    result: ResultSummary


class RunPage(TypedDict, total=False):
    """The body of ``GET /workflows/runs``."""

    items: List[RunView]
    next_cursor: str
    concurrency: Dict[str, Any]


class AsyncAdmission(TypedDict, total=False):
    """The ``202 Accepted`` body returned for an asynchronous submission."""

    run_id: str
    state: RunState
    feature: Feature
    status_url: str
    events_url: str
    result_url: str


__all__ = [
    "AsyncAdmission",
    "AuditConfig",
    "CommonConfig",
    "CrawlerConfig",
    "CrawlerRecoveryConfig",
    "ExecutionMode",
    "ExtractConfig",
    "Feature",
    "JsonObject",
    "JsonSchema",
    "JsonValue",
    "MemoryConfig",
    "PaginationConfig",
    "ProxyConfig",
    "ProxyRegionConfig",
    "ProxyRegionScope",
    "ResultSummary",
    "RunPage",
    "RunProgress",
    "RunState",
    "RunView",
    "SchemaConfig",
    "SelectorChainVersion",
    "TitleConfig",
    "ValidationMode",
]
