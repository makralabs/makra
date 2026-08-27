# Makra SDK Specification

Status: **Normative draft for SDK version 0.2.0**

This document is the language-neutral source of truth for generating and
maintaining the official `makra` packages for Python (PyPI) and JavaScript
(npm). The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.
Where this document and an implementation disagree, this document wins.

Version 0.2.0 aligns the public behavior of the Python and JavaScript packages.
Both ship typed response declarations, workflow configuration builders,
outcome helpers, reserved-header rejection, operation argument validation, and
`MakraResultError`. Language naming and duration units remain idiomatic.

## 1. Goals and scope

The SDK provides a small, typed client for the public Makra HTTP API. Version
0.1 covers:

- API connectivity and readiness checks;
- structured extraction from one or more URLs;
- page-schema generation for a single URL;
- all three workflow response modes: blocking, streaming (SSE), and deferred;
- run management: status, listing, cancellation, polling, result retrieval;
- request-overridable workflow configuration;
- API-key authentication and idempotent submission;
- bounded automatic retries for transient failures;
- consistent HTTP, transport, and stream errors.

The SDK is a transport wrapper. It MUST NOT reinterpret successful response
payloads, hide Makra response metadata, or couple users to server-internal
Python models.

Natural-language query extraction, request-level `actions`, provider
configuration, telemetry processing, and API-key issuance are outside version
0.1. These require a future spec revision.

## 2. Packages and runtime support

| Ecosystem | Registry name | Source directory | Minimum runtime |
| --- | --- | --- | --- |
| Python | `makra` | `sdk/python` | Python 3.9 |
| JavaScript | `makra` | `sdk/javascript` | Node.js 18, ESM |

Both packages MUST use semantic versioning and SHOULD share a public SDK
version. Both packages are `0.2.0`. The initial joint release was `0.1.0`.

Python MUST ship a `py.typed` marker and type hints. JavaScript MUST ship an
ESM entry point and TypeScript declarations even though the implementation is
JavaScript.

## 3. Configuration

### 3.1 Defaults

| Setting | Default | Rationale |
| --- | --- | --- |
| Production base URL | `https://api.makralabs.org` | |
| Development base URL constant | `http://localhost:8080` | |
| API key fallback | `makra-development-key` | |
| Request timeout | 300 s / 300,000 ms per origin page | Blocking submissions hold the connection until the run is terminal. Paginated extracts and sequential multi-URL extracts multiply this budget automatically unless the caller passes an explicit timeout. |
| Connect timeout (Python only) | 10 s | |
| Stream idle timeout | 90 s / 90,000 ms | The gateway heartbeats every 15 s; a far larger gap means a dead connection |
| Max retries | 2 | |
| Retry backoff base | 0.5 s / 500 ms | |
| Retry backoff ceiling | 8 s / 8,000 ms | |
| Poll interval floor | 2 s / 2,000 ms | |

Durations are expressed in the unit idiomatic to each language: seconds in
Python, milliseconds in JavaScript.

The production URL MUST be the default. Development scripts MUST explicitly
select the development URL (local public API gateway).

The dummy API key is temporary. It ensures development requests exercise the
production authentication wire format before the server enforces keys. It is
not a secret and MUST NOT be presented as one. When authentication is enabled,
applications MUST pass a real key.

### 3.2 Resolution order

Configuration MUST resolve in this order:

1. explicit constructor option;
2. environment variable;
3. SDK default.

The supported environment variables are:

| Variable | Setting | Unit |
| --- | --- | --- |
| `MAKRA_API_KEY` | API key | — |
| `MAKRA_BASE_URL` | Base URL | — |
| `MAKRA_TIMEOUT` | Request timeout | **seconds in both languages** |
| `MAKRA_MAX_RETRIES` | Retry budget | count |

`MAKRA_TIMEOUT` is language-neutral, so it is read in seconds even by the
JavaScript SDK, which converts it to milliseconds internally.

An explicit empty API key is treated as absent and falls through to the
environment/default. A base URL MUST be an absolute `http://` or `https://`
URL. Trailing slashes MUST be removed before path construction.

Timeouts and backoffs MUST be greater than zero and the retry budget MUST NOT
be negative; violations fail at construction time (§8.2).

### 3.3 Authentication and common headers

Every request, including development requests and `ping`, MUST send:

```http
Api-Key: <api-key>
Content-Type: application/json
Accept: application/json
```

