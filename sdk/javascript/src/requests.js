/**
 * Request validation and payload construction.
 *
 * Every check here happens before any network I/O, so a malformed call fails
 * locally instead of spending a round trip to learn the same thing. Only the
 * rules the API itself enforces are duplicated — the SDK never invents
 * constraints of its own.
 */

import {
  EXECUTION_MODES,
  ExecutionModes,
  PROXY_CONTINENTS,
  PROXY_REGION_SCOPES,
  ProxyRegionScopes,
  VALIDATION_MODES,
} from "./constants.js";
import { ISO_3166_ALPHA2 } from "./iso3166.js";

/** Build the `POST /workflows/extract` body. */
export function buildExtractPayload({ urls, schema, executionMode, config, stream }) {
  const payload = {
    urls: validatedUrls(urls),
    schema: validatedSchema(schema),
    execution_mode: validatedChoice("executionMode", executionMode, EXECUTION_MODES),
    config: validatedExtractConfig(config),
  };
  if (stream) payload.stream = true;
  return payload;
}

/** Build the `POST /workflows/schema` body. */
export function buildSchemaPayload({ url, onlyMemoized, config, stream }) {
  if (typeof url !== "string" || !url.trim()) {
    throw new TypeError("url must be a non-empty string");
  }
  if (typeof onlyMemoized !== "boolean") {
    throw new TypeError("onlyMemoized must be a boolean");
  }
  const payload = {
    url,
    only_memoized: onlyMemoized,
    config: validatedCommonConfig(config, "config"),
  };
  if (stream) payload.stream = true;
  return payload;
}

/** A fresh key so a retried submission replays instead of double-billing. */
export function newIdempotencyKey() {
  return `makra-sdk-${globalThis.crypto.randomUUID().replace(/-/g, "")}`;
}

/**
 * Resolve how long a workflow request may occupy the connection.
 *
 * An explicit timeout always wins. Otherwise the client default is a
 * per-page budget: pagination adds one unit per additional page, and
 * sequential multi-URL extracts multiply by the URL count.
 *
 * Durations are milliseconds.
 */
export function resolveWorkflowTimeout(
  explicit,
  base,
  { config, urlCount = 1, executionMode = ExecutionModes.CONCURRENT } = {},
) {
  if (explicit !== undefined && explicit !== null) return explicit;
  let pages = 1;
  const pagination = config?.pagination;
  if (pagination && pagination.enabled) {
    const extra = pagination.additional_pages || 0;
    if (Number.isInteger(extra) && extra > 0) pages = 1 + extra;
  }
  const urls =
    executionMode === ExecutionModes.SEQUENTIAL && urlCount > 0 ? urlCount : 1;
  return base * pages * urls;
}

function validatedUrls(urls) {
  if (!Array.isArray(urls)) throw new TypeError("urls must be an array of URL strings");
  if (urls.length === 0) throw new RangeError("urls must contain at least one URL");
  for (const url of urls) {
    if (typeof url !== "string" || !url.trim()) {
      throw new TypeError("each URL must be a non-empty string");
    }
  }
  return [...urls];
}

function validatedSchema(schema) {
  const empty =
    schema === null ||
    typeof schema !== "object" ||
    (Array.isArray(schema) ? schema.length === 0 : Object.keys(schema).length === 0);
  if (empty) {
    throw new TypeError("schema must be a non-empty JSON object or array");
  }
  return schema;
}

function validatedExtractConfig(config) {
  const resolved = validatedCommonConfig(config, "config");
  if (Object.prototype.hasOwnProperty.call(resolved, "audit")) {
    throw new TypeError("config.audit is not supported");
  }
  if (resolved.validation_mode !== undefined && resolved.validation_mode !== null) {
    validatedChoice("config.validation_mode", resolved.validation_mode, VALIDATION_MODES);
  }
  validatePagination(resolved.pagination);
  validateFlags(resolved.title, "config.title", ["enabled"]);
  return resolved;
}

function validatedCommonConfig(config, path) {
  if (config === undefined || config === null) return {};
  requireObject(config, path);
  const resolved = { ...config };
  if (Object.prototype.hasOwnProperty.call(resolved, "memory")) {
    throw new TypeError("config.memory is not supported");
  }
  if (resolved.crawler !== undefined && resolved.crawler !== null) {
    resolved.crawler = normalizedCrawler(resolved.crawler);
  }
  return resolved;
}

function normalizedCrawler(crawler) {
  requireObject(crawler, "config.crawler");
  const resolved = { ...crawler };
  validateBoundedMs(
    resolved.post_ready_wait_ms,
    "config.crawler.post_ready_wait_ms",
    120_000,
  );
  if (resolved.recovery !== undefined && resolved.recovery !== null) {
    resolved.recovery = recoveryToWire(resolved.recovery);
  }
  if (resolved.proxy !== undefined && resolved.proxy !== null) {
    resolved.proxy = normalizedProxy(resolved.proxy);
  }
  return resolved;
}

