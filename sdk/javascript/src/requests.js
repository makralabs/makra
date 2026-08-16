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
  PROXY_REGION_SCOPES,
  SELECTOR_CHAIN_VERSIONS,
  VALIDATION_MODES,
} from "./constants.js";

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
  if (resolved.validation_mode !== undefined && resolved.validation_mode !== null) {
    validatedChoice("config.validation_mode", resolved.validation_mode, VALIDATION_MODES);
  }
  validateFlags(resolved.audit, "config.audit", ["enabled", "use_cache"]);
  validatePagination(resolved.pagination);
  validateFlags(resolved.title, "config.title", ["enabled"]);
  return resolved;
}

function validatedCommonConfig(config, path) {
  if (config === undefined || config === null) return {};
  requireObject(config, path);
  const resolved = { ...config };
  validateMemory(resolved.memory);
  validateCrawler(resolved.crawler);
  return resolved;
}

function validateMemory(memory) {
  if (memory === undefined || memory === null) return;
  requireObject(memory, "config.memory");
  if (memory.selector_chain_version !== undefined && memory.selector_chain_version !== null) {
    validatedChoice(
      "config.memory.selector_chain_version",
      memory.selector_chain_version,
      SELECTOR_CHAIN_VERSIONS,
    );
  }
  validateFlags(memory, "config.memory", ["enabled"]);
}

function validateCrawler(crawler) {
  if (crawler === undefined || crawler === null) return;
  requireObject(crawler, "config.crawler");
  validateBoundedMs(
    crawler.post_ready_wait_ms,
    "config.crawler.post_ready_wait_ms",
    120_000,
  );

  const recovery = crawler.recovery;
  if (recovery !== undefined && recovery !== null) {
    requireObject(recovery, "config.crawler.recovery");
    validateFlags(recovery, "config.crawler.recovery", ["one_last_retry"]);
    validateBoundedMs(
      recovery.one_last_retry_delay_ms,
      "config.crawler.recovery.one_last_retry_delay_ms",
      300_000,
    );
  }

  const proxy = crawler.proxy;
  if (proxy === undefined || proxy === null) return;
  requireObject(proxy, "config.crawler.proxy");
  const region = proxy.region;
  if (region === undefined || region === null) return;
  requireObject(region, "config.crawler.proxy.region");
  if (region.scope !== undefined && region.scope !== null) {
    validatedChoice("config.crawler.proxy.region.scope", region.scope, PROXY_REGION_SCOPES);
  }
  if (region.value !== undefined && region.value !== null && typeof region.value !== "string") {
    throw new TypeError("config.crawler.proxy.region.value must be a string or null");
  }
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
