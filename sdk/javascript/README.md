# Makra JavaScript SDK

The official JavaScript client for the Makra web extraction API. ESM, no
runtime dependencies, Node 18+.

## Install

```bash
npm install makra
```

## Quick start

```js
import { Makra } from "makra";

const makra = new Makra({ apiKey: "mk_live_..." });

const result = await makra.extract({
  urls: ["https://example.com"],
  schema: { title: "The page title" },
});
```

## Three ways to run a workflow

Pick by how long the work takes and how much you want to watch it happen.

| Mode | Use when | Method |
| --- | --- | --- |
| REST | The run is short and you just want the answer | `extract` / `schema` |
| Streaming | You want live progress, e.g. to drive a UI | `extractStream` / `schemaStream` |
| Deferred | The run is long, or the caller cannot stay online | `submitExtract` / `submitSchema` |

### 1. REST

The connection is held until the run finishes, so `timeout` is really "how
long may this workflow take". It defaults to 300000 ms.

```js
const data = await makra.extract({
  urls: ["https://example.com/products"],
  schema: { products: [{ name: "string", price: "number" }] },
  config: {
    validation_mode: "repair",
    memory: { enabled: true, selector_chain_version: "v2" },
    pagination: { enabled: true, additional_pages: 2 },
  },
  timeout: 120_000,
});
```

Discover what a page contains before you write a schema:

```js
const pageSchema = await makra.schema({
  url: "https://example.com/products",
  config: { crawler: { proxy: { region: { scope: "country", value: "DE" } } } },
});
```

### 2. Streaming

The stream carries lifecycle and progress events, **not** the extracted data.
When a terminal event arrives, fetch the stored result.

```js
let runId;
for await (const event of makra.extractStream({ urls, schema })) {
  runId = event.runId;
  console.log(event.sequence, event.type, event.detailType);
  if (event.isTerminal) console.log("finished:", event.status, event.reason);
}

const data = await makra.getRunResult(runId);
```

Each `WorkflowEvent` exposes `type`, `sequence`, `runId`, the raw `payload`,
and the shortcuts `isTerminal`, `detailType`, `status`, `reason`, `success`.

If the connection drops mid-run, the SDK reconnects to the run's event
endpoint with `Last-Event-ID`, so you see every event exactly once. Silence
longer than `streamIdleTimeout` (90000 ms, versus the gateway's 15 s heartbeat)
counts as a dropped connection.

### 3. Deferred runs

Submit now, collect later — from a different process, if you like.

```js
const run = await makra.submitExtract({ urls, schema });
console.log(run.id, run.state); // queued

await run.wait();               // polls until terminal
const data = await run.result();
```

A handle also supports `refresh()`, `stream()`, and `cancel()`. Everything a
handle does is available directly on the client too — `getRun`, `listRuns`,
`waitForRun`, `streamRunEvents`, `getRunResult`, `cancelRun` — so a run id is
all you need to resume from anywhere.

```js
for await (const event of makra.streamRunEvents(runId, { lastEventId: 42 })) {
  // ...
}
```

## Configuration

Settings resolve as **explicit option → environment variable → default**.
Durations passed as options are milliseconds; `MAKRA_TIMEOUT` is in seconds
because it is shared with the other Makra SDKs.

| Option | Environment | Default |
| --- | --- | --- |
| `apiKey` | `MAKRA_API_KEY` | `makra-development-key` |
| `baseUrl` | `MAKRA_BASE_URL` | `https://api.makralabs.org` |
| `timeout` | `MAKRA_TIMEOUT` (seconds) | `300000` |
| `maxRetries` | `MAKRA_MAX_RETRIES` | `2` |
| `streamIdleTimeout` | — | `90000` |
| `retryBackoff` | — | `500` |
| `defaultHeaders` | — | `{}` |

```js
import { DEVELOPMENT_BASE_URL, Makra } from "makra";

const makra = new Makra({ baseUrl: DEVELOPMENT_BASE_URL, timeout: 60_000 });
```

Authentication uses the `Api-Key` header. Every method accepts an
`AbortSignal` through `signal`, which propagates to the underlying `fetch` and
is rethrown untouched so `AbortError` stays distinguishable from a timeout.

### Retries and idempotency

Transient failures (408, 409, 425, 429, 5xx) are retried with exponential
backoff and full jitter, honouring `Retry-After` when the server sends it.

Retrying a submission is only safe because the SDK attaches a fresh
`Idempotency-Key` to every one: the gateway replays the original run instead of
starting a second billable one. Pass your own `idempotencyKey` to make a
submission replayable across process restarts too.

## Errors

Catch `MakraError` for anything the SDK throws, or a subclass to handle one
condition.

```
MakraError
├── MakraAPIError                     .statusCode .code .body .requestId
│   ├── MakraAuthenticationError      401
│   ├── MakraInsufficientCreditsError 402  .requiredCredits .availableCredits
│   ├── MakraPermissionError          403
│   ├── MakraNotFoundError            404
│   ├── MakraInvalidRequestError      4xx  .field .reason .index
│   ├── MakraRateLimitError           429  .retryAfter .concurrency
│   └── MakraServerError              5xx
├── MakraConnectionError              the request never reached the API
│   └── MakraTimeoutError
├── MakraStreamError                  .runId
└── MakraRunFailedError               .runId .state .run
```

Malformed arguments throw `TypeError` or `RangeError` before any network call,
so a typo in a config key costs nothing.

```js
import { MakraInsufficientCreditsError, MakraRateLimitError } from "makra";

try {
  await makra.extract({ urls, schema });
} catch (error) {
  if (error instanceof MakraInsufficientCreditsError) {
    console.log("need", error.requiredCredits, "have", error.availableCredits);
  } else if (error instanceof MakraRateLimitError) {
    console.log("retry after", error.retryAfter);
  } else throw error;
}
```

## TypeScript

Hand-written declarations ship with the package; no build step or `@types`
install is required.

```ts
import { Makra, type ExtractConfig, type WorkflowEvent } from "makra";
```

See [`../SPEC.md`](../SPEC.md) for the complete contract.
