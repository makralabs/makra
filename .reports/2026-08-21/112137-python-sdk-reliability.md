# Explanation: results, reliability, and errors in the Makra Python SDK

The [reference](112137-python-sdk-reference.md) names every control. This report explains why the SDK behaves the way it does and how to design a production integration around it.

## Results are separate from workflow progress

A workflow can take much longer than an ordinary HTTP request. Makra therefore distinguishes the answer from its lifecycle:

```text
submit / stream workflow
          |
          +--> progress events or 202 admission
                         |
                         v
                   terminal run state
                         |
                         v
                 GET /runs/{id}/result
                         |
                         v
                  stored result payload
```

Blocking mode is the exception: its request stays open and returns the workflow response directly. Streaming mode reports lifecycle details. It may include partial-result events, but it must not be treated as the authoritative result channel. Deferred mode gives the client an admission object, then requires a run query or stored-result retrieval.

This split makes a user interface more honest: it can report progress and survive reconnects without pretending the final data is already complete. It also lets a worker submit work, persist the run ID, and finish it later from a different machine.

## How to handle terminal outcomes

There are two different meanings of failure:

1. **SDK/infrastructure failure.** A request could not connect, timed out, returned a 4xx/5xx API error, or a progress stream could not resume. The SDK raises an exception.
2. **Workflow outcome.** A run reaches a terminal state. `failed`, `cancelled`, and `budget_exhausted` are non-completed terminal states. `wait_for_run` raises `MakraRunFailedError` for them by default, but you can set `raise_on_failure=False` and record the returned `RunView`. A `completed` run with `success: false` is returned because it is a domain-level outcome, not an SDK transport failure.

Recommended pattern for a background worker:

```python
from makra import Makra, MakraRunFailedError

with Makra() as client:
    try:
        run = client.wait_for_run("stored-run-id", timeout=900)
    except MakraRunFailedError as error:
        # Persist error.state and error.run.get("terminal_reason").
        print(error.state, error.run.get("terminal_reason"))
    else:
        # Still inspect run.get("success"), or use run_succeeded(run), if your product needs domain success.
        result = client.get_run_result(run["id"])
```

## Idempotency prevents duplicate billable work

Every workflow submission has an `Idempotency-Key`. If you do not pass one, the SDK creates a fresh `makra-sdk-<uuid>` key. Its HTTP retries reuse that same key, so the gateway can replay the original job instead of starting a second one.

Pass your own stable key when *your application* may retry after a restart or timeout:

```python
request_key = "import-2026-08-21-product-page-42"

with Makra() as client:
    run = client.submit_extract(
        ["https://example.com/products/42"],
        {"name": "Name", "price": "Price"},
        idempotency_key=request_key,
    )
```

Use one key for one logical submission and retain it with your own job record. Do not reuse a key for a different request body: the API can return the non-retryable `idempotency_key_reuse` conflict.

## Retries, deadlines, and stream resumption

The SDK retries transport failures and HTTP `408`, `409`, `425`, `429`, `500`, `502`, `503`, and `504` up to `max_retries` (two by default). It does not retry a `409` whose structured code is `idempotency_key_reuse` or `run_not_terminal`. Delay comes from `Retry-After` when supplied; otherwise it uses exponential backoff with jitter, capped at eight seconds. Jitter spreads many clients out after a shared outage.

There are three time concepts:

| Control | Default | What it limits |
| --- | --- | --- |
| `connect_timeout` | 10 seconds | Establishing an HTTP connection. |
| `timeout` | 300 seconds | A normal request or blocking workflow deadline. |
| `stream_idle_timeout` | 90 seconds | Silence between stream events, not total workflow duration. |

The gateway is expected to send a heartbeat every 15 seconds, so a 90-second silent gap is treated as a dropped stream. Once it knows the run ID, the SDK reconnects by `GET`ting that run's event endpoint with `Last-Event-ID` equal to the highest delivered event sequence. It never repeats the original workflow POST. Each successfully delivered event resets the reconnect budget.

For blocking extraction, the default timeout is a per-origin-page budget. With `pagination.enabled=True` and `additional_pages=2`, a 300-second base becomes 900 seconds. With sequential processing of two URLs it becomes 1,800 seconds. Concurrent URLs share wall-clock time and do not multiply the default. Supplying `timeout=` explicitly always wins.

## Why result redirects are handled specially

The result endpoint can return a redirect to a short-lived object-storage URL. The SDK turns off automatic redirect following on its authenticated client, then downloads the redirect target using a new anonymous `httpx` client. This prevents `Api-Key` from being sent to an external storage host. A redirect without `Location`, or with a location that is not an absolute HTTP(S) URL, raises `MakraResultError`. That class currently subclasses `MakraStreamError` so existing stream catches still work. Exception text never includes a presigned query string.

The trade-off is a small extra request and a distinct error path. The security benefit is that an API credential cannot leak through redirect header forwarding.

## Error hierarchy and handling strategy

```text
MakraError
├── MakraAPIError              HTTP response reached the API
│   ├── MakraAuthenticationError       401
│   ├── MakraInsufficientCreditsError  402
│   ├── MakraPermissionError           403
│   ├── MakraNotFoundError             404
│   ├── MakraInvalidRequestError       other 4xx
│   ├── MakraRateLimitError            429 / concurrency code
│   └── MakraServerError               5xx
├── MakraConnectionError       request did not reach the API
│   └── MakraTimeoutError
├── MakraStreamError           stream ended before terminal completion
│   └── MakraResultError       result redirect/download contract failure
└── MakraRunFailedError        terminal run was not completed
```

Catch a leaf when your application has a specific recovery action. Catch `MakraError` at a service boundary for consistent logging and user-facing error conversion.

```python
from makra import (
    Makra,
    MakraError,
    MakraInsufficientCreditsError,
    MakraInvalidRequestError,
    MakraRateLimitError,
)

try:
    with Makra() as client:
        result = client.extract(["https://example.com"], {"title": "Title"})
except MakraInsufficientCreditsError as error:
    print("Needed:", error.required_credits, "available:", error.available_credits)
except MakraRateLimitError as error:
    print("Retry after:", error.retry_after, "concurrency:", error.concurrency)
except MakraInvalidRequestError as error:
    print("Bad field:", error.field, "reason:", error.reason, "index:", error.index)
except MakraError as error:
    print(type(error).__name__, str(error))
```

`MakraAPIError` exposes `status_code`, `body`, `method`, `path`, `code`, `request_id`, and `message`. Keep `request_id` in support logs. The SDK selects a useful message from structured `error.message`, then top-level `message`/`detail`/`error`, then raw text, without including API keys in its messages.

## Practical production checklist

- Create and reuse one `Makra` or `AsyncMakra` per application lifetime.
- Supply `MAKRA_API_KEY` through your deployment secret mechanism, not source code.
- Persist your own job ID, Makra run ID, and application idempotency key for deferred work.
- Choose streaming for live experience, deferred mode for durability, and blocking only where a long-held connection is acceptable.
- Record terminal `state`, `terminal_reason`, `request_id`, and API error `code` in operational logs.
- Handle `result` as the final data source, including after a streamed terminal event.
- Use `raise_on_failure=False` in reconciliation systems that must classify every final state themselves.