Each implementation SHOULD also send a language-specific user agent containing
the SDK version. API keys MUST NOT appear in exception messages or logs.

Request-specific headers are added per operation:

| Header | Sent on | Value |
| --- | --- | --- |
| `Idempotency-Key` | every workflow submission | caller-supplied, else `makra-sdk-<uuid4 hex>` |
| `Prefer` | deferred submissions | `respond-async` |
| `Accept` | streaming requests | `text/event-stream` |
| `Last-Event-ID` | resumed streams | highest sequence already delivered |

The API key MUST NOT be sent to any host other than the configured base URL.
This is normative for result retrieval, which redirects to presigned object
storage (§5.9).

The following request header names are SDK-owned and MUST be treated
case-insensitively as reserved: `Api-Key`, `Content-Type`, `Accept`,
`User-Agent`, `Idempotency-Key`, `Prefer`, `Last-Event-ID`. **Python 0.2.0:**
collisions in `default_headers` MUST raise `ValueError` naming the header and
the supported constructor or operation argument. Arbitrary tracing and
application headers remain allowed. JavaScript parity for this rejection is
outstanding.

## 4. Public clients

### 4.1 Python

The package MUST export:

- `Makra`: synchronous client;
- `AsyncMakra`: asynchronous client with the same operations;
- `RunHandle` and `AsyncRunHandle`;
- `WorkflowEvent`;
- the full error hierarchy of §8.1;
- `PRODUCTION_BASE_URL`, `DEVELOPMENT_BASE_URL`, `SDK_VERSION`, and the enum
  namespaces `ExecutionModes`, `ValidationModes`, `Iso3166Alpha2`,
  `ProxyRegionScopes`, `ProxyContinents`, `Features`, `RunStates`,
  `EventTypes`, `StreamDetailTypes`, `ErrorCodes`;
- typed config aliases used by operations (`CommonConfig`, `ExtractConfig`,
  `SchemaConfig`) and response aliases (`HealthResponse`, `WorkflowEnvelope`,
  `ExtractResponse`, `SchemaResponse`, `RunResult`, `RunView`, `RunPage`,
  `AsyncAdmission`, `ResponseBody`);
- `ExtractOptions`, `SchemaOptions`, `ProxyRegion`, the run outcome helpers,
  and `MakraResultError`.

Constructor:

```python
Makra(
    api_key: str | None = None,
    *,
    base_url: str | None = None,
    timeout: float = 300.0,
    connect_timeout: float = 10.0,
    stream_idle_timeout: float = 90.0,
    max_retries: int = 2,
    retry_backoff: float = 0.5,
    default_headers: Mapping[str, str] | None = None,
)
```

`Makra` MUST support `with` and `close()`. `AsyncMakra` MUST support
`async with` and `await close()`. Closing a client releases its HTTP resources.

Python public operation names and arguments use `snake_case`. Successful
operation responses are the complete decoded server body: parsed JSON, text, or
`None`. They MUST NOT be wrapped or unwrapped. Python types those bodies
with the aliases in §7.1; the annotations describe the returned value and MUST
NOT claim a narrower shape than the decoder can produce.

### 4.2 JavaScript

The package MUST export:

- `Makra`;
- `RunHandle`, `WorkflowEvent`, and `SSEDecoder`;
- `ExtractOptions`, `SchemaOptions`, `ProxyRegion`, `runIsTerminal`, and
  `runSucceeded`;
- the full error hierarchy of §8.1;
- `PRODUCTION_BASE_URL`, `DEVELOPMENT_BASE_URL`, `DUMMY_API_KEY`,
  `SDK_VERSION`, and the enum namespaces listed in §4.1;
- declarations for all public options and JSON values.

Constructor:

```js
new Makra({
  apiKey,
  baseUrl,
  timeout = 300_000,
  streamIdleTimeout = 90_000,
  maxRetries = 2,
  retryBackoff = 500,
  defaultHeaders = {},
} = {})
```

JavaScript public operation names and arguments use `camelCase`. Nested
workflow `config` objects use the wire field names from §6 (snake_case keys).
Non-streaming operations return a `Promise`; streaming operations return an
`AsyncGenerator` of `WorkflowEvent`. No close method is required because the
standard `fetch` transport owns no per-client resource.

Every operation MUST accept an optional `signal` (`AbortSignal`). A caller
abort MUST propagate untouched so it stays distinguishable from a timeout.

## 5. Operation contract

