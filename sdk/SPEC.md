# Makra SDK Specification

Status: **Normative draft for SDK version 0.1.0**

This document is the language-neutral source of truth for generating and
maintaining the official `makra` packages for Python (PyPI) and JavaScript
(npm). The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.
Where this document and an implementation disagree, this document wins.

## 1. Goals and scope

The SDK provides a small, typed client for the public Makra HTTP API. Version
0.1 covers:

- API connectivity checks;
- structured extraction;
- preprocessing;
- page-schema generation;
- formatting a page as Markdown;
- production/development configuration;
- bearer authentication ready for API-key enforcement;
- consistent HTTP and transport errors.

The SDK is a transport wrapper. It MUST NOT reinterpret successful response
payloads, hide Makra response metadata, or couple users to server-internal
Python models.

Streaming extraction, automatic retries, pagination orchestration, browser
configuration, provider configuration, telemetry processing, and API-key
issuance are outside version 0.1. These require a future spec revision.

## 2. Packages and runtime support

| Ecosystem | Registry name | Source directory | Minimum runtime |
| --- | --- | --- | --- |
| Python | `makra` | `sdk/python` | Python 3.9 |
| JavaScript | `makra` | `sdk/javascript` | Node.js 18, ESM |

Both packages MUST use semantic versioning and MUST have the same public SDK
version. The initial version is `0.1.0`.

Python MUST ship a `py.typed` marker and type hints. JavaScript MUST ship an
ESM entry point and TypeScript declarations even though the implementation is
JavaScript.

## 3. Configuration

### 3.1 Defaults

| Setting | Default |
| --- | --- |
| Production base URL | `https://api.makralabs.org` |
| Development base URL constant | `http://localhost:6900` |
| API version | `v1` |
| API key fallback | `makra-development-key` |
| Request timeout | Python: 120 seconds; JavaScript: 120,000 milliseconds |

The production URL MUST be the default. Development scripts MUST explicitly
select the development URL.

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

- `MAKRA_API_KEY`
- `MAKRA_BASE_URL`

An explicit empty API key is treated as absent and falls through to the
environment/default. A base URL MUST be an absolute `http://` or `https://`
URL. Trailing slashes MUST be removed before path construction. An API version
MUST tolerate surrounding slashes but MUST NOT be empty after normalization.

### 3.3 Authentication and common headers

Every request, including development requests and `ping`, MUST send:

```http
Authorization: Bearer <api-key>
Content-Type: application/json
Accept: application/json, text/plain, text/markdown
```

Each implementation SHOULD also send a language-specific user agent containing
the SDK version. API keys MUST NOT appear in exception messages or logs.

## 4. Public clients

### 4.1 Python

The package MUST export:

- `Makra`: synchronous client;
- `AsyncMakra`: asynchronous client with the same operations;
- `MakraError`, `MakraAPIError`, and `MakraConnectionError`;
- `PRODUCTION_BASE_URL`, `DEVELOPMENT_BASE_URL`, and `DUMMY_API_KEY`.

Constructor:

```python
Makra(
    api_key: str | None = None,
    *,
    base_url: str | None = None,
    api_version: str = "v1",
    timeout: float = 120.0,
)
```

`Makra` MUST support `with` and `close()`. `AsyncMakra` MUST support
`async with` and `await close()`. Closing a client releases its HTTP resources.

Python public operation names and arguments use `snake_case`. Operation
responses are decoded JSON values, strings, or `None`, typed as `Any` until
stable response schemas are specified.

### 4.2 JavaScript

The package MUST export:

- `Makra`;
- `MakraError`, `MakraAPIError`, and `MakraConnectionError`;
- `PRODUCTION_BASE_URL`, `DEVELOPMENT_BASE_URL`, and `DUMMY_API_KEY`;
- declarations for all public options and JSON values.

Constructor:

```js
new Makra({
  apiKey,
  baseUrl,
  apiVersion = "v1",
  timeout = 120_000,
} = {})
```

JavaScript public operation names and arguments use `camelCase`. Every
operation returns a `Promise`. No close method is required because the standard
`fetch` transport owns no per-client resource.

## 5. Operation contract

This section defines the public signature, HTTP request, and wire-name mapping.
No implementation may add, omit, or rename wire fields without updating this
spec.

### 5.1 `ping`

Checks whether the Makra service is reachable.

| Item | Value |
| --- | --- |
| Method/path | `GET /ping` |
| Request body | none |
| Python | `ping()` |
| JavaScript | `ping()` |
| Typical response | `{"message": "pong"}` |

`ping` deliberately uses the unversioned service route.

### 5.2 `extract`

Extracts structured information from one or more pages.

| Item | Python | JavaScript | Wire field |
| --- | --- | --- | --- |
| URLs, required | `urls` | `urls` | `urls` |
| Schema, required | `output_schema` | `outputSchema` | `output_schema` |
| Actions, optional | `actions` | `actions` | `actions` |
| Config, optional | `config` | `config` | `config` |

HTTP request:

```http
POST /api/{api_version}/extract
```

```json
{
  "urls": ["https://example.com"],
  "output_schema": {"title": "The page title"},
  "actions": [],
  "config": {}
}
```

`urls` MUST contain at least one non-empty string. `output_schema` MUST be a
non-empty JSON object or array. Omitted `actions` and `config` MUST be sent as
`[]` and `{}` respectively. Supported server actions currently include
`navigation` and `pagination`; clients MUST pass action strings through so the
server remains authoritative.

Python signature:

```python
extract(urls, output_schema, *, actions=None, config=None)
```

