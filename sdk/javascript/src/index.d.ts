/** Type declarations for the Makra JavaScript SDK. */

export declare const SDK_VERSION: string;
export declare const PRODUCTION_BASE_URL: string;
export declare const DEVELOPMENT_BASE_URL: string;
export declare const DUMMY_API_KEY: string;
export declare const DEFAULT_TIMEOUT_MS: number;
export declare const DEFAULT_MAX_RETRIES: number;

// --- Wire enums --------------------------------------------------------------

export type ExecutionMode = "concurrent" | "sequential";
export type ValidationMode = "observe" | "repair";
export type ProxyRegionScope = "worldwide" | "continent" | "country";
export type ProxyContinent =
  | "africa"
  | "asia"
  | "europe"
  | "north.america"
  | "oceania"
  | "south.america";
export type Feature = "extract" | "schema";
export type RunState =
  | "queued"
  | "running"
  | "cancel_requested"
  | "completed"
  | "failed"
  | "cancelled"
  | "budget_exhausted";

export declare const ExecutionModes: {
  readonly CONCURRENT: "concurrent";
  readonly SEQUENTIAL: "sequential";
};
export declare const ValidationModes: {
  readonly OBSERVE: "observe";
  readonly REPAIR: "repair";
};
export declare const ProxyRegionScopes: {
  readonly WORLDWIDE: "worldwide";
  readonly CONTINENT: "continent";
  readonly COUNTRY: "country";
};
export declare const ProxyContinents: {
  readonly AFRICA: "africa";
  readonly ASIA: "asia";
  readonly EUROPE: "europe";
  readonly NORTH_AMERICA: "north.america";
  readonly OCEANIA: "oceania";
  readonly SOUTH_AMERICA: "south.america";
};
/** ISO 3166-1 alpha-2 country codes. `Iso3166Alpha2.DE === "DE"`. */
export declare const Iso3166Alpha2: Readonly<Record<string, string>>;
export declare const ISO_3166_ALPHA2_CODES: readonly string[];
export declare const Features: { readonly EXTRACT: "extract"; readonly SCHEMA: "schema" };
export declare const RunStates: Readonly<Record<string, RunState>>;
export declare const EventTypes: {
  readonly RUN_STARTED: "workflow.run.started";
  readonly RUN_HEARTBEAT: "workflow.run.heartbeat";
  readonly STEP_STARTED: "workflow.step.started";
  readonly STEP_PROGRESS: "workflow.step.progress";
  readonly STEP_COMPLETED: "workflow.step.completed";
  readonly RESULT_PARTIAL: "workflow.result.partial";
  readonly DIAGNOSTIC: "workflow.diagnostic";
  readonly RUN_COMPLETED: "workflow.run.completed";
  readonly RUN_FAILED: "workflow.run.failed";
  readonly RUN_CANCELLED: "workflow.run.cancelled";
  readonly RUN_BUDGET_EXHAUSTED: "workflow.run.budget_exhausted";
};
export declare const StreamDetailTypes: {
  readonly RUN_STARTED: "run.started";
  readonly RUN_STATUS_CHANGED: "run.status_changed";
  readonly RUN_COMPLETED: "run.completed";
  readonly RUN_FAILED: "run.failed";
  readonly RUN_CANCELLED: "run.cancelled";
  readonly RUN_BUDGET_EXHAUSTED: "run.budget_exhausted";
  readonly RUN_TITLE_GENERATED: "run.title_generated";
  readonly STAGE_STARTED: "stage.started";
  readonly STAGE_PROGRESS: "stage.progress";
  readonly STAGE_COMPLETED: "stage.completed";
  readonly STAGE_FAILED: "stage.failed";
  readonly STAGE_SKIPPED: "stage.skipped";
  readonly ACTIVITY_STARTED: "activity.started";
  readonly ACTIVITY_UPDATED: "activity.updated";
  readonly ACTIVITY_OUTPUT_DELTA: "activity.output_delta";
  readonly ACTIVITY_COMPLETED: "activity.completed";
  readonly ACTIVITY_FAILED: "activity.failed";
  readonly MESSAGE_STARTED: "message.started";
  readonly MESSAGE_DELTA: "message.delta";
  readonly MESSAGE_COMPLETED: "message.completed";
  readonly RESULT_PARTIAL: "result.partial";
  readonly RESULT_COMPLETED: "result.completed";
  readonly DIAGNOSTIC: "diagnostic";
};
export declare const ErrorCodes: Readonly<Record<string, string>>;