This section defines the public signature, HTTP request, and wire-name mapping.
No implementation may add, omit, or rename wire fields without updating this
spec.

### 5.0 Response modes

Both workflows accept the same input in three response modes. The mode is
selected entirely by the request, and each mode has its own SDK method so the
return type is unambiguous.

| Mode | Selected by | Server response | SDK methods |
| --- | --- | --- | --- |
| Blocking | neither of the below | `200` with the workflow envelope | `extract`, `schema` |
| Streaming | body `"stream": true` | `200 text/event-stream` | `extract_stream`, `schema_stream` |
| Deferred | header `Prefer: respond-async` | `202` with an admission object | `submit_extract`, `submit_schema` |

A client MUST NOT send both `"stream": true` and `Prefer: respond-async` on one
request.

### 5.1 `ping` and `ready`

Connectivity checks. `ping` reaches only the gateway; `ready` additionally
confirms that result storage is reachable.

| Item | Value |
| --- | --- |
| Method/path | `GET /healthz`, `GET /healthz/ready` |
| Request body | none |
| Success body | `{"status": "ok"}` |
| Python | `ping()`, `ready()` → `HealthResponse \| ResponseBody` |
| JavaScript | `ping()`, `ready()` |

A degraded ready check is an HTTP error (not a successful body) and MUST raise
`MakraAPIError`. Empty or non-JSON success bodies remain valid decoder outputs
and are why the Python return type includes `ResponseBody`.

### 5.2 `extract`

Extracts structured information from one or more pages using a JSON target
schema. Natural-language `query` input is not supported.

| Item | Python | JavaScript | Wire field |
| --- | --- | --- | --- |
| URLs, required | `urls` | `urls` | `urls` |
| Schema, required | `schema` | `schema` | `schema` |
| Execution mode, optional | `execution_mode` | `executionMode` | `execution_mode` |
| Config, optional | `config` | `config` | `config` |

HTTP request:

```http
POST /workflows/extract
```

```json
{
  "urls": ["https://example.com"],
  "schema": {"title": "The page title"},
  "execution_mode": "concurrent",
  "config": {}
}
```

`urls` MUST contain at least one non-empty string. `schema` MUST be a non-empty
JSON object or array. The schema is a target shape with field descriptions, not
necessarily a strict JSON Schema document.

`execution_mode` MUST be `"concurrent"` (default when omitted) or
`"sequential"`. Omitted `config` MUST be sent as `{}`.

Clients MUST NOT send `query`, `actions`, or `output_schema`.

Python signature:

```python
extract(urls, schema, *, execution_mode="concurrent", config=None, idempotency_key=None, timeout=None)
```

`config` MAY be an `ExtractConfig` mapping or an
`ExtractOptions` instance. The request builder MUST convert option objects to
the mapping shape before the shared normalization path, so dictionary and
options inputs that express the same fields produce identical wire JSON.

JavaScript signature:

```js
extract({ urls, schema, executionMode = "concurrent", config = {} })
```

### 5.3 `schema`

Builds or reconstructs an extraction schema for one page.

| Item | Python | JavaScript | Wire field | Default |
| --- | --- | --- | --- | --- |
| URL, required | `url` | `url` | `url` | required |
| Only memoized, optional | `only_memoized` | `onlyMemoized` | `only_memoized` | `false` |
| Config, optional | `config` | `config` | `config` | `{}` |

HTTP request:

```http
POST /workflows/schema
```

```json
{
  "url": "https://example.com/products",
  "only_memoized": false,
  "config": {}
}
```

`url` MUST be a non-empty string. Omitted `config` MUST be sent as `{}`.

Python: `schema(url, *, only_memoized=False, config=None, idempotency_key=None, timeout=None)`

`config` MAY be a `SchemaConfig` mapping or a `SchemaOptions`
instance, converted the same way as extract options.

JavaScript: `schema({ url, onlyMemoized = false, config = {} })`

### 5.4 Streaming variants

| Item | Python | JavaScript |
| --- | --- | --- |
| Extract | `extract_stream(urls, schema, *, execution_mode, config, idempotency_key)` | `extractStream({ urls, schema, executionMode, config, idempotencyKey, signal })` |
| Schema | `schema_stream(url, *, only_memoized, config, idempotency_key)` | `schemaStream({ url, onlyMemoized, config, idempotencyKey, signal })` |

The request body is that of §5.2/§5.3 with `"stream": true` added. `Accept`
MUST be `text/event-stream`.

