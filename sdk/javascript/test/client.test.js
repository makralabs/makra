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

      if (request.url === "/api/v1/extract") {
        sendJson(response, 200, { success: true, data: { title: "Makra" } });
      } else if (request.url === "/api/v1/preprocess") {
        sendJson(response, 422, { detail: "Invalid URL" });
      } else if (
        request.url === "/api/v0/format-markdown" &&
        requests.at(-1).body.url === "https://json.example"
      ) {
        sendJson(response, 200, "not markdown");
      } else if (request.url === "/api/v0/format-markdown") {
        response.writeHead(200, { "content-type": "text/markdown" });
        response.end("# Makra");
      } else {
        sendJson(response, 200, { message: "pong" });
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

test("ping uses the root route and sends the bearer API key", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl: `${baseUrl}/` });

  assert.deepEqual(await client.ping(), { message: "pong" });
  assert.equal(requests[0].path, "/ping");
  assert.equal(requests[0].headers.authorization, "Bearer test-key");
});

test("extract sends the v1 wire payload", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });

  const result = await client.extract({
    urls: ["https://example.com"],
    outputSchema: { title: "Title of the page" },
    actions: ["pagination"],
    config: { use_cache: true },
  });

  assert.deepEqual(result, { success: true, data: { title: "Makra" } });
  assert.equal(requests[0].path, "/api/v1/extract");
  assert.deepEqual(requests[0].body, {
    urls: ["https://example.com"],
    output_schema: { title: "Title of the page" },
    actions: ["pagination"],
    config: { use_cache: true },
  });
});

test("text responses are returned as text", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });

  assert.equal(await client.formatMarkdown("https://example.com"), "# Makra");
});

test("Markdown rejects a non-text content type", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });

  await assert.rejects(
    client.formatMarkdown("https://json.example"),
    /Expected a text\/ response/,
  );
});

test("HTTP errors expose status, body, and request context", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });

  await assert.rejects(
    client.preprocess({ urls: ["https://invalid.example"] }),
    (error) => {
      assert.ok(error instanceof MakraAPIError);
      assert.equal(error.statusCode, 422);
      assert.equal(error.message, "Invalid URL");
      assert.deepEqual(error.body, { detail: "Invalid URL" });
      assert.equal(error.method, "POST");
      assert.equal(error.path, "/api/v1/preprocess");
      return true;
    },
  );
});

test("client-side validation happens before network I/O", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });

  await assert.rejects(
    client.extract({ urls: [], outputSchema: { title: "Title" } }),
    /urls must contain at least one URL/,
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

  assert.equal(requests[0].headers.authorization, `Bearer ${DUMMY_API_KEY}`);
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

  assert.equal(requests[0].headers.authorization, "Bearer explicit-key");
});

function sendJson(response, status, body) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}

function restoreEnvironment(name, value) {
  if (value === undefined) delete process.env[name];
  else process.env[name] = value;
}
