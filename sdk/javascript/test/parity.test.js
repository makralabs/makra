import assert from "node:assert/strict";
import { createServer } from "node:http";
import { afterEach, beforeEach, test } from "node:test";

import {
  ExtractOptions,
  Iso3166Alpha2,
  Makra,
  MakraAPIError,
  MakraResultError,
  MakraStreamError,
  ProxyRegion,
  RunStates,
  SchemaOptions,
  ValidationModes,
  runIsTerminal,
  runSucceeded,
} from "../src/index.js";

let server;
let baseUrl;
let requests;
let handler;

beforeEach(async () => {
  requests = [];
  handler = defaultHandler;
  server = createServer(async (request, response) => {
    const body = await readBody(request);
    requests.push({
      method: request.method,
      path: request.url,
      headers: request.headers,
      body: body ? JSON.parse(body) : undefined,
    });
    handler(request, response, requests.at(-1));
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

afterEach(async () => {
  server.closeAllConnections();
  await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())));
});

test("rejects invalid public arguments before making a request", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });
  await assert.rejects(
    client.extract({ urls: ["https://example.com"], schema: { title: "Title" }, timeout: true }),
    /timeout must be a number/,
  );
  await assert.rejects(
    client.extract({ urls: ["https://example.com"], schema: { title: "Title" }, idempotencyKey: "" }),
    /idempotencyKey must be a non-empty string/,
  );
  await assert.rejects(client.getRun(" "), /runId must be a non-empty string/);
  await assert.rejects(client.waitForRun("run-1", { timeout: true }), /timeout must be a number/);
  await assert.rejects(client.waitForRun("run-1", { pollInterval: 0 }), /pollInterval must be greater than 0/);
  await assert.rejects(client.listRuns({ limit: 101 }), /limit must be between 1 and 100/);
  await assert.rejects(client.listRuns({ feature: "crawl" }), /feature must be one of/);
  assert.throws(() => client.streamRunEvents("", {}), /runId must be a non-empty string/);
  assert.throws(() => client.streamRunEvents("run-1", { lastEventId: -1 }), /lastEventId must not be negative/);
  assert.deepEqual(requests, []);
});

test("rejects reserved default headers and boolean constructor durations", () => {
  assert.throws(
    () => new Makra({ defaultHeaders: { "API-KEY": "other" } }),
    /pass apiKey to the Makra constructor/,
  );
  assert.throws(
    () => new Makra({ defaultHeaders: { "Idempotency-Key": "key" } }),
    /pass idempotencyKey to the workflow method/,
  );
  assert.throws(() => new Makra({ timeout: true }), /timeout must be a number/);
  assert.throws(() => new Makra({ maxRetries: true }), /maxRetries must be a number/);
  assert.doesNotThrow(() => new Makra({ defaultHeaders: { "X-Trace-Id": "abc" } }));
});

test("configuration builders produce the same payload as dictionaries", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });
  const mapping = {
    validation_mode: ValidationModes.REPAIR,
    pagination: { enabled: true, additional_pages: 2 },
    crawler: {
      post_ready_wait_ms: 1000,
      proxy: { region: { scope: "country", value: "DE" } },
      recovery: { retry: true },
    },
  };
  const options = new ExtractOptions({
    validationMode: ValidationModes.REPAIR,
    additionalPages: 2,
    postReadyWaitMs: 1000,
    proxyRegion: ProxyRegion.country(Iso3166Alpha2.DE),
    recoveryRetry: true,
  });

  await client.extract({ urls: ["https://example.com"], schema: { title: "Title" }, config: mapping });
  await client.extract({ urls: ["https://example.com"], schema: { title: "Title" }, config: options });
  const submissions = requests.filter((entry) => entry.method === "POST");
  assert.deepEqual(submissions[0].body.config, submissions[1].body.config);
  assert.deepEqual(new ExtractOptions({ additionalPages: 0 }).toConfig().pagination, {
    enabled: true,
    additional_pages: 0,
  });

  await client.schema({ url: "https://example.com", config: new SchemaOptions({ postReadyWaitMs: 0 }) });
  const allSubmissions = requests.filter((entry) => entry.method === "POST");
  assert.equal(allSubmissions[2].body.config.crawler.post_ready_wait_ms, 0);
});

test("rejects every removed configuration key", async () => {
  const client = new Makra({ apiKey: "test-key", baseUrl });
  await assert.rejects(
    client.extract({
      urls: ["https://example.com"],
      schema: { title: "Title" },
      config: { selector_chain_version: "v1" },
    }),
    /selector_chain_version is not supported/,
  );
  assert.deepEqual(requests, []);
});

