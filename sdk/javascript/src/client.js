/**
 * The Makra API client.
 *
 * Three ways to run a workflow, sharing one transport:
 *
 * - `extract` / `schema` — blocking REST. One call in, one result out.
 * - `extractStream` / `schemaStream` — live progress events over SSE.
 * - `submitExtract` / `submitSchema` — fire and forget, returning a handle
 *   that can be polled, streamed, or cancelled later.
 */

import {
  CONTENT_TYPE_SSE,
  DEFAULT_POLL_INTERVAL_MS,
  ExecutionModes,
  HEADER_IDEMPOTENCY_KEY,
  HEADER_LAST_EVENT_ID,
  HEADER_PREFER,
  HEADER_RUN_ID,
  PATH_EXTRACT,
  PATH_HEALTH,
  PATH_READY,
  PATH_RUNS,
  PATH_SCHEMA,
  PREFER_RESPOND_ASYNC,
  RunStates,
  TERMINAL_RUN_STATES,
  runPath,
} from "./constants.js";
import { resolveConfig } from "./config.js";
import {
  MakraConnectionError,
  MakraRunFailedError,
  MakraStreamError,
  MakraTimeoutError,
} from "./errors.js";
import { parseEvent } from "./events.js";
import {
  buildExtractPayload,
  buildSchemaPayload,
  newIdempotencyKey,
  resolveWorkflowTimeout,
} from "./requests.js";
import { apiError, deadline, decodeBody, isTimeout } from "./response.js";
import { isRetryableStatus, retryDelay, sleep } from "./retry.js";
import { RunHandle } from "./runs.js";
import { SSEDecoder, readLines } from "./sse.js";

const REDIRECT_STATUS = new Set([301, 302, 303, 307, 308]);

export class Makra {
  /**
   * @param {object} [options] Explicit settings; anything omitted falls back
   *   to `MAKRA_*` environment variables and then to the SDK defaults.
   */
  constructor(options = {}) {
    this.config = resolveConfig(options);
  }

  get apiKey() {
    return this.config.apiKey;
  }

  get baseUrl() {
    return this.config.baseUrl;
  }

  // --- Health --------------------------------------------------------------

  /** Check that the API gateway is reachable. */
  async ping({ signal } = {}) {
    return this.#request("GET", PATH_HEALTH, { retryable: true, signal });
  }

  /** Check that result storage is reachable, not just the gateway. */
  async ready({ signal } = {}) {
    return this.#request("GET", PATH_READY, { retryable: true, signal });
  }

  // --- Blocking workflows --------------------------------------------------

