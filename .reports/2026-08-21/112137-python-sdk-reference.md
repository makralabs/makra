# Makra Python SDK reference

This is the factual reference for the Python package. Read the [tutorial](112137-python-sdk-tutorial.md) first if you are new to the package, and the [workflow guide](112137-python-sdk-workflows.md) for task-focused examples.

## Client construction and lifecycle

```python
Makra(
    api_key: str | None = None,
    *,
    base_url: str | None = None,
    timeout: float | None = None,
    connect_timeout: float | None = None,
    stream_idle_timeout: float | None = None,
    max_retries: int | None = None,
    retry_backoff: float | None = None,
    default_headers: Mapping[str, str] | None = None,
)
```

`AsyncMakra` has the same constructor. `Makra` supports `with` and `close()`; `AsyncMakra` supports `async with` and `await close()`. Read-only properties `config`, `api_key`, `base_url`, and `timeout` expose resolved settings.

Resolution order is explicit constructor argument, then environment variable, then SDK default:

| Setting | Environment | Default | Constraint |
| --- | --- | --- | --- |
| `api_key` | `MAKRA_API_KEY` | `makra-development-key` | An explicit empty key falls through to env/default. |
| `base_url` | `MAKRA_BASE_URL` | `https://api.makralabs.org` | Absolute `http` or `https` URL; trailing slash is removed. |
| `timeout` | `MAKRA_TIMEOUT` | `300.0` seconds | Must be greater than zero. |
| `connect_timeout` | — | `10.0` seconds | Must be greater than zero. |
| `stream_idle_timeout` | — | `90.0` seconds | Must be greater than zero. |
| `max_retries` | `MAKRA_MAX_RETRIES` | `2` | Must be zero or greater. |
| `retry_backoff` | — | `0.5` seconds | Must be greater than zero. |
| `default_headers` | — | `{}` | String keys and values. Reserved SDK headers are rejected. |

The client sends `Api-Key`, JSON `Content-Type`, JSON `Accept`, and a `makra-python/0.2.0` user agent on every request. Per-operation headers add idempotency, async preference, or SSE acceptance as needed. `default_headers` cannot override `Api-Key`, `Content-Type`, `Accept`, `User-Agent`, `Idempotency-Key`, `Prefer`, or `Last-Event-ID`.

## Workflow operations

| Method | Return | Purpose |
| --- | --- | --- |
| `ping()` | `HealthResponse \| ResponseBody` | `GET /healthz`; checks gateway reachability. |
| `ready()` | `HealthResponse \| ResponseBody` | `GET /healthz/ready`; also checks result storage. |
| `extract(urls, schema, *, execution_mode, config, idempotency_key, timeout)` | `ExtractResponse \| ResponseBody` | Blocking structured extraction. |
| `schema(url, *, only_memoized, config, idempotency_key, timeout)` | `SchemaResponse \| ResponseBody` | Blocking schema generation. |
| `extract_stream(...)` / `schema_stream(...)` | iterator of `WorkflowEvent` | Streaming workflow progress. |
| `submit_extract(...)` / `submit_schema(...)` | `RunHandle` | Deferred submission. |

Async variants return awaitables except stream methods, which return async iterators.

### `extract`

```python
client.extract(
    urls,
    schema,
    *,
    execution_mode="concurrent",
    config=None,
    idempotency_key=None,
    timeout=None,
)
```

`urls` must be a non-string sequence containing at least one non-empty string. `schema` must be a non-empty mapping or list. `execution_mode` is `"concurrent"` or `"sequential"`; use `ExecutionModes.CONCURRENT` or `ExecutionModes.SEQUENTIAL`. A schema is an extraction target shape, not required to be formal JSON Schema. Omitting config sends `{}`. `config` may be an `ExtractConfig` dictionary or an `ExtractOptions` instance.

### `schema`

```python
client.schema(
    url,
    *,
    only_memoized=False,
    config=None,
    idempotency_key=None,
    timeout=None,
)
```

`url` must be a non-empty string and `only_memoized` must be a boolean. Schema generation has only common configuration; `only_memoized` is a top-level request argument, not a config key. `config` may be a `SchemaConfig` dictionary or a `SchemaOptions` instance.

### Streaming and deferred signatures

`extract_stream` accepts `urls`, `schema`, `execution_mode`, `config`, and `idempotency_key`. `schema_stream` accepts `url`, `only_memoized`, `config`, and `idempotency_key`. Neither has a workflow `timeout`; a stream instead has an idle-gap timeout.

`submit_extract` and `submit_schema` accept the same arguments as their streaming equivalents. Each returns a handle with `id`, `feature`, `state`, `status_url`, `events_url`, `result_url`, and raw `admission` fields.

## Run management

| Client method | Arguments | Notes |
| --- | --- | --- |
| `get_run(run_id)` | ID | Returns run metadata, not stored data. |
| `list_runs(limit=None, cursor=None, feature=None, state=None)` | optional filters | Returns a `RunPage` with `items`, optional `next_cursor`, and optional `concurrency`. |
| `cancel_run(run_id)` | ID | Requests cancellation; idempotent. |
| `stream_run_events(run_id, last_event_id=0)` | ID, resume sequence | Attaches to a run's SSE endpoint. |
| `wait_for_run(run_id, timeout=None, poll_interval=None, raise_on_failure=True)` | ID plus policy | Polls terminal state. |
| `get_run_result(run_id)` | ID | Retrieves the stored terminal payload (`RunResult \| ResponseBody`). |