Argument validation MUST happen when the method is called, not when the
returned iterator is first advanced.

Implementations MUST reject a non-`text/event-stream` success response with
`MakraStreamError` rather than silently returning no events.

### 5.5 Event contract

The gateway frames events per the WHATWG SSE specification. Implementations
MUST handle: `id`, `event`, and `data` fields; multi-line `data` joined with
`\n`; a leading single space stripped from each value; comment lines beginning
with `:` (the gateway sends `: keepalive` every 15 seconds) ignored; and a
blank line dispatching the accumulated message.

Each dispatched message MUST be exposed as an event object:

| Concept | Python | JavaScript | Source |
| --- | --- | --- | --- |
| Event name | `type` | `type` | SSE `event:` |
| Monotonic sequence | `sequence` | `sequence` | SSE `id:`, `0` when absent |
| Decoded body | `payload` | `payload` | SSE `data:` |
| Owning run | `run_id` | `runId` | `X-Makra-Run-Id` |
| Closes the stream | `is_terminal` | `isTerminal` | derived |
| Step name | `detail_type` | `detailType` | `payload.stream_event_type` |
| Status / reason / success | `status`, `reason`, `success` | same, camelCase | payload fields |

Callers MUST be able to match `type` against `EventTypes` and `detail_type` /
`detailType` against `StreamDetailTypes` without string literals.

Terminal event names are `workflow.run.completed`, `workflow.run.failed`,
`workflow.run.cancelled`, and `workflow.run.budget_exhausted`. Iteration MUST
stop after yielding a terminal event.

A stream MUST NOT be treated as carrying the result payload. Callers obtain
data through §5.9 after a terminal event.

### 5.6 Stream resumption

If a stream ends without a terminal event — connection reset, or silence
exceeding the stream idle timeout — the implementation MUST attempt to resume,
up to the retry budget, by issuing:

```http
GET /workflows/runs/{run_id}/events
Last-Event-ID: <highest sequence delivered>
```

Resumption MUST NOT repeat the original `POST`, which would start a second
billable run. Delivering an event MUST reset the retry budget, so a long,
healthy run is never cut short by earlier reconnects. When the run id is
unknown or the budget is exhausted, the implementation MUST raise
`MakraStreamError` carrying the run id when known.

### 5.7 Deferred submission

| Item | Python | JavaScript |
| --- | --- | --- |
| Extract | `submit_extract(...) -> RunHandle` | `submitExtract(...) -> Promise<RunHandle>` |
| Schema | `submit_schema(...) -> RunHandle` | `submitSchema(...) -> Promise<RunHandle>` |

The request body is that of §5.2/§5.3 with `Prefer: respond-async`. The server
answers `202` with an admission object, and the SDK wraps it in a handle
exposing `id`, `feature`, `state`, `status_url`, `events_url`, `result_url`,
and the raw `admission`.

A handle MUST offer `refresh`, `wait`, `stream`, `result`, and `cancel`, each
delegating to the corresponding client operation in §5.8–§5.9. A handle is a
convenience only: a run id alone MUST be sufficient to do everything a handle
can do.

### 5.8 Run management

| Operation | Method/path | Python | JavaScript |
| --- | --- | --- | --- |
| Fetch one run | `GET /workflows/runs/{id}` | `get_run(run_id)` | `getRun(runId)` |
| List runs | `GET /workflows/runs` | `list_runs(*, limit, cursor, feature, state)` | `listRuns({ limit, cursor, feature, state })` |
| Cancel | `POST /workflows/runs/{id}/cancel` | `cancel_run(run_id)` | `cancelRun(runId)` |
| Stream events | `GET /workflows/runs/{id}/events` | `stream_run_events(run_id, *, last_event_id)` | `streamRunEvents(runId, { lastEventId })` |
| Poll to terminal | — | `wait_for_run(run_id, ...)` | `waitForRun(runId, ...)` |

Terminal run states are `completed`, `failed`, `cancelled`, and
`budget_exhausted`.

`wait_for_run` MUST poll until the run is terminal or the timeout expires, and
MUST respect the server's `poll_after_ms` hint as a lower bound on the interval.
A non-`completed` terminal state raises `MakraRunFailedError` unless the caller
opts out (`raise_on_failure=False` / `throwOnFailure: false`). A `completed`
run whose payload reports `success: false` is a domain outcome, not an SDK
error, and MUST be returned.

