"""Typed shapes for Makra request configuration and response bodies.

These mirror the wire contract exactly: nested ``config`` keys keep their
snake_case names in Python because they are forwarded to the API unchanged.
The API rejects unknown ``config`` keys, so the TypedDicts double as
documentation of what a caller is allowed to override.

Response aliases describe the decoded value a method returns. They do not
wrap, unwrap, or otherwise transform the server body.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Mapping, Optional, TypedDict, Union

JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Union[JsonPrimitive, Mapping[str, Any], List[Any]]
JsonObject = Mapping[str, Any]
JsonSchema = Union[Mapping[str, Any], List[Any]]

# Decoded success body: parsed JSON, a text fallback, or None for empty/204.
ResponseBody = Union[Mapping[str, Any], List[Any], str, int, float, bool, None]

ProxyRegionScope = Literal["worldwide", "continent", "country"]
ProxyContinent = Literal[
    "africa", "asia", "europe", "north.america", "oceania", "south.america"
]
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
    """SDK-facing recovery flags. Sent on the wire as ``one_last_retry*``."""

    retry: bool
    retry_delay_ms: Optional[int]


class CrawlerConfig(TypedDict, total=False):
    post_ready_wait_ms: Optional[int]
    proxy: ProxyConfig
    recovery: CrawlerRecoveryConfig


class PaginationConfig(TypedDict, total=False):
    enabled: bool
    additional_pages: int


class TitleConfig(TypedDict, total=False):
    enabled: bool


class CommonConfig(TypedDict, total=False):
    """Request-overridable config shared by the extract and schema workflows."""

    crawler: CrawlerConfig


class ExtractConfig(CommonConfig, total=False):
    """Extract workflow config: common keys plus extract-only controls."""

    validation_mode: Optional[ValidationMode]
    pagination: PaginationConfig
    title: TitleConfig


class SchemaConfig(CommonConfig, total=False):
    """Schema workflow config: the common keys only."""


# --- Response bodies -------------------------------------------------------


class HealthResponse(TypedDict):
    """Success body of ``GET /healthz`` and ``GET /healthz/ready``."""

    status: str


class WorkflowEnvelope(TypedDict, total=False):
    """Stable fields on a blocking workflow success body.

    ``data`` and other payload keys remain untyped because their shape is the
    caller's schema, not a fixed SDK contract. Runtime values are never
    unwrapped out of this envelope.
    """

    success: bool
    status: str
    message: str
    data: Any
    errors: List[Any]
    warnings: List[Any]
    usage: Dict[str, Any]
    billing_state: str
    telemetry_run_id: str


class ExtractResponse(WorkflowEnvelope, total=False):
    """Blocking ``POST /workflows/extract`` success body."""


class SchemaResponse(WorkflowEnvelope, total=False):
    """Blocking ``POST /workflows/schema`` success body."""


class RunResult(WorkflowEnvelope, total=False):
    """Stored result payload from ``GET /workflows/runs/{id}/result``."""


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
    "CommonConfig",
    "CrawlerConfig",
    "CrawlerRecoveryConfig",
    "ExecutionMode",
    "ExtractConfig",
    "ExtractResponse",
    "Feature",
    "HealthResponse",
    "JsonObject",
    "JsonSchema",
    "JsonValue",
    "PaginationConfig",
    "ProxyConfig",
    "ProxyContinent",
    "ProxyRegionConfig",
    "ProxyRegionScope",
    "ResponseBody",
    "ResultSummary",
    "RunPage",
    "RunProgress",
    "RunResult",
    "RunState",
    "RunView",
    "SchemaConfig",
    "SchemaResponse",
    "TitleConfig",
    "ValidationMode",
    "WorkflowEnvelope",
]
