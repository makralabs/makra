import assert from "node:assert/strict";
import { createServer } from "node:http";
import { afterEach, beforeEach, test } from "node:test";

import { DUMMY_API_KEY, Makra, MakraAPIError } from "../src/index.js";

let server;
let baseUrl;
let requests;

beforeEach(async () => {
  requests = [];
  server = createServer((request, response) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => {
      const rawBody = Buffer.concat(chunks).toString();
      requests.push({
        method: request.method,
        path: request.url,
        headers: request.headers,
        body: rawBody ? JSON.parse(rawBody) : undefined,
      });

      if (request.url === "/workflows/extract") {
        sendJson(response, 200, { success: true, data: { title: "Makra" } });
      } else if (request.url === "/workflows/schema") {
        sendJson(response, 422, { detail: "Invalid URL" });
      } else if (request.url === "/healthz") {
        sendJson(response, 200, { status: "ok" });
      } else {
        sendJson(response, 404, { detail: "Not found" });
      }
    });
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  baseUrl = `http://127.0.0.1:${address.port}`;
});

afterEach(async () => {
  server.closeAllConnections();
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
});

test("ping uses healthz and sends the Api-Key header", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl: `${baseUrl}/` });

  assert.deepEqual(await client.ping(), { status: "ok" });
  assert.equal(requests[0].path, "/healthz");
  assert.equal(requests[0].headers["api-key"], "test-key");
});

test("extract sends the workflow wire payload", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });

  const result = await client.extract({
    urls: ["https://example.com"],
    schema: { title: "Title of the page" },
    executionMode: "sequential",
    config: {
      validation_mode: "repair",
      memory: { enabled: true, selector_chain_version: "v2" },
      pagination: { enabled: true, additional_pages: 2 },
      crawler: {
        post_ready_wait_ms: 1000,
        proxy: { region: { scope: "country", value: "DE" } },
        recovery: {
          one_last_retry: true,
          one_last_retry_delay_ms: null,
        },
      },
      audit: { enabled: false, use_cache: true },
    },
  });

  assert.deepEqual(result, { success: true, data: { title: "Makra" } });
  assert.equal(requests[0].path, "/workflows/extract");
  assert.deepEqual(requests[0].body, {
    urls: ["https://example.com"],
    schema: { title: "Title of the page" },
    execution_mode: "sequential",
    config: {
      validation_mode: "repair",
      memory: { enabled: true, selector_chain_version: "v2" },
      pagination: { enabled: true, additional_pages: 2 },
      crawler: {
        post_ready_wait_ms: 1000,
        proxy: { region: { scope: "country", value: "DE" } },
        recovery: {
          one_last_retry: true,
          one_last_retry_delay_ms: null,
        },
      },
      audit: { enabled: false, use_cache: true },
    },
  });
});

test("schema sends the workflow wire payload", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });

  await assert.rejects(
    client.schema({
      url: "https://invalid.example",
      onlyMemoized: true,
      config: { memory: { enabled: false } },
    }),
    (error) => {
      assert.ok(error instanceof MakraAPIError);
      assert.equal(error.statusCode, 422);
      assert.equal(error.message, "Invalid URL");
      assert.deepEqual(error.body, { detail: "Invalid URL" });
      assert.equal(error.method, "POST");
      assert.equal(error.path, "/workflows/schema");
      return true;
    },
  );

  assert.deepEqual(requests[0].body, {
    url: "https://invalid.example",
    only_memoized: true,
    config: { memory: { enabled: false } },
  });
});

test("client-side validation happens before network I/O", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });

  await assert.rejects(
    client.extract({ urls: [], schema: { title: "Title" } }),
    /urls must contain at least one URL/,
  );
  await assert.rejects(
    client.extract({ urls: ["https://example.com"], schema: {} }),
    /schema must be a non-empty/,
  );
  assert.deepEqual(requests, []);
});

test("an explicit empty base URL is invalid", () => {
  assert.throws(
    () => new Makra({ baseUrl: "" }),
    /absolute HTTP or HTTPS URL/,
  );
});

test("a missing API key sends the dummy key", async () => {
  const previousApiKey = process.env.MAKRA_API_KEY;
  delete process.env.MAKRA_API_KEY;
  try {
    await new Makra({ baseUrl }).ping();
  } finally {
    restoreEnvironment("MAKRA_API_KEY", previousApiKey);
  }

  assert.equal(requests[0].headers["api-key"], DUMMY_API_KEY);
});

test("explicit configuration overrides environment variables", async () => {
  const previousApiKey = process.env.MAKRA_API_KEY;
  const previousBaseUrl = process.env.MAKRA_BASE_URL;
  process.env.MAKRA_API_KEY = "environment-key";
  process.env.MAKRA_BASE_URL = "https://environment.invalid";
  try {
    await new Makra({ apiKey: "explicit-key", baseUrl }).ping();
  } finally {
    restoreEnvironment("MAKRA_API_KEY", previousApiKey);
    restoreEnvironment("MAKRA_BASE_URL", previousBaseUrl);
  }

  assert.equal(requests[0].headers["api-key"], "explicit-key");
});

function sendJson(response, status, body) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}

function restoreEnvironment(name, value) {
  if (value === undefined) delete process.env[name];
  else process.env[name] = value;
}