### 5.9 Result retrieval

| Item | Value |
| --- | --- |
| Method/path | `GET /workflows/runs/{id}/result` |
| Python | `get_run_result(run_id)` → `RunResult \| ResponseBody` |
| JavaScript | `getRunResult(runId)` |

The gateway either streams the stored payload directly or answers `303 See
Other` with a presigned object-storage URL. Implementations MUST NOT let the
HTTP client follow this redirect automatically, because the `Api-Key` header
would be forwarded to a third-party host. They MUST instead issue an
unauthenticated request to the `Location` target. A redirect without a
`Location`, or with a `Location` that is not an absolute `http` or `https`
URL, raises `MakraResultError`. `MakraResultError` is a
subclass of `MakraStreamError` during this compatibility period so existing
stream catches still work. Exception messages and the optional `location`
attribute MUST NOT include a presigned query string.

### 5.10 Retries and idempotency

Implementations MUST retry only on statuses `408`, `409`, `425`, `429`, `500`,
`502`, `503`, and `504`, and on transport failures, up to `max_retries`.

`409` MUST NOT be retried when the structured error code is
`idempotency_key_reuse` or `run_not_terminal`; those are genuine conflicts, not
races.

The delay MUST be `Retry-After` when the server supplies it, otherwise
exponential backoff with full jitter, capped at the backoff ceiling in §3.1.

Every workflow submission MUST carry an `Idempotency-Key`. Without it a retried
`POST` could start — and bill — a second run. Implementations MUST generate one
per submission when the caller does not supply it.

### 5.11 Run outcome helpers

Both packages MUST export two pure helpers that interpret a run mapping without
wrapping it:

```python
run_is_terminal(run: Mapping[str, Any]) -> bool
run_succeeded(run: Mapping[str, Any]) -> bool
```

```js
runIsTerminal(run)
runSucceeded(run)
```

`run_is_terminal` is true when `state` is one of `completed`, `failed`,
`cancelled`, or `budget_exhausted` — the same `TERMINAL_RUN_STATES` set used by
polling. `run_succeeded` is true only when `state == "completed"` and
`success is not False`. Absence of `success` on a completed run is treated as
successful for compatibility with existing run responses. Incomplete states
(`queued`, `running`, `cancel_requested`), missing `state`, and every
non-completed terminal state are not successful.

`WorkflowEvent.success` is unchanged.

## 6. Workflow `config`

`config` is a nested JSON object. Deployment policy supplies defaults; callers
override only the keys they set. Unknown keys are rejected by the server.

SDK public names MUST be used in Python and JavaScript `config` objects. One
recovery pair is renamed for callers and mapped onto the wire names before the
request is sent:

| SDK config path | Wire path |
| --- | --- |
| `crawler.recovery.retry` | `crawler.recovery.one_last_retry` |
| `crawler.recovery.retry_delay_ms` | `crawler.recovery.one_last_retry_delay_ms` |

Implementations MUST reject `config.memory`, `config.audit`,
`selector_chain_version`, and the wire recovery names `one_last_retry` /
`one_last_retry_delay_ms` when they appear on the public `config` object.

### 6.1 Common config (extract and schema)

These keys MAY appear on both `extract` and `schema` requests:

```json
{
  "crawler": {
    "post_ready_wait_ms": null,
    "proxy": {
      "region": {
        "scope": "worldwide",
        "value": null
      }
    },
    "recovery": {
      "retry": true,
      "retry_delay_ms": null
    }
  }
}
```

| Path | Type | Default | Notes |
| --- | --- | --- | --- |
| `crawler.post_ready_wait_ms` | integer \| null | `null` | `0`–`120000`; `null` uses deployment default |
| `crawler.proxy.region.scope` | string | `"worldwide"` | Allowed: `"worldwide"`, `"continent"`, `"country"` |
| `crawler.proxy.region.value` | string \| null | `null` | `null` for worldwide; a `ProxyContinents` slug; an ISO 3166-1 alpha-2 code (`Iso3166Alpha2`) |
| `crawler.recovery.retry` | boolean | `true` | One final fresh-session retry |
| `crawler.recovery.retry_delay_ms` | integer \| null | `null` | `0`–`300000`; `null` uses deployment default |

Proxy mode and credentials are deployment policy. Callers only select the exit
region. Country values MUST be ISO 3166-1 alpha-2 codes; continent values MUST
be one of `africa`, `asia`, `europe`, `north.america`, `oceania`,
`south.america`.

