/**
 * Wire-level constants for the Makra API.
 *
 * Every URL, header, enum value, and default the SDK depends on is declared
 * here so the client modules stay free of scattered string literals. Changing
 * the HTTP surface should mean changing this file and nothing else.
 */

export const SDK_VERSION = "0.1.0";
export const USER_AGENT = `makra-js/${SDK_VERSION}`;

// --- Endpoints -------------------------------------------------------------

export const PRODUCTION_BASE_URL = "https://api.makralabs.org";
export const DEVELOPMENT_BASE_URL = "http://localhost:8080";

export const PATH_HEALTH = "/healthz";
export const PATH_READY = "/healthz/ready";
export const PATH_EXTRACT = "/workflows/extract";
export const PATH_SCHEMA = "/workflows/schema";
export const PATH_RUNS = "/workflows/runs";

/** Build the path of a single run resource, e.g. `/runs/<id>/result`. */
export function runPath(runId, suffix = "") {
  return `${PATH_RUNS}/${runId}${suffix}`;
}

// --- Configuration ---------------------------------------------------------

export const ENV_API_KEY = "MAKRA_API_KEY";
export const ENV_BASE_URL = "MAKRA_BASE_URL";
export const ENV_TIMEOUT = "MAKRA_TIMEOUT";
export const ENV_MAX_RETRIES = "MAKRA_MAX_RETRIES";

/**
 * Temporary shared key for local development against a gateway that does not
 * yet enforce authentication. It is not a secret.
 */
export const DUMMY_API_KEY = "makra-development-key";

/**
 * A synchronous submission holds the connection until the run is terminal, so
 * the request timeout is really "how long may a workflow take".
 */
export const DEFAULT_TIMEOUT_MS = 300_000;
/**
 * The gateway emits an SSE heartbeat every 15 seconds. A read gap far larger
 * than that means the connection died, not that the run is slow.
 */
export const DEFAULT_STREAM_IDLE_TIMEOUT_MS = 90_000;
export const DEFAULT_MAX_RETRIES = 2;
export const DEFAULT_RETRY_BACKOFF_MS = 500;
export const MAX_RETRY_BACKOFF_MS = 8_000;
export const DEFAULT_POLL_INTERVAL_MS = 2_000;

// --- Headers ---------------------------------------------------------------

export const HEADER_API_KEY = "Api-Key";
export const HEADER_IDEMPOTENCY_KEY = "Idempotency-Key";
export const HEADER_PREFER = "Prefer";
export const HEADER_LAST_EVENT_ID = "Last-Event-ID";
export const HEADER_RETRY_AFTER = "Retry-After";
export const HEADER_REQUEST_ID = "X-Request-Id";
export const HEADER_RUN_ID = "X-Makra-Run-Id";
export const HEADER_USAGE_STATUS = "X-Makra-Usage-Status";
export const HEADER_CREDITS_CHARGED = "X-Makra-Credits-Charged";
export const HEADER_TELEMETRY_RUN_ID = "X-Makra-Telemetry-Run-Id";

export const PREFER_RESPOND_ASYNC = "respond-async";

export const CONTENT_TYPE_JSON = "application/json";
export const CONTENT_TYPE_SSE = "text/event-stream";

// --- Request enums ---------------------------------------------------------

/** How multiple URLs in one extract request are processed. */
export const ExecutionModes = Object.freeze({
  CONCURRENT: "concurrent",
  SEQUENTIAL: "sequential",
});

/** What the extract workflow does when output fails schema validation. */
export const ValidationModes = Object.freeze({
  OBSERVE: "observe",
  REPAIR: "repair",
});

export const SelectorChainVersions = Object.freeze({ V1: "v1", V2: "v2" });

export const ProxyRegionScopes = Object.freeze({
  WORLDWIDE: "worldwide",
  CONTINENT: "continent",
  COUNTRY: "country",
});

/** The billable workflow a run belongs to. */
export const Features = Object.freeze({ EXTRACT: "extract", SCHEMA: "schema" });

export const EXECUTION_MODES = new Set(Object.values(ExecutionModes));
export const VALIDATION_MODES = new Set(Object.values(ValidationModes));
export const SELECTOR_CHAIN_VERSIONS = new Set(
  Object.values(SelectorChainVersions),
);
export const PROXY_REGION_SCOPES = new Set(Object.values(ProxyRegionScopes));

// --- Run lifecycle ---------------------------------------------------------

export const RunStates = Object.freeze({
  QUEUED: "queued",
  RUNNING: "running",
  CANCEL_REQUESTED: "cancel_requested",
  COMPLETED: "completed",
  FAILED: "failed",
  CANCELLED: "cancelled",
  BUDGET_EXHAUSTED: "budget_exhausted",
});

export const TERMINAL_RUN_STATES = new Set([
  RunStates.COMPLETED,
  RunStates.FAILED,
  RunStates.CANCELLED,
  RunStates.BUDGET_EXHAUSTED,
]);

/** SSE `event:` names emitted on a run's event stream. */
export const EventTypes = Object.freeze({
  RUN_STARTED: "workflow.run.started",
  RUN_HEARTBEAT: "workflow.run.heartbeat",
  STEP_STARTED: "workflow.step.started",
  STEP_PROGRESS: "workflow.step.progress",
  STEP_COMPLETED: "workflow.step.completed",
  RESULT_PARTIAL: "workflow.result.partial",
  DIAGNOSTIC: "workflow.diagnostic",
  RUN_COMPLETED: "workflow.run.completed",
  RUN_FAILED: "workflow.run.failed",
  RUN_CANCELLED: "workflow.run.cancelled",
  RUN_BUDGET_EXHAUSTED: "workflow.run.budget_exhausted",
});

export const TERMINAL_EVENT_TYPES = new Set([
  EventTypes.RUN_COMPLETED,
  EventTypes.RUN_FAILED,
  EventTypes.RUN_CANCELLED,
  EventTypes.RUN_BUDGET_EXHAUSTED,
]);

// --- Error codes -----------------------------------------------------------

/** Structured `error.code` values the gateway can return. */
export const ErrorCodes = Object.freeze({
  INSUFFICIENT_CREDITS: "insufficient_credits",
  TOO_MANY_CONCURRENT_RUNS: "too_many_concurrent_runs",
  IDEMPOTENCY_KEY_REUSE: "idempotency_key_reuse",
  INVALID_WORKFLOW_URL: "invalid_workflow_url",
  INVALID_REQUEST_CONTRACT: "invalid_request_contract",
  STREAMING_UNAVAILABLE: "streaming_unavailable",
  RUN_NOT_TERMINAL: "run_not_terminal",
  RESULT_NOT_AVAILABLE: "result_not_available",
  RESULT_TEMPORARILY_UNAVAILABLE: "result_temporarily_unavailable",
  NOT_FOUND: "not_found",
});