// --- Request configuration ---------------------------------------------------

export interface ProxyRegionConfig {
  scope?: ProxyRegionScope | null;
  /** ISO 3166-1 alpha-2 when scope is country; a ProxyContinents slug when continent. */
  value?: string | null;
}

export interface ProxyConfig {
  region?: ProxyRegionConfig | null;
}

export interface CrawlerRecoveryConfig {
  retry?: boolean | null;
  /** 0–300000 ms. */
  retry_delay_ms?: number | null;
}

export interface CrawlerConfig {
  /** 0–120000 ms. */
  post_ready_wait_ms?: number | null;
  recovery?: CrawlerRecoveryConfig | null;
  proxy?: ProxyConfig | null;
}

export interface PaginationConfig {
  enabled?: boolean | null;
  additional_pages?: number | null;
}

export interface TitleConfig {
  enabled?: boolean | null;
}

export interface CommonConfig {
  crawler?: CrawlerConfig | null;
}

export interface ExtractConfig extends CommonConfig {
  validation_mode?: ValidationMode | null;
  pagination?: PaginationConfig | null;
  title?: TitleConfig | null;
}

export type SchemaConfig = CommonConfig;

export type JsonSchema = Record<string, unknown> | unknown[];
export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
/** Parsed JSON, a text fallback, or `undefined` for an empty/204 response. */
export type ResponseBody = JsonValue | undefined;

export interface HealthResponse {
  status: string;
  [key: string]: unknown;
}

/** Stable fields on a completed workflow response. The result data is caller-defined. */
export interface WorkflowEnvelope {
  success?: boolean;
  status?: string;
  message?: string;
  data?: unknown;
  errors?: unknown[];
  warnings?: unknown[];
  usage?: Record<string, unknown>;
  billing_state?: string;
  telemetry_run_id?: string;
  [key: string]: unknown;
}

export type ExtractResponse = WorkflowEnvelope;
export type SchemaResponse = WorkflowEnvelope;
export type RunResult = WorkflowEnvelope;

export interface BaseOptionsInit {
  postReadyWaitMs?: number;
  proxyRegion?: ProxyRegion;
  recoveryRetry?: boolean;
  recoveryRetryDelayMs?: number;
}

/** A proxy egress region. Use the static factories to avoid wire nesting. */
export declare class ProxyRegion {
  readonly scope: ProxyRegionScope;
  readonly value: string | null;
  constructor(scope: ProxyRegionScope, value?: string | null);
  static worldwide(): ProxyRegion;
  static continent(value: ProxyContinent): ProxyRegion;
  static country(value: string): ProxyRegion;
  toConfig(): ProxyRegionConfig;
}

declare class BaseOptions {
  protected constructor(options?: BaseOptionsInit);
  toConfig(): SchemaConfig;
}

/** Ergonomic configuration builder for schema generation. */
export declare class SchemaOptions extends BaseOptions {
  constructor(options?: BaseOptionsInit);
  toConfig(): SchemaConfig;
}

export interface ExtractOptionsInit extends BaseOptionsInit {
  validationMode?: ValidationMode;
  additionalPages?: number;
  paginationEnabled?: boolean;
  titleEnabled?: boolean;
}

/** Ergonomic configuration builder for structured extraction. */
export declare class ExtractOptions extends BaseOptions {
  constructor(options?: ExtractOptionsInit);
  toConfig(): ExtractConfig;
}

// --- Responses ---------------------------------------------------------------

export interface ResultSummary {
  available?: boolean;
  size_bytes?: number;
  content_type?: string;
  expires_at?: string;
  sha256?: string;
  href?: string;
  [key: string]: unknown;
}

export interface RunProgress {
  pages_total?: number;
  pages_completed?: number;
  attempt_number?: number;
  phase?: string;
  [key: string]: unknown;
}