### 6.2 Extract-only config

These keys are valid only on `extract` requests:

```json
{
  "validation_mode": "repair",
  "pagination": {
    "enabled": false,
    "additional_pages": 0
  },
  "title": {
    "enabled": true
  }
}
```

| Path | Type | Default | Notes |
| --- | --- | --- | --- |
| `validation_mode` | string \| null | `"repair"` | Allowed: `"observe"`, `"repair"`, `null` |
| `pagination.enabled` | boolean | `false` | Follow next-page controls |
| `pagination.additional_pages` | integer | `0` | Must be `>= 0`; pages beyond the origin URL |
| `title.enabled` | boolean | deployment default | Generate a human-readable run title |

When `pagination.enabled` is true, the default blocking and `wait` timeout
MUST be `base * (1 + additional_pages)`. Sequential extract additionally
multiplies by the URL count. An explicit `timeout` argument disables scaling.
Stream idle timeout is unchanged: it bounds silence between SSE events, not
run duration.

### 6.3 Schema-only config

Beyond the common keys in §6.1, `schema` requests have no additional public
config keys in version 0.1. Top-level `only_memoized` remains a request field,
not a `config` key.

### 6.4 Language typing

Python SHOULD expose `TypedDict` helpers (`CommonConfig`, `ExtractConfig`,
`SchemaConfig`) documenting the shapes above. JavaScript MUST declare matching
interfaces. Implementations MAY perform light client-side validation of enums
and ranges, but MUST still fail before network I/O for empty URLs and empty
schemas.

### 6.5 Option objects

Both packages MAY accept `ExtractOptions` and `SchemaOptions` in addition to the
nested dictionaries in §6.1–§6.2. These frozen objects hide wire nesting and
MUST convert themselves into the existing mapping shape before the single
normalization and validation path. Unset fields MUST be omitted so deployment
defaults continue to apply.

```python
ExtractOptions(
    validation_mode=ValidationModes.REPAIR,
    additional_pages=2,
    proxy_region=ProxyRegion.country(Iso3166Alpha2.DE),
    recovery_retry=True,
)
```

```js
new ExtractOptions({
  validationMode: ValidationModes.REPAIR,
  additionalPages: 2,
  proxyRegion: ProxyRegion.country(Iso3166Alpha2.DE),
  recoveryRetry: true,
})
```

`additional_pages=None` leaves pagination unspecified. Setting
`additional_pages` without `pagination_enabled` enables pagination, including
`additional_pages=0` as enabled-with-zero-extra-pages. Shared crawler fields
live on an internal `BaseOptions` base; `ExtractOptions` does not subclass
`SchemaOptions`. `ProxyRegion` is the only nested value object; crawler,
recovery, pagination, and title settings are fields on the top-level option
objects.

Dictionary configuration remains supported in both packages.

## 7. Response decoding

Clients MUST preserve the complete successful server response.

1. HTTP 204 or an empty response body returns Python `None` / JavaScript
   `undefined`.
2. A response whose `Content-Type` contains `json` is parsed as JSON.
3. A non-JSON response is returned as text.
4. If a response claims JSON but cannot be parsed, its text body is returned.
5. Any HTTP status from 400 through 599 raises/rejects `MakraAPIError`, even
   when the JSON body has a `success` field.

Version 0.2 does not unwrap a `{ success, data, ... }` envelope. Runtime
response values remain the decoded server body.

### 7.1 Response aliases

These Python aliases and TypeScript declarations describe the value a method returns. They MUST
NOT transform it. Only fields guaranteed by the server contract belong on the
typed envelope; unstable feature data remains untyped inside it.

| Alias | Used by | Stable fields |
| --- | --- | --- |
| `ResponseBody` | union member wherever the decoder may return text/`None` | parsed JSON, text, or `None` |
| `HealthResponse` | `ping`, `ready` | `status` |
| `WorkflowEnvelope` | blocking workflow bodies | `success`, `status`, `message`, `data`, `errors`, `warnings`, `usage`, `billing_state`, `telemetry_run_id` |
| `ExtractResponse` | `extract` | the workflow envelope |
| `SchemaResponse` | `schema` | the workflow envelope |
| `RunResult` | `get_run_result`, handle `result()` | the stored workflow envelope |

Method annotations MUST keep the `| ResponseBody` union when empty or non-JSON
success bodies remain valid decoder outputs.

## 8. Errors