`RunView` can include: `id`, `feature`, `state`, `sequence`, `poll_after_ms`, `result_available`, `progress`, `response_mode`, `success`, usage/billing fields, timestamps, `terminal_reason`, and `result` summary metadata. The result summary can include `available`, `content_type`, `size_bytes`, `sha256`, and `href`.

Run states are `queued`, `running`, `cancel_requested`, `completed`, `failed`, `cancelled`, and `budget_exhausted`. Terminal states are `completed`, `failed`, `cancelled`, and `budget_exhausted`.

## Workflow configuration

Pass a regular nested dictionary or an `ExtractOptions` / `SchemaOptions` object. `CommonConfig`, `ExtractConfig`, and `SchemaConfig` TypedDicts are exported for type checkers. Option objects convert to those dictionaries and then take the same validation path. SDK config keys stay snake_case because they are forwarded to the API.

```python
from makra import ExtractOptions, Iso3166Alpha2, ProxyRegion, ValidationModes

config = ExtractOptions(
    validation_mode=ValidationModes.REPAIR,
    additional_pages=2,
    title_enabled=True,
    post_ready_wait_ms=1_000,
    proxy_region=ProxyRegion.country(Iso3166Alpha2.DE),
    recovery_retry=True,
    recovery_retry_delay_ms=2_000,
)
```

Shared crawler fields live on an internal `BaseOptions` base. `SchemaOptions` and `ExtractOptions` both inherit that base; `ExtractOptions` adds extract-only fields. `ExtractOptions` does not subclass `SchemaOptions`.

### Common configuration: extraction and schema

| Path | Accepted values | Behavior |
| --- | --- | --- |
| `crawler.post_ready_wait_ms` | integer or `None`, `0..120000` | Extra post-readiness wait; `None` uses deployment default. |
| `crawler.proxy.region.scope` | `worldwide`, `continent`, or `country` | Selects proxy egress scope. |
| `crawler.proxy.region.value` | `None` or string | Must be `None` for worldwide; continent slug for continent; ISO alpha-2 code for country. |
| `crawler.recovery.retry` | bool or `None` | One final fresh-session retry. Sent to API as `one_last_retry`. |
| `crawler.recovery.retry_delay_ms` | integer or `None`, `0..300000` | Delay before that retry. Sent as `one_last_retry_delay_ms`. |

Use `ProxyRegionScopes`, `ProxyContinents`, and `Iso3166Alpha2`:

```python
from makra import Iso3166Alpha2, ProxyContinents, ProxyRegionScopes

country_proxy = {
    "crawler": {"proxy": {"region": {
        "scope": ProxyRegionScopes.COUNTRY,
        "value": Iso3166Alpha2.DE,
    }}}
}
continent_proxy = {
    "crawler": {"proxy": {"region": {
        "scope": ProxyRegionScopes.CONTINENT,
        "value": ProxyContinents.EUROPE,
    }}}
}
```

Supported continent slugs are `africa`, `asia`, `europe`, `north.america`, `oceania`, and `south.america`. Country input is normalized to uppercase; continent input to lowercase. ISO code `XK` is also included for Kosovo because proxy providers commonly use it.

### Extraction-only configuration

| Path | Accepted values | Default/effect |
| --- | --- | --- |
| `validation_mode` | `observe`, `repair`, or `None` | Deployment default is repair; use `ValidationModes`. |
| `pagination.enabled` | bool | Enables following next-page controls. |
| `pagination.additional_pages` | integer `>= 0` | Number of pages after the origin page. |
| `title.enabled` | bool | Requests generation of a human-readable run title. |

Example:

```python
from makra import ValidationModes

config = {
    "validation_mode": ValidationModes.REPAIR,
    "pagination": {"enabled": True, "additional_pages": 2},
    "title": {"enabled": True},
    "crawler": {
        "post_ready_wait_ms": 1_000,
        "recovery": {"retry": True, "retry_delay_ms": 2_000},
    },
}
```

The SDK rejects malformed local arguments before network I/O: empty URLs/schemas, invalid enum values, invalid ranges, non-mapping configs, `config.memory`, `config.selector_chain_version`, extraction `config.audit`, and wire-name recovery keys in `crawler.recovery`. Per-call `timeout` and `poll_interval` must be numbers greater than zero; `last_event_id` must be an integer `>= 0`; `run_id` and supplied `idempotency_key` values must be non-empty strings; `list_runs.limit` must be 1–100; `feature` and `state` must be exported values. The service remains the authority for unrecognized keys and deployment policy.

## Event reference

`WorkflowEvent` has `type`, `sequence`, `payload`, and `run_id`. Convenience properties are `is_terminal`, `detail_type` (`payload.stream_event_type`), `status`, `reason`, and `success`.

Use `EventTypes` for event names. Terminal types: `RUN_COMPLETED`, `RUN_FAILED`, `RUN_CANCELLED`, `RUN_BUDGET_EXHAUSTED`. Other event types include run start/heartbeat, step start/progress/completion, partial results, and diagnostics. Use `StreamDetailTypes` for detailed status values such as `RUN_TITLE_GENERATED`, stage/activity/message progress, partial result, final result, and diagnostic.

## Response decoding

Success responses remain complete: an empty or `204` body becomes `None`; a JSON content type becomes parsed JSON; a non-JSON body becomes text; invalid JSON that claims to be JSON also becomes text. HTTP 4xx and 5xx responses always raise an exception rather than being returned as a success-shaped body. Static aliases (`ExtractResponse`, `SchemaResponse`, `RunResult`, `HealthResponse`) describe those decoded values; they do not unwrap `{success, data}`.