  /**
   * Extract structured data and wait for the result.
   *
   * The connection is held until the run is terminal, so `timeout` is
   * effectively the longest a workflow may take. When omitted, the client
   * default is a per-page budget: paginated extracts and sequential
   * multi-URL extracts get a proportionally longer deadline.
   */
  async extract({
    urls,
    schema,
    executionMode = ExecutionModes.CONCURRENT,
    config,
    idempotencyKey,
    timeout,
    signal,
  }) {
    const body = buildExtractPayload({ urls, schema, executionMode, config });
    return this.#request("POST", PATH_EXTRACT, {
      body,
      headers: submitHeaders(idempotencyKey),
      retryable: true,
      timeout: this.#workflowTimeout(timeout, body),
      signal,
    });
  }

  /** Build a JSON Schema describing everything one page contains. */
  async schema({ url, onlyMemoized = false, config, idempotencyKey, timeout, signal }) {
    const body = buildSchemaPayload({ url, onlyMemoized, config });
    return this.#request("POST", PATH_SCHEMA, {
      body,
      headers: submitHeaders(idempotencyKey),
      retryable: true,
      timeout: this.#workflowTimeout(timeout, body),
      signal,
    });
  }

  // --- Streaming workflows -------------------------------------------------

  /**
   * Run an extraction and iterate its progress events as they happen.
   *
   * The stream carries lifecycle and progress events, not the payload. Read
   * `event.runId` from any event and call `getRunResult` once a terminal event
   * arrives.
   *
   * @returns {AsyncGenerator<import("./events.js").WorkflowEvent>}
   */
  extractStream({
    urls,
    schema,
    executionMode = ExecutionModes.CONCURRENT,
    config,
    idempotencyKey,
    signal,
  }) {
    const body = buildExtractPayload({
      urls,
      schema,
      executionMode,
      config,
      stream: true,
    });
    return this.#streamEvents("POST", PATH_EXTRACT, { body, idempotencyKey, signal });
  }

  /** Run schema generation and iterate its progress events. */
  schemaStream({ url, onlyMemoized = false, config, idempotencyKey, signal }) {
    const body = buildSchemaPayload({ url, onlyMemoized, config, stream: true });
    return this.#streamEvents("POST", PATH_SCHEMA, { body, idempotencyKey, signal });
  }

  /** Attach to an existing run's event stream, optionally resuming. */
  streamRunEvents(runId, { lastEventId = 0, signal } = {}) {
    return this.#streamEvents("GET", runPath(runId, "/events"), {
      runId,
      lastEventId,
      signal,
    });
  }

  // --- Deferred submission -------------------------------------------------

  /** Queue an extraction and return immediately with a run handle. */
  async submitExtract({
    urls,
    schema,
    executionMode = ExecutionModes.CONCURRENT,
    config,
    idempotencyKey,
    signal,
  }) {
    const body = buildExtractPayload({ urls, schema, executionMode, config });
    return new RunHandle(this, await this.#submit(PATH_EXTRACT, body, idempotencyKey, signal), {
      timeout: this.#workflowTimeout(undefined, body),
    });
  }

  /** Queue a schema build and return immediately with a run handle. */
  async submitSchema({ url, onlyMemoized = false, config, idempotencyKey, signal }) {
    const body = buildSchemaPayload({ url, onlyMemoized, config });
    return new RunHandle(this, await this.#submit(PATH_SCHEMA, body, idempotencyKey, signal), {
      timeout: this.#workflowTimeout(undefined, body),
    });
  }

  // --- Run management ------------------------------------------------------

  /** Fetch run metadata. Never the result payload. */
  async getRun(runId, { signal } = {}) {
    return this.#request("GET", runPath(runId), { retryable: true, signal });
  }

  /** List the caller's non-archived runs, newest first. */
  async listRuns({ limit, cursor, feature, state, signal } = {}) {
    return this.#request("GET", PATH_RUNS, {
      params: { limit, cursor, feature, state },
      retryable: true,
      signal,
    });
  }

  /** Request cancellation of a run. Safe to call more than once. */
  async cancelRun(runId, { signal } = {}) {
    return this.#request("POST", runPath(runId, "/cancel"), {
      retryable: true,
      signal,
    });
  }

  /**
   * Poll until the run is terminal.
   *
   * A `completed` run whose payload reports `success: false` is a domain
   * failure, not an infrastructure one, so it is returned rather than thrown.
   */
  async waitForRun(
    runId,
    { timeout, pollInterval, throwOnFailure = true, signal } = {},
  ) {
    const expiresAt = Date.now() + (timeout ?? this.config.timeout);
    for (;;) {
      const run = await this.getRun(runId, { signal });
      if (TERMINAL_RUN_STATES.has(run?.state)) {
        if (throwOnFailure && run.state !== RunStates.COMPLETED) {
          throw new MakraRunFailedError(
            `Workflow run ${runId} ended in state '${run.state}': ${
              run.terminal_reason ?? "no reason reported"
            }`,
            { runId, state: run.state, run },
          );
        }
        return run;
      }
      const delay = nextPollDelay(run, pollInterval);
      if (Date.now() + delay > expiresAt) {
        throw new MakraTimeoutError(`Workflow run ${runId} did not finish in time`, {
          method: "GET",
          path: runPath(runId),
        });
      }
      await sleep(delay);
    }
  }

  /** Download a terminal run's stored result payload. */
  async getRunResult(runId, { signal } = {}) {
    const path = runPath(runId, "/result");
    const response = await this.#send("GET", path, { retryable: true, signal });
    if (REDIRECT_STATUS.has(response.status)) {
      return this.#downloadRedirect(response, path, signal);
    }
    return decodeBody(response);
  }

  // --- Internals -----------------------------------------------------------

  async #submit(path, body, idempotencyKey, signal) {
    const admission = await this.#request("POST", path, {
      body,
      headers: { ...submitHeaders(idempotencyKey), [HEADER_PREFER]: PREFER_RESPOND_ASYNC },
      retryable: true,
      signal,
    });
    return admission ?? {};
  }

  async #request(method, path, options) {
    return decodeBody(await this.#send(method, path, options));
  }

  /**
   * Perform one request, retrying transient failures.
   *
   * Retries are only attempted for callers that opted in, and only for status
   * codes the API marks as transient — a rejected request is never replayed in
   * the hope of a different answer.
   */
  async #send(method, path, { body, params, headers, timeout, retryable, signal } = {}) {
    const url = this.config.url(path) + queryString(params);
    let attempt = 0;
    for (;;) {
      let error;
      const clock = deadline(timeout ?? this.config.timeout, signal);
      try {
        const response = await fetch(url, {
          method,
          headers: { ...this.config.headers(), ...headers },
          body: body === undefined ? undefined : JSON.stringify(body),
          signal: clock.signal,
          redirect: "manual",
        });
        if (response.status < 400) return response;
        error = await apiError(response, method, path);
        if (!isRetryableStatus(response.status, error.code)) throw error;
      } catch (cause) {
        // Either the API error we just decided not to retry, or the caller
        // cancelling; both propagate untouched. Anything else is transport.
        if (cause === error || signal?.aborted) throw cause;
        error = this.#connectionError(cause, method, path);
      } finally {
        clock.clear();
      }

      attempt += 1;
      if (!retryable || attempt > this.config.maxRetries) throw error;
      await sleep(
        retryDelay(attempt, {
          backoff: this.config.retryBackoff,
          retryAfter: error.retryAfter,
        }),
      );
    }
  }

  #workflowTimeout(timeout, body) {
    return resolveWorkflowTimeout(timeout, this.config.timeout, {
      config: body?.config,
      urlCount: Array.isArray(body?.urls) ? body.urls.length : 1,
      executionMode: body?.execution_mode ?? ExecutionModes.CONCURRENT,
    });
  }

  #connectionError(cause, method, path) {
    if (isTimeout(cause)) {
      return new MakraTimeoutError(`Request to the Makra API timed out: ${path}`, {
        method,
        path,
        cause,
      });
    }
    return new MakraConnectionError(
      `Could not connect to the Makra API: ${cause?.message ?? cause}`,
      { method, path, cause },
    );
  }

  /**
   * Follow a result redirect without leaking credentials to storage.
   *
   * Production stores results in object storage and redirects to a short-lived
   * presigned URL. That URL authenticates itself, so the download must not
   * carry the Makra API key.
   */
  async #downloadRedirect(response, path, signal) {
    const location = response.headers.get("location");
    if (!location) throw new MakraStreamError("Result redirect did not include a location");
    const clock = deadline(this.config.timeout, signal);
    let download;
    try {
      download = await fetch(location, { signal: clock.signal });
    } catch (cause) {
      if (signal?.aborted) throw cause;
      throw this.#connectionError(cause, "GET", path);
    } finally {
      clock.clear();
    }
    if (download.status >= 400) throw await apiError(download, "GET", path);
    return decodeBody(download);
  }

  /**
   * Iterate a run's events, reconnecting if the connection drops.
   *
   * A resumed stream is always a plain GET on the run's event endpoint: the
   * original submission already created the run, and repeating the POST would
   * start a second one. `Last-Event-ID` tells the gateway where to pick up, so
   * no event is delivered twice.
   */
  async *#streamEvents(method, path, { body, idempotencyKey, runId, lastEventId = 0, signal } = {}) {
    let request = {
      method,
      path,
      body,
      headers:
        method === "POST"
          ? { ...submitHeaders(idempotencyKey), Accept: CONTENT_TYPE_SSE }
          : { Accept: CONTENT_TYPE_SSE },
    };
    let attempt = 0;

    for (;;) {
      let cause;
      const clock = deadline(this.config.streamIdleTimeout, signal);
      try {
        const response = await fetch(this.config.url(request.path), {
          method: request.method,
          headers: withResume(request.headers, lastEventId),
          body: request.body === undefined ? undefined : JSON.stringify(request.body),
          signal: clock.signal,
        });
        if (response.status >= 400) throw await apiError(response, request.method, request.path);
        if (!response.headers.get("content-type")?.includes(CONTENT_TYPE_SSE)) {
          throw new MakraStreamError(
            `Expected an event stream but the API returned '${
              response.headers.get("content-type") ?? "no content type"
            }'`,
            { runId: response.headers.get(HEADER_RUN_ID) ?? runId },
          );
        }
        runId ??= response.headers.get(HEADER_RUN_ID) ?? undefined;

        const decoder = new SSEDecoder();
        for await (const line of readLines(response.body, clock.extend)) {
          const message = decoder.feed(line);
          if (!message) continue;
          const event = parseEvent(message, runId);
          attempt = 0;
          lastEventId = event.sequence || lastEventId;
          yield event;
          if (event.isTerminal) return;
        }
      } catch (error) {
        if (signal?.aborted) throw error;
        if (error?.statusCode !== undefined) throw error;
        cause = error;
      } finally {
        clock.clear();
      }

      // Reaching here means the stream ended without a terminal event.
      attempt += 1;
      if (!runId || attempt > this.config.maxRetries) {
        throw new MakraStreamError("Event stream ended before the run finished", {
          runId,
          cause,
        });
      }
      request = {
        method: "GET",
        path: runPath(runId, "/events"),
        body: undefined,
        headers: { Accept: CONTENT_TYPE_SSE },
      };
      await sleep(retryDelay(attempt, { backoff: this.config.retryBackoff }));
    }
  }
}

function submitHeaders(idempotencyKey) {
  return { [HEADER_IDEMPOTENCY_KEY]: idempotencyKey || newIdempotencyKey() };
}

function withResume(headers, lastEventId) {
  return lastEventId > 0
    ? { ...headers, [HEADER_LAST_EVENT_ID]: String(lastEventId) }
    : headers;
}

/** Respect the server's minimum reconciliation interval. */
function nextPollDelay(run, pollInterval) {
  const floor = pollInterval ?? DEFAULT_POLL_INTERVAL_MS;
  const suggested = run?.poll_after_ms;
  return typeof suggested === "number" && suggested > 0
    ? Math.max(floor, suggested)
    : floor;
}

function queryString(params) {
  if (!params) return "";
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) query.set(key, String(value));
  }
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}