test("run outcome helpers match Python semantics", () => {
  assert.equal(runIsTerminal({ state: RunStates.COMPLETED }), true);
  assert.equal(runIsTerminal({ state: RunStates.RUNNING }), false);
  assert.equal(runSucceeded({ state: RunStates.COMPLETED }), true);
  assert.equal(runSucceeded({ state: RunStates.COMPLETED, success: false }), false);
  assert.equal(runSucceeded({ state: RunStates.FAILED, success: true }), false);
});

test("retries a workflow with the same idempotency key", async () => {
  let attempts = 0;
  handler = (request, response) => {
    if (request.url === "/workflows/extract") {
      attempts += 1;
      if (attempts < 3) {
        return sendJson(response, 503, { error: { code: "unavailable" } });
      }
      return sendJson(response, 202, {
        run_id: "run-1",
        feature: "extract",
        state: "queued",
      });
    }
    if (request.url === "/workflows/runs/run-1") {
      return sendJson(response, 200, {
        id: "run-1",
        state: "completed",
        success: true,
      });
    }
    return sendJson(response, 200, { success: true });
  };
  const client = new Makra({ apiKey: "test-key", baseUrl, retryBackoff: 1 });
  assert.deepEqual(
    await client.extract({ urls: ["https://example.com"], schema: { title: "Title" } }),
    { success: true },
  );
  const submissions = requests.filter((entry) => entry.path === "/workflows/extract");
  assert.equal(submissions.length, 3);
  assert.equal(new Set(submissions.map((entry) => entry.headers["idempotency-key"])).size, 1);
});

test("one-call workflow timeouts preserve the recoverable run id", async () => {
  handler = (request, response) => {
    if (request.url === "/workflows/extract") {
      return sendJson(response, 202, {
        run_id: "run-timeout",
        feature: "extract",
        state: "queued",
      });
    }
    return sendJson(response, 200, {
      id: "run-timeout",
      state: "running",
      poll_after_ms: 1,
    });
  };
  const { MakraTimeoutError } = await import("../src/index.js");
  const client = new Makra({ apiKey: "test-key", baseUrl });
  await assert.rejects(
    client.extract({
      urls: ["https://example.com"],
      schema: { title: "Title" },
      timeout: 1,
    }),
    (error) =>
      error instanceof MakraTimeoutError &&
      error.runId === "run-timeout" &&
      String(error).includes('getRun("run-timeout")'),
  );
});

test("does not retry an idempotency-key reuse conflict", async () => {
  handler = (request, response) => sendJson(response, 409, {
    error: { code: "idempotency_key_reuse", message: "different request" },
  });
  const client = new Makra({ apiKey: "test-key", baseUrl, retryBackoff: 1 });
  await assert.rejects(
    client.extract({ urls: ["https://example.com"], schema: { title: "Title" } }),
    (error) => error instanceof MakraAPIError && error.code === "idempotency_key_reuse",
  );
  assert.equal(requests.length, 1);
});

test("supports deferred submissions and all direct run-management methods", async () => {
  handler = (request, response) => {
    if (request.url === "/workflows/extract" && request.headers.prefer === "respond-async") {
      return sendJson(response, 202, {
        run_id: "run-1",
        feature: "extract",
        state: "queued",
        status_url: "/workflows/runs/run-1",
      });
    }
    if (request.url.startsWith("/workflows/runs?") && request.method === "GET") {
      return sendJson(response, 200, { items: [{ id: "run-1", state: "completed" }] });
    }
    if (request.url === "/workflows/runs/run-1" && request.method === "GET") {
      return sendJson(response, 200, { id: "run-1", state: "completed", success: true });
    }
    if (request.url === "/workflows/runs/run-1/cancel" && request.method === "POST") {
      return sendJson(response, 200, { id: "run-1", state: "cancelled" });
    }
    sendJson(response, 404, { detail: "Not found" });
  };
  const client = new Makra({ apiKey: "test-key", baseUrl });
  const handle = await client.submitExtract({
    urls: ["https://example.com"],
    schema: { title: "Title" },
  });
  assert.equal(handle.id, "run-1");
  assert.equal((await handle.refresh()).state, "completed");
  assert.equal((await handle.wait()).state, "completed");
  assert.equal((await client.getRun("run-1")).state, "completed");
  assert.equal((await client.listRuns({ limit: 2, feature: "extract" })).items[0].id, "run-1");
  assert.equal((await handle.cancel()).state, "cancelled");
});

