"""Wire-level constants for the Makra API.

Every URL, header, enum value, and default the SDK depends on is declared here
so the client modules stay free of scattered string literals. Changing the HTTP
surface should mean changing this file and nothing else.
"""

from __future__ import annotations

from typing import FrozenSet

SDK_VERSION = "0.1.0"
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
HEADER_RETRY_AFTER = "Retry-After"
HEADER_REQUEST_ID = "X-Request-Id"
HEADER_RUN_ID = "X-Makra-Run-Id"
HEADER_USAGE_STATUS = "X-Makra-Usage-Status"
HEADER_CREDITS_CHARGED = "X-Makra-Credits-Charged"
HEADER_TELEMETRY_RUN_ID = "X-Makra-Telemetry-Run-Id"

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


class SelectorChainVersions:
    V1 = "v1"
    V2 = "v2"


SELECTOR_CHAIN_VERSIONS: FrozenSet[str] = frozenset(
    {SelectorChainVersions.V1, SelectorChainVersions.V2}
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


class Features:
    """The billable workflow a run belongs to."""

    EXTRACT = "extract"
    SCHEMA = "schema"


# --- Run lifecycle ---------------------------------------------------------


class RunStates:
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"


TERMINAL_RUN_STATES: FrozenSet[str] = frozenset(
    {
        RunStates.COMPLETED,
        RunStates.FAILED,
        RunStates.CANCELLED,
        RunStates.BUDGET_EXHAUSTED,
    }
)


class EventTypes:
    """SSE ``event:`` names emitted on a run's event stream."""

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
