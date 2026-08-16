/** Response decoding and deadline plumbing shared by every request. */

import { HEADER_REQUEST_ID, HEADER_RETRY_AFTER } from "./constants.js";
import { buildApiError } from "./errors.js";
import { parseRetryAfter } from "./retry.js";

/**
 * Decode a response body without ever discarding what the server sent.
 *
 * JSON is parsed, anything else is returned as text, and a body that claims to
 * be JSON but is not falls back to its text rather than throwing.
 */
export async function decodeBody(response) {
  if (response.status === 204) return undefined;
  const text = await response.text();
  if (!text) return undefined;
  if (response.headers.get("content-type")?.toLowerCase().includes("json")) {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
  return text;
}

/** Build the SDK error for an HTTP error response. */
export async function apiError(response, method, path) {
  return buildApiError({
    statusCode: response.status,
    body: await decodeBody(response),
    method,
    path,
    requestId: response.headers.get(HEADER_REQUEST_ID) ?? undefined,
    retryAfter: parseRetryAfter(response.headers.get(HEADER_RETRY_AFTER)),
  });
}

/**
 * An abort signal that fires after `timeoutMs`, or when the caller's own
 * signal does.
 *
 * `AbortSignal.any` would express this in one line but is only available from
 * Node 20, and this SDK supports Node 18.
 *
 * The returned `extend` restarts the clock. Streaming uses it to turn a total
 * deadline into an idle deadline: as long as events keep arriving, the
 * connection stays open.
 */
export function deadline(timeoutMs, external) {
  const controller = new AbortController();
  const abortFromExternal = () => controller.abort(external.reason);

  let timer = setTimeout(() => controller.abort(new DOMException("TimeoutError", "TimeoutError")), timeoutMs);
  if (external) {
    if (external.aborted) abortFromExternal();
    else external.addEventListener("abort", abortFromExternal, { once: true });
  }

  return {
    signal: controller.signal,
    extend() {
      clearTimeout(timer);
      timer = setTimeout(
        () => controller.abort(new DOMException("TimeoutError", "TimeoutError")),
        timeoutMs,
      );
    },
    clear() {
      clearTimeout(timer);
      external?.removeEventListener("abort", abortFromExternal);
    },
  };
}

/** Whether a failed request was aborted rather than refused by the network. */
export function isTimeout(error) {
  return error?.name === "TimeoutError" || error?.name === "AbortError";
}