JavaScript signature:

```js
extract({ urls, outputSchema, actions = [], config = {} })
```

### 5.3 `preprocess`

Preprocesses and annotates pages for later extraction.

HTTP request:

```http
POST /api/{api_version}/preprocess
```

```json
{
  "urls": ["https://example.com"],
  "options": {}
}
```

`urls` follows the common URL validation rule. Omitted `options` MUST be sent
as `{}`.

Python: `preprocess(urls, *, options=None)`

JavaScript: `preprocess({ urls, options = {} })`

### 5.4 `page_schema` / `pageSchema`

Builds Makra's page schema for one or more pages.

HTTP request:

```http
POST /api/{api_version}/page-schema
```

| Python | JavaScript | Wire field | Default |
| --- | --- | --- | --- |
| `urls` | `urls` | `urls` | required |
| `output_type` | `outputType` | `output_type` | `"json"` |
| `debug_mode` | `debugMode` | `debug_mode` | `false` |
| `debug_output_type` | `debugOutputType` | `debug_output_type` | `"text"` |

`output_type`/`outputType` MUST be `json` or `text`. JSON output is decoded;
text output is returned as a string.

### 5.5 `format_markdown` / `formatMarkdown`

Formats one page as Markdown using the stable v0 formatter route.

| Item | Value |
| --- | --- |
| Method/path | `POST /api/v0/format-markdown` |
| Body | `{"url": "<non-empty URL string>"}` |
| Python | `format_markdown(url) -> str` |
| JavaScript | `formatMarkdown(url) -> Promise<string>` |

This endpoint is explicitly pinned to `v0`; changing the client's configured
API version MUST NOT change its path. A successful non-text response is a
transport-contract error.

## 6. Response decoding

Clients MUST preserve the complete successful server response.

1. HTTP 204 or an empty response body returns Python `None` / JavaScript
   `undefined`.
2. A response whose `Content-Type` contains `json` is parsed as JSON.
3. A non-JSON response is returned as text.
4. If a response claims JSON but cannot be parsed, its text body is returned.
5. Any HTTP status from 400 through 599 raises/rejects `MakraAPIError`, even
   when the JSON body has a `success` field.

Version 0.1 does not unwrap a `{ success, data, ... }` envelope.

## 7. Errors

### 7.1 Hierarchy

`MakraError` is the base SDK error.

`MakraAPIError` represents an HTTP error response and MUST expose:

| Concept | Python | JavaScript |
| --- | --- | --- |
| HTTP status | `status_code` | `statusCode` |
| decoded response | `body` | `body` |
| request method | `method` | `method` |
| request path | `path` | `path` |
| optional request ID | `request_id` | `requestId` |
| readable message | `message` | `message` |

The message MUST select the first non-empty string from JSON fields `message`,
`detail`, and `error`; then a non-empty text body; then
`Makra API returned HTTP <status>`.

`MakraConnectionError` represents DNS, connection, timeout, abort, or response
contract failures. It MUST expose the request method and path when known, and
MUST retain the original exception as the Python exception cause or JavaScript
`cause`.

### 7.2 Client validation

Invalid constructor or operation arguments MUST fail before network I/O.
Python uses `ValueError`; JavaScript uses `TypeError` (surfaced as a rejected
operation Promise). Validation errors are not `MakraAPIError`.

## 8. Cross-language parity

The two implementations MUST have equivalent observable behavior. Idiomatic
naming differences are intentional:

| Python | JavaScript |
| --- | --- |
| `base_url` | `baseUrl` |
| `api_version` | `apiVersion` |
| `output_schema` | `outputSchema` |
| `page_schema` | `pageSchema` |
| `format_markdown` | `formatMarkdown` |
| `status_code` | `statusCode` |
| `request_id` | `requestId` |

New operations MUST be specified once in this document with an explicit
language-to-wire mapping, then implemented and released in both packages.

## 9. Acceptance cases

Generated or hand-written implementations MUST verify these public seams:

1. `base_url="http://localhost:6900/"` plus `ping()` requests exactly
   `http://localhost:6900/ping`.
2. `api_key="test-key"` sends `Authorization: Bearer test-key`.
3. `extract` maps idiomatic schema names to `output_schema` and supplies empty
   defaults.
4. Markdown content with `text/markdown` is returned unchanged as text.
5. `422 {"detail":"Invalid URL"}` becomes `MakraAPIError` with status 422,
   message `Invalid URL`, the full body, method, and path.
6. An empty URL list fails without making an HTTP request.
7. Missing API-key configuration still sends the documented dummy key.
8. Explicit configuration overrides environment variables.

Tests SHOULD observe requests through a local isolated HTTP fixture or a public
transport seam and MUST NOT depend on the production service.

## 10. Repository layout and playground

```text
sdk/
  SPEC.md
  python/
    pyproject.toml
    src/makra/
    tests/
  javascript/
    package.json
    src/
    test/
playground/
  python.py
  node.mjs
  README.md
```

Playground scripts MUST default to `http://localhost:6900`, MUST send a dummy
key unless `MAKRA_API_KEY` is set, and MUST allow `MAKRA_BASE_URL` to override
the development URL. They are examples, not registry package contents.

## 11. Release requirements

Before publishing either package:

- all acceptance cases pass in both languages;
- package archives contain source, types, README, and license only as intended;
- no secret or real API key is committed;
- versions match between PyPI and npm packages;
- examples run against a user-selected server;
- the changelog/spec records any public breaking change.

Publishing credentials and automated release workflows are intentionally not
part of this version.