### 8.1 Hierarchy

`MakraError` is the base SDK error. Implementations MUST provide this exact
tree so that catching a parent keeps working when a new leaf is added:

```
MakraError
├── MakraAPIError                      HTTP 4xx/5xx
│   ├── MakraAuthenticationError       401
│   ├── MakraInsufficientCreditsError  402
│   ├── MakraPermissionError           403
│   ├── MakraNotFoundError             404
│   ├── MakraRateLimitError            429, or code too_many_concurrent_runs
│   ├── MakraServerError               5xx
│   └── MakraInvalidRequestError       any other 4xx
├── MakraConnectionError               never reached the API
│   └── MakraTimeoutError
├── MakraStreamError                   stream ended before a terminal event
│   └── MakraResultError               result redirect/download contract failure
└── MakraRunFailedError                run terminal in a non-completed state
```

Subclass-specific attributes, read from the structured `error` object when
present:

| Error | Python | JavaScript |
| --- | --- | --- |
| `MakraInvalidRequestError` | `field`, `reason`, `index` | `field`, `reason`, `index` |
| `MakraInsufficientCreditsError` | `required_credits`, `available_credits` | `requiredCredits`, `availableCredits` |
| `MakraRateLimitError` | `retry_after`, `concurrency` | `retryAfter`, `concurrency` |
| `MakraStreamError` | `run_id` | `runId` |
| `MakraResultError` | `run_id`, `location` | outstanding |
| `MakraRunFailedError` | `run_id`, `state`, `run` | `runId`, `state`, `run` |

`MakraAPIError` represents an HTTP error response and MUST expose:

| Concept | Python | JavaScript |
| --- | --- | --- |
| HTTP status | `status_code` | `statusCode` |
| decoded response | `body` | `body` |
| request method | `method` | `method` |
| request path | `path` | `path` |
| optional request ID | `request_id` | `requestId` |
| structured error code | `code` | `code` |
| readable message | `message` | `message` |

The message MUST select, in order: `error.message` from the structured
envelope; then the first non-empty string among the top-level JSON fields
`message`, `detail`, and `error`; then a non-empty text body; then
`Makra API returned HTTP <status>`.

`code` MUST be `error.code` when the structured envelope is present, and absent
otherwise. Implementations MUST NOT branch on message text.

`MakraConnectionError` represents DNS, connection, timeout, abort, or response
contract failures. It MUST expose the request method and path when known, and
MUST retain the original exception as the Python exception cause or JavaScript
`cause`.

### 8.2 Client validation

Invalid constructor or operation arguments MUST fail before network I/O.
Python uses `ValueError`; JavaScript uses `TypeError` for wrong shapes and
`RangeError` for out-of-range values. Validation errors are not `MakraAPIError`
and MUST NOT be retried.

Validation MUST cover the constraints the API itself enforces — non-empty URL
lists and schemas, enum membership, integer ranges — and MUST NOT invent
constraints of its own. Both packages additionally MUST reject, before network
I/O, including on streaming methods at call time rather than first iteration:

| Argument | Rule |
| --- | --- |
| per-call `timeout`, `poll_interval` | real number greater than zero; booleans rejected |
| `last_event_id` | integer `>= 0`; booleans rejected |
| `run_id` | non-empty string |
| `idempotency_key` | non-empty string when supplied |
| `list_runs.limit` | integer 1–100, matching the public list window |
| `feature`, `state` | members of the exported feature / run-state values |
| `default_headers` | string keys and values; reserved names rejected (§3.3) |

Unknown nested `config` keys that the contract has not removed MUST still be
forwarded so future server flags can be used before an SDK release.

## 9. Cross-language parity

The two implementations MUST have equivalent observable behavior. Idiomatic
naming differences are intentional:

| Python | JavaScript |
| --- | --- |
| `base_url` | `baseUrl` |
| `execution_mode` | `executionMode` |
| `only_memoized` | `onlyMemoized` |
| `status_code` | `statusCode` |
| `request_id` | `requestId` |
| `idempotency_key` | `idempotencyKey` |
| `last_event_id` | `lastEventId` |
| `max_retries` | `maxRetries` |
| `stream_idle_timeout` | `streamIdleTimeout` |
| `extract_stream` | `extractStream` |
| `submit_extract` | `submitExtract` |
| `wait_for_run` | `waitForRun` |
| `is_terminal` | `isTerminal` |
| `run_id` | `runId` |

