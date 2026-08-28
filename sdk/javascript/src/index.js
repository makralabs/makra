/**
 * Makra JavaScript SDK.
 *
 * Structured web data extraction, in three shapes:
 *
 * ```js
 * import { Makra } from "makra";
 *
 * const makra = new Makra({ apiKey: "mk_live_..." });
 *
 * // 1. Convenient — durable submission, one call in, one result out.
 * const data = await makra.extract({ urls, schema });
 *
 * // 2. Streaming — watch a run happen, then read the stored result.
 * let runId;
 * for await (const event of makra.extractStream({ urls, schema })) {
 *   runId = event.runId;
 * }
 * const streamed = await makra.getRunResult(runId);
 *
 * // 3. Deferred — submit now, collect later from anywhere.
 * const run = await makra.submitExtract({ urls, schema });
 * await run.wait();
 * const deferred = await run.result();
 * ```
 */

export { Makra } from "./client.js";
export { resolveConfig } from "./config.js";
export { RunHandle } from "./runs.js";
export { runIsTerminal, runSucceeded } from "./runs.js";
export { ExtractOptions, ProxyRegion, SchemaOptions } from "./options.js";
export { WorkflowEvent, parseEvent, terminalState } from "./events.js";
export { SSEDecoder } from "./sse.js";

export {
  MakraAPIError,
  MakraAuthenticationError,
  MakraConnectionError,
  MakraError,
  MakraInsufficientCreditsError,
  MakraInvalidRequestError,
  MakraNotFoundError,
  MakraPermissionError,
  MakraRateLimitError,
  MakraResultError,
  MakraRunFailedError,
  MakraServerError,
  MakraStreamError,
  MakraTimeoutError,
} from "./errors.js";

export {
  DEFAULT_MAX_RETRIES,
  DEFAULT_TIMEOUT_MS,
  DEVELOPMENT_BASE_URL,
  DUMMY_API_KEY,
  ErrorCodes,
  EventTypes,
  ExecutionModes,
  Features,
  PRODUCTION_BASE_URL,
  ProxyContinents,
  ProxyRegionScopes,
  RunStates,
  SDK_VERSION,
  StreamDetailTypes,
  ValidationModes,
} from "./constants.js";
export { Iso3166Alpha2, ISO_3166_ALPHA2_CODES } from "./iso3166.js";
