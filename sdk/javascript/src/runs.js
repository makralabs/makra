/**
 * Handle for an asynchronously submitted workflow run.
 *
 * A handle is the small, ergonomic object returned by `submitExtract` and
 * `submitSchema`. It remembers the run id so the caller does not have to
 * thread it through every follow-up call.
 */
export class RunHandle {
  constructor(client, admission) {
    this.id = admission.run_id ?? "";
    this.feature = admission.feature;
    this.state = admission.state;
    this.statusUrl = admission.status_url;
    this.eventsUrl = admission.events_url;
    this.resultUrl = admission.result_url;
    this.admission = admission;
    this.client = client;
  }

  /** Fetch current run metadata and update the cached state. */
  async refresh() {
    return this.#track(await this.client.getRun(this.id));
  }

  /**
   * Poll until the run reaches a terminal state.
   *
   * Prefer `stream()` when you want live progress; polling exists for
   * reconciliation and for callers that cannot hold a connection open.
   */
  async wait(options) {
    return this.#track(await this.client.waitForRun(this.id, options));
  }

  /** Attach to the run's live event stream. */
  stream(options) {
    return this.client.streamRunEvents(this.id, options);
  }

  /** Download the stored result payload. */
  async result() {
    return this.client.getRunResult(this.id);
  }

  /** Request cancellation. Idempotent; a terminal run is returned as-is. */
  async cancel() {
    return this.#track(await this.client.cancelRun(this.id));
  }

  #track(run) {
    this.state = run?.state ?? this.state;
    return run;
  }
}
