/**
 * Error hierarchy for the Makra SDK.
 *
 * Callers can catch the base `MakraError` for anything the SDK throws, or a
 * specific subclass to branch on a condition worth handling — a missing key, an
 * empty balance, a rate limit. Every HTTP failure carries the decoded body so
 * no information is lost behind the error type.
 */

import { ErrorCodes } from "./constants.js";

/** Base class for all errors thrown by the Makra SDK. */
export class MakraError extends Error {
  constructor(message) {
    super(message);
    this.name = new.target.name;
  }
}

/** An HTTP error response returned by the Makra API. */
export class MakraAPIError extends MakraError {
  constructor(message, { statusCode, body, method, path, code, requestId }) {
    super(message);
    this.statusCode = statusCode;
    this.body = body;
    this.method = method;
    this.path = path;
    this.code = code ?? undefined;
    this.requestId = requestId ?? undefined;
  }
}

/** The API key or session token is missing, invalid, revoked, or expired. */
export class MakraAuthenticationError extends MakraAPIError {}

/** The credential is valid but lacks the required workflow permission. */
export class MakraPermissionError extends MakraAPIError {}

/** The run or result does not exist, or belongs to another principal. */
export class MakraNotFoundError extends MakraAPIError {}

/**
 * The request was rejected before execution. `field` and `reason` are
 * populated for contract and URL-admission failures, which name the offending
 * part of the request without echoing it.
 */
export class MakraInvalidRequestError extends MakraAPIError {
  constructor(message, options) {
    super(message, options);
    const detail = errorDetail(this.body);
    this.field = detail.field;
    this.reason = detail.reason;
    this.index = detail.index;
  }
}

/** The account balance cannot cover the workflow's credit hold. */
export class MakraInsufficientCreditsError extends MakraAPIError {
  constructor(message, options) {
    super(message, options);
    const detail = errorDetail(this.body);
    this.requiredCredits = detail.required_credits;
    this.availableCredits = detail.available_credits;
  }
}

/** Too many requests, or too many workflow runs active at once. */
export class MakraRateLimitError extends MakraAPIError {
  constructor(message, options) {
    super(message, options);
    this.retryAfter = options.retryAfter ?? undefined;
    this.concurrency = errorDetail(this.body).concurrency;
  }
}

/** The API, or an upstream service it depends on, failed. */
export class MakraServerError extends MakraAPIError {}

/** The request could not reach the Makra API. */
export class MakraConnectionError extends MakraError {
  constructor(message, { method = "", path = "", cause } = {}) {
    super(message, { cause });
    this.method = method;
    this.path = path;
    if (cause !== undefined) this.cause = cause;
  }
}

/** The request or an event stream exceeded its configured timeout. */
export class MakraTimeoutError extends MakraConnectionError {
  constructor(message, { runId, ...options } = {}) {
    super(message, options);
    this.runId = runId ?? undefined;
  }
}

/** An event stream ended before a terminal event and could not resume. */
export class MakraStreamError extends MakraError {
  constructor(message, { runId, cause } = {}) {
    super(message);
    this.runId = runId ?? undefined;
    if (cause !== undefined) this.cause = cause;
  }
}

/** A stored-result redirect or download contract failed. */
export class MakraResultError extends MakraStreamError {
  constructor(message, { runId, location, cause } = {}) {
    super(message, { runId, cause });
    this.location = location ?? undefined;
  }
}

/** A run reached a terminal state other than `completed`. */
export class MakraRunFailedError extends MakraError {
  constructor(message, { runId, state, run }) {
    super(message);
    this.runId = runId;
    this.state = state;
    this.run = run;
  }
}

const STATUS_ERRORS = new Map([
  [401, MakraAuthenticationError],
  [402, MakraInsufficientCreditsError],
  [403, MakraPermissionError],
  [404, MakraNotFoundError],
  [429, MakraRateLimitError],
]);

/** Return the structured `{ error: {...} }` object, or an empty object. */
function errorDetail(body) {
  const error = isObject(body) ? body.error : undefined;
  return isObject(error) ? error : {};
}

export function errorCode(body) {
  const code = errorDetail(body).code;
  return typeof code === "string" && code ? code : undefined;
}

/**
 * Pick the most specific human-readable message the body offers.
 *
 * The API has several error envelopes: a structured `{ error: {...} }` object,
 * a flat `{ error: "..." }` string, and the FastAPI `detail` form that
 * Morpheus responses pass through.
 */
export function errorMessage(body, fallback) {
  const message = errorDetail(body).message;
  if (typeof message === "string" && message) return message;
  if (isObject(body)) {
    for (const field of ["message", "detail", "error"]) {
      if (typeof body[field] === "string" && body[field]) return body[field];
    }
  }
  if (typeof body === "string" && body) return body;
  return fallback;
}

/** Map an HTTP error response onto the most specific SDK error. */
export function buildApiError({
  statusCode,
  body,
  method,
  path,
  requestId,
  retryAfter,
}) {
  const message = errorMessage(body, `Makra API returned HTTP ${statusCode}`);
  const code = errorCode(body);
  const options = { statusCode, body, method, path, code, requestId, retryAfter };

  if (statusCode === 429 || code === ErrorCodes.TOO_MANY_CONCURRENT_RUNS) {
    return new MakraRateLimitError(message, options);
  }
  const ErrorClass = STATUS_ERRORS.get(statusCode);
  if (ErrorClass) return new ErrorClass(message, options);
  if (statusCode >= 500) return new MakraServerError(message, options);
  if (statusCode >= 400) return new MakraInvalidRequestError(message, options);
  return new MakraAPIError(message, options);
}

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
