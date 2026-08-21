# Makra Python SDK: reading guide

This report series explains version `0.2.0` of the `makra` Python package only. It is based on the implementation in `sdk/python/src/makra`, its test suite, README, and the SDK contract in `sdk/SPEC.md`.

Makra is a typed HTTP client for turning web pages into structured data. It does not scrape a page locally or define a custom response model. Instead, it sends a requested target shape to the Makra API, returns the successful response body without unwrapping it, and offers tools to observe and recover long-running work.

## Start here

Read the reports in this order:

1. [Tutorial: your first extraction](112137-python-sdk-tutorial.md) to see the smallest useful program.
2. [How-to guide: choose and operate workflow modes](112137-python-sdk-workflows.md) to pick blocking, streaming, or deferred runs.
3. [Reference: client, operations, and configuration](112137-python-sdk-reference.md) for every public option, configuration key, type, and state.
4. [Explanation: results, reliability, and errors](112137-python-sdk-reliability.md) for the behavior that matters in a production integration.

## Mental model

```text
Your Python application
        |
        |  Makra / AsyncMakra
        v
Makra public API
   |                    |
   | workflow response  | run APIs
   v                    v
blocking result     run metadata, SSE progress, stored result
```

The SDK has two workflows:

| Workflow | What it is for | Primary call |
| --- | --- | --- |
| Extraction | Obtain data from one or more URLs in a shape you describe | `extract(urls, schema, ...)` |
| Schema discovery | Ask Makra to generate/reconstruct a page schema for one URL | `schema(url, ...)` |

Each workflow has three response modes:

| Mode | Methods | Best fit |
| --- | --- | --- |
| Blocking | `extract`, `schema` | A short server-side job where the caller can wait. |
| Streaming | `extract_stream`, `schema_stream` | A CLI or UI that needs lifecycle and progress updates. |
| Deferred | `submit_extract`, `submit_schema` | A worker, webhook-style architecture, or any job that may outlive the caller. |

All three submit the same logical workflow. They differ only in how the client receives it back. Streaming events are progress notifications, not extracted data. Deferred jobs return a `RunHandle`; a run ID is sufficient to resume the same work in another process.

## Install and select a client

The package requires Python 3.9+ and has one runtime dependency, `httpx`.

```bash
pip install makra
```

Use `Makra` in synchronous programs such as scripts, command-line tools, and conventional web request handlers. Use `AsyncMakra` in an existing `asyncio` application. Their operation names, keyword arguments, validation, response handling, and error hierarchy are intentionally equivalent. The async equivalents are awaited; streams use `async for`; the client uses `async with`.

```python
from makra import Makra

with Makra(api_key="your-api-key") as client:
    print(client.ping())
```

The sync client owns an HTTP connection pool. Create one client per application or service lifetime and close it, preferably with `with`. Do not create a new client for every URL. `AsyncMakra` follows the same rule with `async with`.

## What the SDK deliberately does not do

The 0.2 SDK does not support natural-language query extraction, request-level actions, provider configuration, telemetry processing, or API-key issuance. It also does not turn a successful `{ "success": true, "data": ... }` envelope into `data`; inspect the full response your API returns. This preserves response metadata and avoids coupling the client to server-internal models. Response aliases such as `ExtractResponse` describe that returned value; they do not wrap it.

## Public building blocks

- `Makra` and `AsyncMakra`: synchronous and asynchronous clients.
- `RunHandle` and `AsyncRunHandle`: convenience wrappers around a deferred run ID.
- `WorkflowEvent`: an SSE progress/lifecycle event.
- `ClientConfig` and `resolve_config`: the resolved client settings and resolution helper.
- Constants such as `ExecutionModes`, `ValidationModes`, `RunStates`, `EventTypes`, `StreamDetailTypes`, `ProxyRegionScopes`, `ProxyContinents`, and `Iso3166Alpha2`: named values that avoid fragile string literals.
- `ExtractOptions`, `SchemaOptions`, and `ProxyRegion`: optional builders for workflow config that convert to the same nested dictionaries the API accepts.
- `run_is_terminal` and `run_succeeded`: helpers for interpreting a run mapping.
- `MakraError` and subclasses: predictable exception types for API, connection, stream, result-retrieval, and terminal-run failures.

## Source notes

The current package version is `0.2.0`; its production default URL is `https://api.makralabs.org`. The local development constant is `http://localhost:8080`. When no key is configured, the SDK sends the documented development fallback key `makra-development-key`; it is not a credential and production applications should always provide a real API key.