Two differences are deliberate and MUST NOT be "fixed":

- Python takes required operation arguments positionally (`extract(urls,
  schema, ...)`); JavaScript takes a single options object
  (`extract({ urls, schema })`). Each is the idiom of its ecosystem.
- Durations use each language's conventional unit (§3.1).

Wire JSON for workflow bodies and nested `config` keys uses the snake_case
names in §5–§6 for both languages. Response objects are passed through with
their wire keys unchanged, so `run.state` and `run.poll_after_ms` read the same
in both languages.

New operations MUST be specified once in this document with an explicit
language-to-wire mapping, then implemented and released in both packages.

The 0.2.0 additions are available in both packages and MUST remain aligned.

## 10. Acceptance cases

Generated or hand-written implementations MUST verify these public seams:

1. `base_url="http://localhost:8080/"` plus `ping()` requests exactly
   `http://localhost:8080/healthz`.
2. `api_key="test-key"` sends `Api-Key: test-key`.
3. `extract` maps to `POST /workflows/extract` with `schema` and empty
   `config` defaults.
4. `schema` maps to `POST /workflows/schema` with `url` and
   `only_memoized`.
5. `422 {"detail":"Invalid URL"}` becomes `MakraAPIError` with status 422,
   message `Invalid URL`, the full body, method, and path.
6. An empty URL list / empty schema fails without making an HTTP request.
7. Missing API-key configuration still sends the documented dummy key.
8. Explicit configuration overrides environment variables.
9. A submission that fails twice with `503` succeeds on the third attempt, and
   all three requests carry the same `Idempotency-Key`.
10. A `409` with code `idempotency_key_reuse` is not retried.
11. A streaming submission yields each event once and stops after the terminal
    event.
12. A stream that drops mid-run resumes with `GET /workflows/runs/{id}/events`
    and `Last-Event-ID` set to the last delivered sequence.
13. A stream that never terminates within the retry budget raises
    `MakraStreamError` carrying the run id.
14. `303` result retrieval fetches the `Location` target **without** the
    `Api-Key` header.
15. A caller-supplied cancellation signal propagates unchanged and is not
    reported as a timeout.

Tests SHOULD observe requests through a local isolated HTTP fixture or a public
transport seam and MUST NOT depend on the production service.

## 11. Repository layout and playground

Both packages are organised around the same seven concerns, one module each, so
a change to the HTTP surface has exactly one home in either language.

```text
sdk/
  SPEC.md
  python/
    pyproject.toml
    src/makra/
      __init__.py     public surface
      _constants.py   URLs, headers, enums, defaults
      _iso3166.py     ISO 3166-1 alpha-2 country codes
      _types.py       request and response TypedDicts
      _options.py     BaseOptions, ExtractOptions, SchemaOptions, ProxyRegion
      _config.py      settings resolution
      _errors.py      error hierarchy and HTTP mapping
      _requests.py    validation and payload building
      _retry.py       retryable statuses and backoff
      _response.py    body decoding
      _sse.py         SSE framing
      _events.py      WorkflowEvent
      _runs.py        run handles
      _client.py      Makra / AsyncMakra
    tests/
  javascript/
    package.json
    src/
      index.js        public surface
      index.d.ts      TypeScript declarations
      constants.js    URLs, headers, enums, defaults
      iso3166.js      ISO 3166-1 alpha-2 country codes
      config.js       settings resolution
      errors.js       error hierarchy and HTTP mapping
      requests.js     validation and payload building
      retry.js        retryable statuses and backoff
      response.js     body decoding and deadlines
      sse.js          SSE framing
      events.js       WorkflowEvent
      runs.js         run handles
      client.js       Makra
    test/
playground/
  python.py
  node.mjs
  README.md
```

Neither package may take a runtime dependency beyond `httpx` (Python) and the
platform `fetch` (JavaScript).

Playground scripts MUST default to `http://localhost:8080`, MUST send a dummy
key unless `MAKRA_API_KEY` is set, and MUST allow `MAKRA_BASE_URL` to override
the development URL. They are examples, not registry package contents.

## 12. Release requirements

Before publishing either package:

- all acceptance cases pass in both languages;
- package archives contain source, types, README, and license only as intended;
- no secret or real API key is committed;
- versions match between PyPI and npm packages;
- examples run against a user-selected server;
- the changelog/spec records any public breaking change.

Publishing credentials and automated release workflows are intentionally not
part of this version.
