const PRODUCTION_BASE_URL = "https://api.makralabs.org";
const DEVELOPMENT_BASE_URL = "http://localhost:6900";
const DUMMY_API_KEY = "makra-development-key";

export class MakraError extends Error {
  constructor(message) {
    super(message);
    this.name = "MakraError";
  }
}

export class MakraAPIError extends MakraError {
  constructor(message, { statusCode, body, method, path, requestId }) {
    super(message);
    this.name = "MakraAPIError";
    this.statusCode = statusCode;
    this.body = body;
    this.method = method;
    this.path = path;
    this.requestId = requestId;
  }
}

export class MakraConnectionError extends MakraError {
  constructor(message, { method, path, cause } = {}) {
    super(message);
    this.name = "MakraConnectionError";
    this.method = method;
    this.path = path;
    if (cause !== undefined) this.cause = cause;
  }
}

export class Makra {
  constructor({
    apiKey,
    baseUrl,
    apiVersion = "v1",
    timeout = 120_000,
  } = {}) {
    apiKey = apiKey || process.env.MAKRA_API_KEY || DUMMY_API_KEY;
    baseUrl =
      baseUrl === undefined
        ? process.env.MAKRA_BASE_URL || PRODUCTION_BASE_URL
        : baseUrl;
    if (typeof baseUrl !== "string") {
      throw new TypeError("baseUrl must be an absolute HTTP or HTTPS URL");
    }
    const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");
    let parsedUrl;
    try {
      parsedUrl = new URL(normalizedBaseUrl);
    } catch {
      throw new TypeError("baseUrl must be an absolute HTTP or HTTPS URL");
    }
    if (!["http:", "https:"].includes(parsedUrl.protocol)) {
      throw new TypeError("baseUrl must be an absolute HTTP or HTTPS URL");
    }

    if (typeof apiVersion !== "string") {
      throw new TypeError("apiVersion must be a non-empty string");
    }
    const normalizedVersion = apiVersion.replace(/^\/+|\/+$/g, "");
    if (!normalizedVersion) throw new TypeError("apiVersion must not be empty");

    this.apiKey = apiKey;
    this.baseUrl = normalizedBaseUrl;
    this.apiVersion = normalizedVersion;
    this.timeout = timeout;
  }

  ping() {
    return this.#request("GET", "/ping");
  }

  async extract({ urls, outputSchema, actions = [], config = {} }) {
    validateUrls(urls);
    if (
      outputSchema === null ||
      typeof outputSchema !== "object" ||
      Object.keys(outputSchema).length === 0
    ) {
      throw new TypeError(
        "outputSchema must be a non-empty JSON object or array",
      );
    }
    return this.#request("POST", this.#versionedPath("extract"), {
      urls,
      output_schema: outputSchema,
      actions,
      config,
    });
  }

  async preprocess({ urls, options = {} }) {
    validateUrls(urls);
    return this.#request("POST", this.#versionedPath("preprocess"), {
      urls,
      options,
    });
  }

  async pageSchema({
    urls,
    outputType = "json",
    debugMode = false,
    debugOutputType = "text",
  }) {
    validateUrls(urls);
    if (!["json", "text"].includes(outputType)) {
      throw new TypeError("outputType must be 'json' or 'text'");
    }
    return this.#request("POST", this.#versionedPath("page-schema"), {
      urls,
      output_type: outputType,
      debug_mode: debugMode,
      debug_output_type: debugOutputType,
    });
  }

  async formatMarkdown(url) {
    if (typeof url !== "string" || !url.trim()) {
      throw new TypeError("url must be a non-empty string");
    }
    const path = "/api/v0/format-markdown";
    const response = await this.#request(
      "POST",
      path,
      { url },
      { expectedContentType: "text/" },
    );
    if (typeof response !== "string") {
      throw new MakraConnectionError(
        "Expected a text response from the Makra API",
        { method: "POST", path },
      );
    }
    return response;
  }

  #versionedPath(endpoint) {
    return `/api/${this.apiVersion}/${endpoint}`;
  }

  async #request(method, path, body, { expectedContentType } = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);
    let response;
    let decodedBody;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: {
          Accept: "application/json, text/plain, text/markdown",
          Authorization: `Bearer ${this.apiKey}`,
          "Content-Type": "application/json",
          "User-Agent": "makra-javascript/0.1.0",
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
      decodedBody = await decodeResponse(response);
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      throw new MakraConnectionError(
        `Could not connect to the Makra API: ${reason}`,
        { method, path, cause: error },
      );
    } finally {
      clearTimeout(timeoutId);
    }

    if (!response.ok) {
      throw new MakraAPIError(
        errorMessage(decodedBody, `Makra API returned HTTP ${response.status}`),
        {
          statusCode: response.status,
          body: decodedBody,
          method,
          path,
          requestId: response.headers.get("x-request-id") ?? undefined,
        },
      );
    }
    const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
    if (expectedContentType && !contentType.startsWith(expectedContentType)) {
      throw new MakraConnectionError(
        `Expected a ${expectedContentType} response from the Makra API`,
        { method, path },
      );
    }
    return decodedBody;
  }
}

function validateUrls(urls) {
  if (!Array.isArray(urls) || urls.length === 0) {
    throw new TypeError("urls must contain at least one URL");
  }
  if (urls.some((url) => typeof url !== "string" || !url.trim())) {
    throw new TypeError("each URL must be a non-empty string");
  }
}

async function decodeResponse(response) {
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

function errorMessage(body, fallback) {
  if (body && typeof body === "object") {
    for (const field of ["message", "detail", "error"]) {
      if (typeof body[field] === "string" && body[field]) return body[field];
    }
  }
  return typeof body === "string" && body ? body : fallback;
}

export { DEVELOPMENT_BASE_URL, DUMMY_API_KEY, PRODUCTION_BASE_URL };
