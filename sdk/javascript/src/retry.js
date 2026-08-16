/**
 * Retry policy for the Makra client.
 *
 * A request is retried only when repeating it is safe. GET requests always
 * are. A workflow submission is only safe because the SDK attaches an
 * `Idempotency-Key`: the gateway then replays the original run instead of
 * starting a second billable one.
 */

import { DEFAULT_RETRY_BACKOFF_MS, MAX_RETRY_BACKOFF_MS } from "./constants.js";

export const RETRYABLE_STATUS_CODES = new Set([
  408, 409, 425, 429, 500, 502, 503, 504,
]);

/**
 * 409 is retryable only for the idempotent replay race, never for a genuine
 * conflict such as reusing one key for two different bodies.
 */
const NON_RETRYABLE_CODES = new Set(["idempotency_key_reuse", "run_not_terminal"]);

export function isRetryableStatus(statusCode, code) {
  if (code && NON_RETRYABLE_CODES.has(code)) return false;
  return RETRYABLE_STATUS_CODES.has(statusCode);
}

/**
 * Milliseconds to wait before attempt `attempt` (1-based).
 *
 * A server-supplied `Retry-After` always wins. Otherwise the delay grows
 * exponentially with full jitter, which spreads out a fleet of clients that
 * were all rejected at the same moment.
 */
export function retryDelay(
  attempt,
  { backoff = DEFAULT_RETRY_BACKOFF_MS, retryAfter } = {},
) {
  if (retryAfter !== undefined && retryAfter !== null && retryAfter >= 0) {
    return Math.min(retryAfter * 1000, MAX_RETRY_BACKOFF_MS);
  }
  const ceiling = Math.min(
    backoff * 2 ** Math.max(attempt - 1, 0),
    MAX_RETRY_BACKOFF_MS,
  );
  return ceiling / 2 + Math.random() * (ceiling / 2);
}

/** Parse a `Retry-After` header expressed in seconds. */
export function parseRetryAfter(value) {
  if (!value) return undefined;
  const seconds = Number(String(value).trim());
  if (!Number.isFinite(seconds) || seconds < 0) return undefined;
  return seconds;
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