export interface RunView {
  id?: string;
  run_id?: string;
  feature?: Feature;
  state?: RunState;
  sequence?: number;
  created_at?: string;
  started_at?: string;
  terminal_at?: string;
  updated_at?: string;
  terminal_reason?: string;
  failure_code?: string;
  progress?: RunProgress;
  result?: ResultSummary;
  result_available?: boolean;
  poll_after_ms?: number;
  response_mode?: string;
  success?: boolean;
  upstream_status?: number;
  credits_charged?: number;
  credits_charged_str?: string;
  usage?: Record<string, unknown>;
  billing_state?: string;
  telemetry_run_id?: string;
  archived?: boolean;
  [key: string]: unknown;
}

export interface RunPage {
  items?: RunView[];
  next_cursor?: string | null;
  concurrency?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface AsyncAdmission {
  run_id: string;
  feature?: Feature;
  state?: RunState;
  status_url?: string;
  events_url?: string;
  result_url?: string;
  [key: string]: unknown;
}

// --- Events ------------------------------------------------------------------

export interface ServerSentEventMessage {
  event: string;
  data: string;
  id?: string;
  retry?: number;
}

export declare class SSEDecoder {
  lastEventId?: string;
  feed(line: string): ServerSentEventMessage | null;
}

export declare class WorkflowEvent {
  readonly type: string;
  readonly sequence: number;
  readonly payload: Record<string, unknown>;
  readonly runId?: string;
  /** Whether this event closes the stream. */
  readonly isTerminal: boolean;
  /** The fine-grained step name, e.g. `StreamDetailTypes.RUN_TITLE_GENERATED`. */
  readonly detailType?: string;
  readonly status?: string;
  readonly reason?: string;
  /** Domain success on a terminal event; `undefined` before the run ends. */
  readonly success?: boolean;
}

export declare function parseEvent(
  message: ServerSentEventMessage,
  runId?: string,
): WorkflowEvent;
export declare function terminalState(event: WorkflowEvent): RunState;

// --- Errors ------------------------------------------------------------------

export declare class MakraError extends Error {}

export declare class MakraAPIError extends MakraError {
  readonly statusCode: number;
  readonly body: unknown;
  readonly method: string;
  readonly path: string;
  readonly code?: string;
  readonly requestId?: string;
}

export declare class MakraAuthenticationError extends MakraAPIError {}
export declare class MakraPermissionError extends MakraAPIError {}
export declare class MakraNotFoundError extends MakraAPIError {}
export declare class MakraServerError extends MakraAPIError {}

export declare class MakraInvalidRequestError extends MakraAPIError {
  readonly field?: string;
  readonly reason?: string;
  readonly index?: number;
}

export declare class MakraInsufficientCreditsError extends MakraAPIError {
  readonly requiredCredits?: number;
  readonly availableCredits?: number;
}

export declare class MakraRateLimitError extends MakraAPIError {
  /** Seconds, from the `Retry-After` header. */
  readonly retryAfter?: number;
  readonly concurrency?: Record<string, unknown>;
}

export declare class MakraConnectionError extends MakraError {
  readonly method: string;
  readonly path: string;
}

export declare class MakraTimeoutError extends MakraConnectionError {
  readonly runId?: string;
}

export declare class MakraStreamError extends MakraError {
  readonly runId?: string;
}

export declare class MakraResultError extends MakraStreamError {
  readonly location?: string;
}

export declare class MakraRunFailedError extends MakraError {
  readonly runId: string;
  readonly state: RunState;
  readonly run: RunView;
}

// --- Configuration -----------------------------------------------------------

export interface MakraOptions {
  /** Falls back to `MAKRA_API_KEY`. */
  apiKey?: string;
  /** Falls back to `MAKRA_BASE_URL`, then to the production gateway. */
  baseUrl?: string;
  /** Milliseconds. Falls back to `MAKRA_TIMEOUT` (seconds), then 300000. */
  timeout?: number;
  /** Milliseconds of silence that mark an event stream as dead. Default 90000. */
  streamIdleTimeout?: number;
  /** Falls back to `MAKRA_MAX_RETRIES`, then 2. */
  maxRetries?: number;
  /** Base backoff in milliseconds. Default 500. */
  retryBackoff?: number;
  defaultHeaders?: Record<string, string>;
  env?: Record<string, string | undefined>;
}

export interface ResolvedConfig {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly timeout: number;
  readonly streamIdleTimeout: number;
  readonly maxRetries: number;
  readonly retryBackoff: number;
  readonly defaultHeaders: Record<string, string>;
  headers(): Record<string, string>;
  url(path: string): string;
}

export declare function resolveConfig(options?: MakraOptions): ResolvedConfig;

// --- Operations --------------------------------------------------------------

export interface RequestOptions {
  signal?: AbortSignal;
}

export interface ExtractRequestOptions extends RequestOptions {
  urls: string[];
  schema: JsonSchema;
  /** Default `"concurrent"`. */
  executionMode?: ExecutionMode;
  config?: ExtractConfig | ExtractOptions;
  /** Supply your own to make a submission replayable across processes. */
  idempotencyKey?: string;
  /** Milliseconds; overrides the client timeout for this call. */
  timeout?: number;
}

export interface SchemaRequestOptions extends RequestOptions {
  url: string;
  /** Return only an already-memoized schema instead of building one. */
  onlyMemoized?: boolean;
  config?: SchemaConfig | SchemaOptions;
  idempotencyKey?: string;
  timeout?: number;
}

export type ExtractStreamOptions = Omit<ExtractRequestOptions, "timeout">;
export type SchemaStreamOptions = Omit<SchemaRequestOptions, "timeout">;

export interface WaitOptions extends RequestOptions {
  /** Milliseconds to keep polling before giving up. */
  timeout?: number;
  /** Minimum milliseconds between polls. */
  pollInterval?: number;
  /** Throw `MakraRunFailedError` on a non-`completed` terminal state. */
  throwOnFailure?: boolean;
}

export interface ListRunsOptions extends RequestOptions {
  limit?: number;
  cursor?: string;
  feature?: Feature;
  state?: RunState;
}

export interface StreamRunOptions extends RequestOptions {
  lastEventId?: number;
}

export declare function runIsTerminal(run: Record<string, unknown>): boolean;
export declare function runSucceeded(run: Record<string, unknown>): boolean;

/** A submitted run, observable without holding the original connection. */
export declare class RunHandle {
  readonly id: string;
  readonly feature?: Feature;
  state?: RunState;
  readonly statusUrl?: string;
  readonly eventsUrl?: string;
  readonly resultUrl?: string;
  readonly admission: AsyncAdmission;
  readonly client: Makra;

