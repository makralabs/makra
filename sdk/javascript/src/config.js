/**
 * Client configuration resolution.
 *
 * Settings resolve in one fixed order — explicit option, then environment
 * variable, then SDK default — so an application can be configured entirely
 * from code, entirely from the environment, or from any mix of the two.
 *
 * Durations passed as options are milliseconds, the JavaScript convention.
 * `MAKRA_TIMEOUT` is read in seconds instead, because it is shared with the
 * other Makra SDKs.
 */

import {
  CONTENT_TYPE_JSON,
  DEFAULT_MAX_RETRIES,
  DEFAULT_RETRY_BACKOFF_MS,
  DEFAULT_STREAM_IDLE_TIMEOUT_MS,
  DEFAULT_TIMEOUT_MS,
  DUMMY_API_KEY,
  ENV_API_KEY,
  ENV_BASE_URL,
  ENV_MAX_RETRIES,
  ENV_TIMEOUT,
  HEADER_API_KEY,
  PRODUCTION_BASE_URL,
  RESERVED_REQUEST_HEADERS,
  USER_AGENT,
} from "./constants.js";

/** Resolve constructor options against the environment and defaults. */
export function resolveConfig({
  apiKey,
  baseUrl,
  timeout,
  streamIdleTimeout,
  maxRetries,
  retryBackoff,
  defaultHeaders,
  env = typeof process === "undefined" ? {} : process.env,
} = {}) {
  const envTimeout = env[ENV_TIMEOUT];
  const config = {
    apiKey: apiKey || env[ENV_API_KEY] || DUMMY_API_KEY,
    baseUrl: normalizeBaseUrl(
      baseUrl === undefined ? env[ENV_BASE_URL] || PRODUCTION_BASE_URL : baseUrl,
    ),
    timeout: positive(
      "timeout",
      timeout,
      envTimeout === undefined ? undefined : Number(envTimeout) * 1000,
      DEFAULT_TIMEOUT_MS,
    ),
    streamIdleTimeout: positive(
      "streamIdleTimeout",
      streamIdleTimeout,
      undefined,
      DEFAULT_STREAM_IDLE_TIMEOUT_MS,
    ),
    maxRetries: nonNegative(
      "maxRetries",
      maxRetries,
      env[ENV_MAX_RETRIES],
      DEFAULT_MAX_RETRIES,
    ),
    retryBackoff: positive(
      "retryBackoff",
      retryBackoff,
      undefined,
      DEFAULT_RETRY_BACKOFF_MS,
    ),
    defaultHeaders: validatedDefaultHeaders(defaultHeaders),
  };

  /** Headers sent on every request, including health checks. */
  config.headers = () => ({
    [HEADER_API_KEY]: config.apiKey,
    "Content-Type": CONTENT_TYPE_JSON,
    Accept: CONTENT_TYPE_JSON,
    "User-Agent": USER_AGENT,
    ...config.defaultHeaders,
  });
  config.url = (path) => config.baseUrl + path;

  return Object.freeze(config);
}

function normalizeBaseUrl(value) {
  const invalid = new TypeError("baseUrl must be an absolute HTTP or HTTPS URL");
  if (typeof value !== "string" || !value) throw invalid;
  const normalized = value.replace(/\/+$/, "");
  let parsed;
  try {
    parsed = new URL(normalized);
  } catch {
    throw invalid;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") throw invalid;
  return normalized;
}

function coerce(name, explicit, fromEnv, fallback) {
  for (const value of [explicit, fromEnv]) {
    if (value === undefined || value === null || value === "") continue;
    if (typeof value === "boolean") {
      throw new TypeError(`${name} must be a number`);
    }
    const number = Number(value);
    if (!Number.isFinite(number)) {
      throw new TypeError(`${name} must be a number`);
    }
    return number;
  }
  return fallback;
}

function validatedDefaultHeaders(defaultHeaders) {
  if (defaultHeaders === undefined || defaultHeaders === null) return {};
  if (
    typeof defaultHeaders !== "object" ||
    Array.isArray(defaultHeaders)
  ) {
    throw new TypeError("defaultHeaders must be an object of strings");
  }
  const resolved = {};
  for (const [key, value] of Object.entries(defaultHeaders)) {
    if (typeof value !== "string") {
      throw new TypeError("defaultHeaders keys and values must be strings");
    }
    const reserved = key.toLowerCase();
    if (RESERVED_REQUEST_HEADERS.has(reserved)) {
      throw new TypeError(
        `defaultHeaders must not include reserved header '${key}'; ${reservedHeaderHint(reserved)}`,
      );
    }
    resolved[key] = value;
  }
  return resolved;
}

const RESERVED_HEADER_HINTS = {
  "api-key": "pass apiKey to the Makra constructor",
  "content-type": "the SDK sets Content-Type automatically",
  accept: "the SDK sets Accept automatically",
  "user-agent": "the SDK sets User-Agent automatically",
  "idempotency-key": "pass idempotencyKey to the workflow method",
  prefer: "use submitExtract or submitSchema for deferred runs",
  "last-event-id": "pass lastEventId to streamRunEvents",
};

function reservedHeaderHint(name) {
  return RESERVED_HEADER_HINTS[name] ?? "this header is owned by the SDK";
}

function positive(name, explicit, fromEnv, fallback) {
  const value = coerce(name, explicit, fromEnv, fallback);
  if (value <= 0) throw new RangeError(`${name} must be greater than 0`);
  return value;
}

function nonNegative(name, explicit, fromEnv, fallback) {
  const value = coerce(name, explicit, fromEnv, fallback);
  if (value < 0) throw new RangeError(`${name} must not be negative`);
  return value;
}
