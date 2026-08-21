# How to choose and operate a Makra workflow

This guide helps you select a response mode and safely handle its result. The [reference](112137-python-sdk-reference.md) contains every method and configuration option.

## Choose the response mode

| If you need... | Use | Result handling |
| --- | --- | --- |
| The answer in this request and the job is short | Blocking | The method returns the successful API response body. |
| A progress bar, logs, or run-stage notifications | Streaming | Iterate events; after a terminal event, retrieve the stored result by `run_id`. |
| A durable job that can outlive this process | Deferred | Submit a job, retain its `RunHandle.id`, then wait, stream, cancel, or fetch the result later. |

## How to make a blocking request

Blocking `extract` and `schema` hold the HTTP connection until the workflow completes:

```python
from makra import Makra, ValidationModes

with Makra(timeout=120) as client:
    result = client.extract(
        ["https://example.com/products"],
        {"products": [{"name": "Name", "price": "Price"}]},
        config={"validation_mode": ValidationModes.REPAIR},
    )

print(result)
```

The `timeout` keyword on `extract` and `schema` overrides that individual workflow's deadline. If omitted, the client's timeout is a per-origin-page budget. It scales automatically for enabled pagination and for sequential multi-URL extraction; an explicit timeout does not scale.

## How to stream live progress and then retrieve data

The stream is server-sent events (SSE). It reports lifecycle and progress, not the extracted payload. Save `run_id` from an event, handle the terminal event, then call `get_run_result`.

```python
from makra import EventTypes, Makra, StreamDetailTypes

run_id = None
with Makra() as client:
    for event in client.extract_stream(
        ["https://example.com/products"],
        {"products": [{"name": "Name", "price": "Price"}]},
    ):
        run_id = event.run_id
        print(event.sequence, event.type, event.detail_type)

        if event.detail_type == StreamDetailTypes.RUN_TITLE_GENERATED:
            print("Run title:", event.payload.get("title"))

        if event.type == EventTypes.RUN_COMPLETED:
            print("Workflow domain success:", event.success)
        elif event.is_terminal:
            print("Workflow stopped:", event.status, event.reason)

    if run_id is None:
        raise RuntimeError("The stream did not identify a run")
    result = client.get_run_result(run_id)

print(result)
```

The SDK reconnects a broken stream to the run event endpoint, sending `Last-Event-ID` for the last delivered sequence. It does not submit the workflow again. If it cannot discover a run ID or reconnection exhausts `max_retries`, it raises `MakraStreamError` with `run_id` where known.

For async programs, use `async for event in client.extract_stream(...)` inside `async with AsyncMakra()`; result retrieval is `await client.get_run_result(run_id)`.

## How to submit a durable job

Deferred submission asks the API to accept work and responds with a handle right away:

```python
from makra import Makra

with Makra() as client:
    run = client.submit_extract(
        ["https://example.com/products"],
        {"products": [{"name": "Name", "price": "Price"}]},
    )
    print(run.id, run.state, run.status_url)

    terminal_run = run.wait()
    result = run.result()

print(terminal_run)
print(result)
```

Persist `run.id`, not the Python handle. Another process can resume with client-level APIs:

```python
with Makra() as client:
    run = client.wait_for_run("run-id-from-your-database")
    result = client.get_run_result("run-id-from-your-database")
```

`RunHandle` exposes `refresh()`, `wait()`, `stream()`, `result()`, and `cancel()`. Its async counterpart exposes the same operations, with awaits where an HTTP call occurs.

## How to wait without treating a failed run as an exception

By default, `wait_for_run` raises `MakraRunFailedError` when a terminal state is `failed`, `cancelled`, or `budget_exhausted`. For a reconciliation job that needs to record every terminal outcome, opt out:

```python
with Makra() as client:
    run = client.wait_for_run(
        "run-id-from-your-database",
        timeout=600,
        poll_interval=2,
        raise_on_failure=False,
    )

if run.get("state") == "completed":
    result = client.get_run_result(run["id"])
else:
    print("Terminal state:", run.get("state"), run.get("terminal_reason"))
```

The same distinction is available as helpers:

```python
from makra import run_is_terminal, run_succeeded

if run_is_terminal(run) and run_succeeded(run):
    result = client.get_run_result(run["id"])
```

Polling honours the server's `poll_after_ms` as a lower bound. The client uses two seconds when you do not provide `poll_interval`. A `completed` run whose payload says `success: false` is returned, not raised: that is a workflow/domain outcome rather than a transport failure.

## How to inspect, list, and cancel runs

```python
from makra import Features, Makra, RunStates

with Makra() as client:
    page = client.list_runs(
        limit=20,
        feature=Features.EXTRACT,
        state=RunStates.RUNNING,
    )
    for run in page.get("items", []):
        print(run["id"], run["state"], run.get("progress"))

    cancelled = client.cancel_run("run-id-to-stop")
    print(cancelled["state"])
```

`list_runs` accepts `limit`, `cursor`, `feature`, and `state`; use the returned `next_cursor` for the next page when present. Cancellation is safe to request more than once; a terminal run is returned as-is.

## Troubleshooting mode selection

- Use blocking mode for a request/response integration only if its timeout can cover the job.
- Use streaming mode for user-facing progress, but retain the run ID so the result can be fetched after a browser or network interruption.
- Use deferred mode for batch work, queues, scheduled jobs, and any process that may terminate before the workflow does.
- Never parse extracted data from SSE events. Retrieve the stored result after a terminal event.
