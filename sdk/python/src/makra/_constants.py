"""Wire-level constants for the Makra API.

Every URL, header, enum value, and default the SDK depends on is declared here
so the client modules stay free of scattered string literals. Changing the HTTP
surface should mean changing this file and nothing else.
"""

from __future__ import annotations

from typing import FrozenSet

SDK_VERSION = "0.2.0"
USER_AGENT = "makra-python/" + SDK_VERSION

# --- Endpoints -------------------------------------------------------------

PRODUCTION_BASE_URL = "https://api.makralabs.org"
DEVELOPMENT_BASE_URL = "http://localhost:8080"

PATH_HEALTH = "/healthz"
PATH_READY = "/healthz/ready"
PATH_EXTRACT = "/workflows/extract"
PATH_SCHEMA = "/workflows/schema"
PATH_RUNS = "/workflows/runs"


def run_path(run_id: str, suffix: str = "") -> str:
    """Build the path of a single run resource, e.g. ``/runs/<id>/result``."""
    return "{}/{}{}".format(PATH_RUNS, run_id, suffix)


# --- Configuration ---------------------------------------------------------

ENV_API_KEY = "MAKRA_API_KEY"
ENV_BASE_URL = "MAKRA_BASE_URL"
ENV_TIMEOUT = "MAKRA_TIMEOUT"
ENV_MAX_RETRIES = "MAKRA_MAX_RETRIES"

# Temporary shared key for local development against a gateway that does not
# yet enforce authentication. It is not a secret.
DUMMY_API_KEY = "makra-development-key"

# A synchronous submission holds the connection until the run is terminal, so
# the request timeout is really "how long may a workflow take".
DEFAULT_TIMEOUT = 300.0
DEFAULT_CONNECT_TIMEOUT = 10.0
# The gateway emits an SSE heartbeat every 15 seconds. A read gap far larger
# than that means the connection died, not that the run is slow.
DEFAULT_STREAM_IDLE_TIMEOUT = 90.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF = 0.5
MAX_RETRY_BACKOFF = 8.0
DEFAULT_POLL_INTERVAL = 2.0

# --- Headers ---------------------------------------------------------------

HEADER_API_KEY = "Api-Key"
HEADER_IDEMPOTENCY_KEY = "Idempotency-Key"
HEADER_PREFER = "Prefer"
HEADER_LAST_EVENT_ID = "Last-Event-ID"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_ACCEPT = "Accept"
HEADER_USER_AGENT = "User-Agent"
HEADER_RETRY_AFTER = "Retry-After"
HEADER_REQUEST_ID = "X-Request-Id"
HEADER_RUN_ID = "X-Makra-Run-Id"
HEADER_USAGE_STATUS = "X-Makra-Usage-Status"
HEADER_CREDITS_CHARGED = "X-Makra-Credits-Charged"
HEADER_TELEMETRY_RUN_ID = "X-Makra-Telemetry-Run-Id"

# Names the SDK sets itself. Callers pass the matching constructor or
# operation argument instead of overriding these through default_headers.
RESERVED_REQUEST_HEADERS: FrozenSet[str] = frozenset(
    {
        HEADER_API_KEY.lower(),
        HEADER_CONTENT_TYPE.lower(),
        HEADER_ACCEPT.lower(),
        HEADER_USER_AGENT.lower(),
        HEADER_IDEMPOTENCY_KEY.lower(),
        HEADER_PREFER.lower(),
        HEADER_LAST_EVENT_ID.lower(),
    }
)

# GET /workflows/runs query window documented by the public API.
LIST_RUNS_MIN_LIMIT = 1
LIST_RUNS_MAX_LIMIT = 100

PREFER_RESPOND_ASYNC = "respond-async"

CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_SSE = "text/event-stream"

# --- Request enums ---------------------------------------------------------


class ExecutionModes:
    """How multiple URLs in one extract request are processed."""

    CONCURRENT = "concurrent"
    SEQUENTIAL = "sequential"


EXECUTION_MODES: FrozenSet[str] = frozenset(
    {ExecutionModes.CONCURRENT, ExecutionModes.SEQUENTIAL}
)


class ValidationModes:
    """What the extract workflow does when output fails schema validation."""

    OBSERVE = "observe"
    REPAIR = "repair"


VALIDATION_MODES: FrozenSet[str] = frozenset(
    {ValidationModes.OBSERVE, ValidationModes.REPAIR}
)


class ProxyRegionScopes:
    WORLDWIDE = "worldwide"
    CONTINENT = "continent"
    COUNTRY = "country"


PROXY_REGION_SCOPES: FrozenSet[str] = frozenset(
    {
        ProxyRegionScopes.WORLDWIDE,
        ProxyRegionScopes.CONTINENT,
        ProxyRegionScopes.COUNTRY,
    }
)