test("streams schema generation and submits schema work", async () => {
  handler = (request, response) => {
    if (request.url === "/workflows/schema" && request.headers.prefer === "respond-async") {
      return sendJson(response, 202, { run_id: "schema-1", feature: "schema", state: "queued" });
    }
    response.writeHead(200, {
      "content-type": "text/event-stream",
      "x-makra-run-id": "schema-1",
    });
    response.end('id: 1\nevent: workflow.run.completed\ndata: {"state":"completed"}\n\n');
  };
  const client = new Makra({ apiKey: "test-key", baseUrl });
  const run = await client.submitSchema({ url: "https://example.com" });
  assert.equal(run.id, "schema-1");
  const events = [];
  for await (const event of client.schemaStream({ url: "https://example.com" })) events.push(event);
  assert.equal(events.length, 1);
  assert.equal(events[0].isTerminal, true);
});

test("streams terminal events once and resumes interrupted streams", async () => {
  handler = (request, response) => {
    if (request.method === "POST") {
      response.writeHead(200, {
        "content-type": "text/event-stream",
        "x-makra-run-id": "run-1",
      });
      response.end('id: 1\nevent: workflow.run.started\ndata: {"state":"running"}\n\n');
      return;
    }
    assert.equal(request.url, "/workflows/runs/run-1/events");
    assert.equal(request.headers["last-event-id"], "1");
    response.writeHead(200, { "content-type": "text/event-stream" });
    response.end('id: 2\nevent: workflow.run.completed\ndata: {"state":"completed","success":true}\n\n');
  };
  const client = new Makra({ apiKey: "test-key", baseUrl, retryBackoff: 1 });
  const events = [];
  for await (const event of client.extractStream({ urls: ["https://example.com"], schema: { title: "Title" } })) {
    events.push(event);
  }
  assert.deepEqual(events.map((event) => event.sequence), [1, 2]);
  assert.equal(events.at(-1).isTerminal, true);
});

test("reports a stream that cannot resume with its run id", async () => {
  handler = (request, response) => {
    response.writeHead(200, {
      "content-type": "text/event-stream",
      "x-makra-run-id": "run-1",
    });
    response.end();
  };
  const client = new Makra({ apiKey: "test-key", baseUrl, maxRetries: 0 });
  await assert.rejects(
    async () => {
      for await (const event of client.extractStream({
        urls: ["https://example.com"],
        schema: { title: "Title" },
      })) {
        void event;
      }
    },
    (error) => error instanceof MakraStreamError && error.runId === "run-1",
  );
});

test("downloads result redirects anonymously and validates locations", async () => {
  handler = (request, response) => {
    if (request.url.startsWith("/workflows/runs/run-1/result")) {
      response.writeHead(303, { location: `${baseUrl}/stored?sig=secret` });
      response.end();
      return;
    }
    assert.equal(request.headers["api-key"], undefined);
    sendJson(response, 200, { success: true, data: { title: "Stored" } });
  };
  const client = new Makra({ apiKey: "secret-key", baseUrl });
  assert.deepEqual(await client.getRunResult("run-1"), { success: true, data: { title: "Stored" } });
  assert.equal(requests.length, 2);

  handler = (request, response) => {
    response.writeHead(303, { location: "/relative?sig=secret" });
    response.end();
  };
  await assert.rejects(
    client.getRunResult("run-1"),
    (error) => error instanceof MakraResultError && error.runId === "run-1" && !String(error).includes("secret"),
  );
});

test("propagates a caller abort without converting it to a timeout", async () => {
  const controller = new AbortController();
  const reason = new Error("cancelled by caller");
  controller.abort(reason);
  const client = new Makra({ apiKey: "test-key", baseUrl });
  await assert.rejects(client.ping({ signal: controller.signal }), (error) => error === reason);
});

function defaultHandler(request, response) {
  if (
    (request.url === "/workflows/extract" || request.url === "/workflows/schema") &&
    request.headers.prefer === "respond-async"
  ) {
    return sendJson(response, 202, {
      run_id: "run-default",
      feature: request.url.endsWith("schema") ? "schema" : "extract",
      state: "queued",
    });
  }
  if (request.url === "/workflows/runs/run-default") {
    return sendJson(response, 200, {
      id: "run-default",
      state: "completed",
      success: true,
    });
  }
  if (request.url === "/workflows/runs/run-default/result") {
    return sendJson(response, 200, { success: true });
  }
  sendJson(response, 200, { status: "ok" });
}

function sendJson(response, status, body) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}

function readBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on("data", (chunk) => chunks.push(chunk));
    request.on("end", () => resolve(Buffer.concat(chunks).toString()));
    request.on("error", reject);
  });
}
