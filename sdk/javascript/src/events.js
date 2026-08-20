/** Workflow events, the domain layer on top of SSE framing. */

import { RunStates, TERMINAL_EVENT_TYPES } from "./constants.js";

/**
 * One progress or lifecycle event from a workflow run.
 *
 * `payload` is the event body exactly as the API sent it. The named accessors
 * are conveniences over the fields the gateway guarantees on terminal events;
 * anything else stays reachable through `payload`.
 */
export class WorkflowEvent {
  constructor({ type, sequence, payload, runId }) {
    this.type = type;
    this.sequence = sequence;
    this.payload = payload;
    this.runId = runId;
  }

  /** Whether this event closes the stream. */
  get isTerminal() {
    return TERMINAL_EVENT_TYPES.has(this.type);
  }

  /** The fine-grained step name; compare with `StreamDetailTypes`. */
  get detailType() {
    return stringOrUndefined(this.payload.stream_event_type);
  }

  get status() {
    return stringOrUndefined(this.payload.status);
  }

  get reason() {
    return stringOrUndefined(this.payload.reason);
  }

  /** Domain success on a terminal event. `undefined` before the run ends. */
  get success() {
    return typeof this.payload.success === "boolean" ? this.payload.success : undefined;
  }
}

/** Convert a raw SSE message into a workflow event. */
export function parseEvent(message, runId) {
  let payload = {};
  if (message.data) {
    let decoded;
    try {
      decoded = JSON.parse(message.data);
    } catch {
      decoded = { raw: message.data };
    }
    payload =
      typeof decoded === "object" && decoded !== null && !Array.isArray(decoded)
        ? decoded
        : { data: decoded };
  }
  return new WorkflowEvent({
    type: message.event,
    sequence: parseSequence(message.id),
    payload,
    runId,
  });
}

const TERMINAL_STATES = new Map([
  ["workflow.run.completed", RunStates.COMPLETED],
  ["workflow.run.failed", RunStates.FAILED],
  ["workflow.run.cancelled", RunStates.CANCELLED],
  ["workflow.run.budget_exhausted", RunStates.BUDGET_EXHAUSTED],
]);

/** The run state implied by a terminal event. */
export function terminalState(event) {
  return event.status ?? TERMINAL_STATES.get(event.type) ?? RunStates.COMPLETED;
}

function parseSequence(raw) {
  if (!raw) return 0;
  const sequence = Number.parseInt(raw, 10);
  return Number.isFinite(sequence) ? sequence : 0;
}

function stringOrUndefined(value) {
  return typeof value === "string" ? value : undefined;
}