  refresh(): Promise<RunView>;
  wait(options?: WaitOptions): Promise<RunView>;
  stream(options?: StreamRunOptions): AsyncGenerator<WorkflowEvent>;
  result(): Promise<RunResult | ResponseBody>;
  cancel(): Promise<RunView>;
}

export declare class Makra {
  constructor(options?: MakraOptions);

  readonly config: ResolvedConfig;
  readonly apiKey: string;
  readonly baseUrl: string;

  ping(options?: RequestOptions): Promise<HealthResponse | ResponseBody>;
  ready(options?: RequestOptions): Promise<HealthResponse | ResponseBody>;

  extract(options: ExtractRequestOptions): Promise<ExtractResponse | ResponseBody>;
  schema(options: SchemaRequestOptions): Promise<SchemaResponse | ResponseBody>;

  extractStream(options: ExtractStreamOptions): AsyncGenerator<WorkflowEvent>;
  schemaStream(options: SchemaStreamOptions): AsyncGenerator<WorkflowEvent>;
  streamRunEvents(runId: string, options?: StreamRunOptions): AsyncGenerator<WorkflowEvent>;

  submitExtract(options: ExtractStreamOptions): Promise<RunHandle>;
  submitSchema(options: SchemaStreamOptions): Promise<RunHandle>;

  getRun(runId: string, options?: RequestOptions): Promise<RunView>;
  listRuns(options?: ListRunsOptions): Promise<RunPage>;
  cancelRun(runId: string, options?: RequestOptions): Promise<RunView>;
  waitForRun(runId: string, options?: WaitOptions): Promise<RunView>;
  getRunResult(runId: string, options?: RequestOptions): Promise<RunResult | ResponseBody>;
}
