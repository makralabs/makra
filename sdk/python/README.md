# Makra Python SDK

The official Python client for the Makra web extraction API.

## Install

```bash
pip install makra
```

For local development from this repository:

```bash
pip install -e sdk/python
```

## Quick start

```python
from makra import Makra

with Makra(api_key="mk_live_...") as client:
    result = client.extract(
        urls=["https://example.com"],
        schema={"title": "The page title"},
    )
    print(result)
```

Every operation exists in two flavours: `Makra` (synchronous) and `AsyncMakra`
(awaitable). The examples below use the synchronous client; the async one is
identical with `await` and `async with`.

## Three ways to run a workflow

Pick by how long the work takes and how much you want to watch it happen.

| Mode | Use when | Method |
| --- | --- | --- |
| REST | The run is short and you just want the answer | `extract` / `schema` |
| Streaming | You want live progress, e.g. to drive a UI | `extract_stream` / `schema_stream` |
| Deferred | The run is long, or the caller cannot stay online | `submit_extract` / `submit_schema` |

### 1. REST

The connection is held until the run finishes, so `timeout` is really "how
long may this workflow take". It defaults to 300 seconds.

```python
data = client.extract(
    urls=["https://example.com/products"],
    schema={"products": [{"name": "string", "price": "number"}]},
    config={
        "validation_mode": "repair",
        "memory": {"enabled": True, "selector_chain_version": "v2"},
        "pagination": {"enabled": True, "additional_pages": 2},
    },
    timeout=120,
)
```

Discover what a page contains before you write a schema:

```python
page_schema = client.schema(
    "https://example.com/products",
    config={"crawler": {"proxy": {"region": {"scope": "country", "value": "DE"}}}},
)
```

### 2. Streaming

The stream carries lifecycle and progress events, **not** the extracted data.
When a terminal event arrives, fetch the stored result.

```python
run_id = None
for event in client.extract_stream(urls=urls, schema=schema):
    run_id = event.run_id
    print(event.sequence, event.type, event.detail_type)
    if event.is_terminal:
        print("finished:", event.status, event.reason)

data = client.get_run_result(run_id)
```

Each `WorkflowEvent` exposes `type`, `sequence`, `run_id`, the raw `payload`,
and the shortcuts `is_terminal`, `detail_type`, `status`, `reason`, `success`.

If the connection drops mid-run, the SDK reconnects to the run's event
endpoint with `Last-Event-ID`, so you see every event exactly once. Silence
longer than `stream_idle_timeout` (90s, versus the gateway's 15s heartbeat)
counts as a dropped connection.

### 3. Deferred runs

Submit now, collect later — from a different process, if you like.

```python
run = client.submit_extract(urls=urls, schema=schema)
print(run.id, run.state)          # queued

run.wait()                        # polls until terminal
data = run.result()
```

A handle also supports `refresh()`, `stream()`, and `cancel()`. Everything a
handle does is available directly on the client too — `get_run`, `list_runs`,
`wait_for_run`, `stream_run_events`, `get_run_result`, `cancel_run` — so a run
id is all you need to resume from anywhere.

```python
for event in client.stream_run_events(run_id, last_event_id=42):
    ...
```

## Configuration

Settings resolve as **explicit argument → environment variable → default**.

| Argument | Environment | Default |
| --- | --- | --- |
| `api_key` | `MAKRA_API_KEY` | `makra-development-key` |
| `base_url` | `MAKRA_BASE_URL` | `https://api.makralabs.org` |
| `timeout` | `MAKRA_TIMEOUT` (seconds) | `300` |
| `max_retries` | `MAKRA_MAX_RETRIES` | `2` |
| `connect_timeout` | — | `10` |
| `stream_idle_timeout` | — | `90` |
| `retry_backoff` | — | `0.5` |
| `default_headers` | — | `{}` |

```python
from makra import DEVELOPMENT_BASE_URL, Makra

client = Makra(base_url=DEVELOPMENT_BASE_URL, timeout=60, max_retries=4)
```

Authentication uses the `Api-Key` header. A client owns an HTTP connection
pool, so build one per application and close it when done.

### Retries and idempotency

Transient failures (408, 409, 425, 429, 5xx) are retried with exponential
backoff and full jitter, honouring `Retry-After` when the server sends it.

Retrying a submission is only safe because the SDK attaches a fresh
`Idempotency-Key` to every one: the gateway replays the original run instead of
starting a second billable one. Pass your own `idempotency_key` to make a
submission replayable across process restarts too.

## Errors

Catch `MakraError` for anything the SDK raises, or a subclass to handle one
condition.

```
MakraError
├── MakraAPIError                     .status_code .code .body .request_id
│   ├── MakraAuthenticationError      401
│   ├── MakraInsufficientCreditsError 402  .required_credits .available_credits
│   ├── MakraPermissionError          403
│   ├── MakraNotFoundError            404
│   ├── MakraInvalidRequestError      4xx  .field .reason .index
│   ├── MakraRateLimitError           429  .retry_after .concurrency
│   └── MakraServerError              5xx
├── MakraConnectionError              the request never reached the API
│   └── MakraTimeoutError
├── MakraStreamError                  .run_id
└── MakraRunFailedError               .run_id .state .run
```

Malformed arguments raise `ValueError` before any network call, so a typo in a
config key costs nothing.

```python
from makra import MakraInsufficientCreditsError, MakraRateLimitError

try:
    client.extract(urls=urls, schema=schema)
except MakraInsufficientCreditsError as error:
    print("need", error.required_credits, "have", error.available_credits)
except MakraRateLimitError as error:
    print("retry after", error.retry_after)
```

## Async

```python
import asyncio
from makra import AsyncMakra

async def main():
    async with AsyncMakra() as client:
        async for event in client.extract_stream(urls=urls, schema=schema):
            print(event.type)
        run = await client.submit_schema("https://example.com")
        await run.wait()
        print(await run.result())

asyncio.run(main())
```

See [`../SPEC.md`](../SPEC.md) for the complete contract.