function recoveryToWire(recovery) {
  requireObject(recovery, "config.crawler.recovery");
  const extra = Object.keys(recovery).filter(
    (key) => key !== "retry" && key !== "retry_delay_ms",
  );
  if (extra.length > 0) {
    throw new TypeError(
      `config.crawler.recovery only accepts retry and retry_delay_ms; unknown keys: ${extra.sort().join(", ")}`,
    );
  }
  const wire = {};
  if (Object.prototype.hasOwnProperty.call(recovery, "retry")) {
    const retry = recovery.retry;
    if (retry !== undefined && retry !== null && typeof retry !== "boolean") {
      throw new TypeError("config.crawler.recovery.retry must be a boolean");
    }
    if (retry !== undefined && retry !== null) wire.one_last_retry = retry;
  }
  if (Object.prototype.hasOwnProperty.call(recovery, "retry_delay_ms")) {
    validateBoundedMs(
      recovery.retry_delay_ms,
      "config.crawler.recovery.retry_delay_ms",
      300_000,
    );
    wire.one_last_retry_delay_ms = recovery.retry_delay_ms;
  }
  return wire;
}

function normalizedProxy(proxy) {
  requireObject(proxy, "config.crawler.proxy");
  const resolved = { ...proxy };
  if (resolved.region === undefined || resolved.region === null) return resolved;
  resolved.region = normalizedRegion(resolved.region);
  return resolved;
}

function normalizedRegion(region) {
  requireObject(region, "config.crawler.proxy.region");
  const resolved = { ...region };
  if (resolved.scope !== undefined && resolved.scope !== null) {
    validatedChoice("config.crawler.proxy.region.scope", resolved.scope, PROXY_REGION_SCOPES);
  }
  if (
    resolved.value !== undefined &&
    resolved.value !== null &&
    typeof resolved.value !== "string"
  ) {
    throw new TypeError("config.crawler.proxy.region.value must be a string or null");
  }
  if (resolved.scope === ProxyRegionScopes.WORLDWIDE && resolved.value != null) {
    throw new TypeError(
      "config.crawler.proxy.region.value must be null when scope is worldwide",
    );
  }
  if (resolved.scope === ProxyRegionScopes.COUNTRY) {
    if (!resolved.value) {
      throw new TypeError(
        "config.crawler.proxy.region.value is required when scope is country",
      );
    }
    const normalized = resolved.value.trim().toUpperCase();
    if (!ISO_3166_ALPHA2.has(normalized)) {
      throw new TypeError(
        "config.crawler.proxy.region.value must be an ISO 3166-1 alpha-2 country code such as Iso3166Alpha2.DE",
      );
    }
    resolved.value = normalized;
  }
  if (resolved.scope === ProxyRegionScopes.CONTINENT) {
    if (!resolved.value) {
      throw new TypeError(
        "config.crawler.proxy.region.value is required when scope is continent",
      );
    }
    const normalized = resolved.value.trim().toLowerCase();
    if (!PROXY_CONTINENTS.has(normalized)) {
      throw new TypeError(
        "config.crawler.proxy.region.value must be a ProxyContinents slug such as ProxyContinents.EUROPE",
      );
    }
    resolved.value = normalized;
  }
  return resolved;
}

function validatePagination(pagination) {
  if (pagination === undefined || pagination === null) return;
  requireObject(pagination, "config.pagination");
  validateFlags(pagination, "config.pagination", ["enabled"]);
  const pages = pagination.additional_pages;
  if (pages === undefined || pages === null) return;
  if (!Number.isInteger(pages) || pages < 0) {
    throw new RangeError("config.pagination.additional_pages must be an integer >= 0");
  }
}

function validateFlags(container, path, names) {
  if (container === undefined || container === null) return;
  requireObject(container, path);
  for (const name of names) {
    const value = container[name];
    if (value !== undefined && value !== null && typeof value !== "boolean") {
      throw new TypeError(`${path}.${name} must be a boolean`);
    }
  }
}

function validateBoundedMs(value, path, maximum) {
  if (value === undefined || value === null) return;
  if (!Number.isInteger(value)) {
    throw new TypeError(`${path} must be an integer or null`);
  }
  if (value < 0 || value > maximum) {
    throw new RangeError(`${path} must be between 0 and ${maximum}`);
  }
}

function validatedChoice(name, value, allowed) {
  if (!allowed.has(value)) {
    throw new TypeError(`${name} must be one of: ${[...allowed].sort().join(", ")}`);
  }
  return value;
}

function requireObject(value, path) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new TypeError(`${path} must be an object`);
  }
}