class ProxyContinents:
    """Continent slugs for ``config.crawler.proxy.region.value``.

    Used when ``scope`` is ``continent``. These are Evomi-style slugs, not
    UN M49 numeric codes.
    """

    AFRICA = "africa"
    ASIA = "asia"
    EUROPE = "europe"
    NORTH_AMERICA = "north.america"
    OCEANIA = "oceania"
    SOUTH_AMERICA = "south.america"


PROXY_CONTINENTS: FrozenSet[str] = frozenset(
    {
        ProxyContinents.AFRICA,
        ProxyContinents.ASIA,
        ProxyContinents.EUROPE,
        ProxyContinents.NORTH_AMERICA,
        ProxyContinents.OCEANIA,
        ProxyContinents.SOUTH_AMERICA,
    }
)


class Features:
    """The billable workflow a run belongs to."""

    EXTRACT = "extract"
    SCHEMA = "schema"


FEATURES: FrozenSet[str] = frozenset({Features.EXTRACT, Features.SCHEMA})


# --- Run lifecycle ---------------------------------------------------------


class RunStates:
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"


RUN_STATES: FrozenSet[str] = frozenset(
    {
        RunStates.QUEUED,
        RunStates.RUNNING,
        RunStates.CANCEL_REQUESTED,
        RunStates.COMPLETED,
        RunStates.FAILED,
        RunStates.CANCELLED,
        RunStates.BUDGET_EXHAUSTED,
    }
)

TERMINAL_RUN_STATES: FrozenSet[str] = frozenset(
    {
        RunStates.COMPLETED,
        RunStates.FAILED,
        RunStates.CANCELLED,
        RunStates.BUDGET_EXHAUSTED,
    }
)


class EventTypes:
    """SSE ``event:`` names on a run's public event stream.

    Match with ``event.type == EventTypes.RUN_COMPLETED``.
    """

    RUN_STARTED = "workflow.run.started"
    RUN_HEARTBEAT = "workflow.run.heartbeat"
    STEP_STARTED = "workflow.step.started"
    STEP_PROGRESS = "workflow.step.progress"
    STEP_COMPLETED = "workflow.step.completed"
    RESULT_PARTIAL = "workflow.result.partial"
    DIAGNOSTIC = "workflow.diagnostic"
    RUN_COMPLETED = "workflow.run.completed"
    RUN_FAILED = "workflow.run.failed"
    RUN_CANCELLED = "workflow.run.cancelled"
    RUN_BUDGET_EXHAUSTED = "workflow.run.budget_exhausted"


TERMINAL_EVENT_TYPES: FrozenSet[str] = frozenset(
    {
        EventTypes.RUN_COMPLETED,
        EventTypes.RUN_FAILED,
        EventTypes.RUN_CANCELLED,
        EventTypes.RUN_BUDGET_EXHAUSTED,
    }
)


class StreamDetailTypes:
    """Fine-grained ``payload.stream_event_type`` values (``event.detail_type``).

    Match with ``event.detail_type == StreamDetailTypes.RUN_TITLE_GENERATED``.
    """

    RUN_STARTED = "run.started"
    RUN_STATUS_CHANGED = "run.status_changed"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"
    RUN_BUDGET_EXHAUSTED = "run.budget_exhausted"
    RUN_TITLE_GENERATED = "run.title_generated"
    STAGE_STARTED = "stage.started"
    STAGE_PROGRESS = "stage.progress"
    STAGE_COMPLETED = "stage.completed"
    STAGE_FAILED = "stage.failed"
    STAGE_SKIPPED = "stage.skipped"
    ACTIVITY_STARTED = "activity.started"
    ACTIVITY_UPDATED = "activity.updated"
    ACTIVITY_OUTPUT_DELTA = "activity.output_delta"
    ACTIVITY_COMPLETED = "activity.completed"
    ACTIVITY_FAILED = "activity.failed"
    MESSAGE_STARTED = "message.started"
    MESSAGE_DELTA = "message.delta"
    MESSAGE_COMPLETED = "message.completed"
    RESULT_PARTIAL = "result.partial"
    RESULT_COMPLETED = "result.completed"
    DIAGNOSTIC = "diagnostic"

# --- Error codes -----------------------------------------------------------


class ErrorCodes:
    """Structured ``error.code`` values the gateway can return."""

    INSUFFICIENT_CREDITS = "insufficient_credits"
    TOO_MANY_CONCURRENT_RUNS = "too_many_concurrent_runs"
    IDEMPOTENCY_KEY_REUSE = "idempotency_key_reuse"
    INVALID_WORKFLOW_URL = "invalid_workflow_url"
    INVALID_REQUEST_CONTRACT = "invalid_request_contract"
    STREAMING_UNAVAILABLE = "streaming_unavailable"
    RUN_NOT_TERMINAL = "run_not_terminal"
    RESULT_NOT_AVAILABLE = "result_not_available"
    RESULT_TEMPORARILY_UNAVAILABLE = "result_temporarily_unavailable"
    NOT_FOUND = "not_found"
