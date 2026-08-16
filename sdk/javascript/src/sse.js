/**
 * A line-oriented Server-Sent Events decoder.
 *
 * The decoder is deliberately transport-agnostic: it is fed decoded text lines
 * and emits complete events, so the framing rules from the WHATWG SSE spec
 * live in exactly one place.
 */

/** Accumulates SSE field lines and dispatches them on a blank line. */
export class SSEDecoder {
  #event = "";
  #data = [];
  #id;
  #retry;

  constructor() {
    this.lastEventId = undefined;
  }

  /** Consume one line and return an event when the message is complete. */
  feed(rawLine) {
    const line = rawLine.replace(/\r$/, "").replace(/^﻿/, "");
    if (!line) return this.#dispatch();
    // A line beginning with a colon is a comment. The gateway sends
    // ": keepalive" every 15 seconds to hold the connection open.
    if (line.startsWith(":")) return null;

    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? "" : line.slice(separator + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") {
      this.#event = value;
    } else if (field === "data") {
      this.#data.push(value);
    } else if (field === "id" && !value.includes("\0")) {
      this.#id = value;
      this.lastEventId = value;
    } else if (field === "retry") {
      const retry = Number(value);
      if (Number.isInteger(retry)) this.#retry = retry;
    }
    return null;
  }

  #dispatch() {
    if (this.#data.length === 0 && !this.#event) {
      this.#reset();
      return null;
    }
    const event = {
      event: this.#event || "message",
      data: this.#data.join("\n"),
      id: this.#id,
      retry: this.#retry,
    };
    this.#reset();
    return event;
  }

  #reset() {
    this.#event = "";
    this.#data = [];
    this.#id = undefined;
  }
}

/**
 * Split a `fetch` response body into text lines.
 *
 * `onChunk` fires for every network chunk, including heartbeat comments, which
 * is what lets the caller treat silence — rather than slowness — as a dead
 * connection.
 */
export async function* readLines(body, onChunk) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      onChunk?.();
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      yield* lines;
    }
    buffer += decoder.decode();
    if (buffer) yield buffer;
  } finally {
    reader.cancel().catch(() => {});
  }
}
