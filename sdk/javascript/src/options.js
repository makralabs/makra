/** Ergonomic builders for workflow configuration objects. */

import { ProxyRegionScopes } from "./constants.js";

export class ProxyRegion {
  constructor(scope, value = null) {
    this.scope = scope;
    this.value = value;
    Object.freeze(this);
  }

  static worldwide() {
    return new ProxyRegion(ProxyRegionScopes.WORLDWIDE);
  }

  static continent(value) {
    return new ProxyRegion(ProxyRegionScopes.CONTINENT, value);
  }

  static country(value) {
    return new ProxyRegion(ProxyRegionScopes.COUNTRY, value);
  }

  toConfig() {
    return this.value == null ? { scope: this.scope } : { scope: this.scope, value: this.value };
  }
}

class BaseOptions {
  constructor({ postReadyWaitMs, proxyRegion, recoveryRetry, recoveryRetryDelayMs } = {}) {
    this.postReadyWaitMs = postReadyWaitMs;
    this.proxyRegion = proxyRegion;
    this.recoveryRetry = recoveryRetry;
    this.recoveryRetryDelayMs = recoveryRetryDelayMs;
  }

  commonConfig() {
    const crawler = {};
    if (this.postReadyWaitMs != null) crawler.post_ready_wait_ms = this.postReadyWaitMs;
    if (this.proxyRegion != null) crawler.proxy = { region: this.proxyRegion.toConfig() };
    const recovery = {};
    if (this.recoveryRetry != null) recovery.retry = this.recoveryRetry;
    if (this.recoveryRetryDelayMs != null) {
      recovery.retry_delay_ms = this.recoveryRetryDelayMs;
    }
    if (Object.keys(recovery).length > 0) crawler.recovery = recovery;
    return Object.keys(crawler).length > 0 ? { crawler } : {};
  }

  toConfig() {
    return this.commonConfig();
  }
}

export class SchemaOptions extends BaseOptions {
  constructor(options = {}) {
    super(options);
    Object.freeze(this);
  }
}

export class ExtractOptions extends BaseOptions {
  constructor({ validationMode, additionalPages, paginationEnabled, titleEnabled, ...common } = {}) {
    super(common);
    this.validationMode = validationMode;
    this.additionalPages = additionalPages;
    this.paginationEnabled = paginationEnabled;
    this.titleEnabled = titleEnabled;
    Object.freeze(this);
  }

  toConfig() {
    const config = this.commonConfig();
    if (this.validationMode != null) config.validation_mode = this.validationMode;
    if (this.paginationEnabled != null || this.additionalPages != null) {
      config.pagination = {
        enabled: this.paginationEnabled == null ? true : this.paginationEnabled,
      };
      if (this.additionalPages != null) {
        config.pagination.additional_pages = this.additionalPages;
      }
    }
    if (this.titleEnabled != null) config.title = { enabled: this.titleEnabled };
    return config;
  }
}

export function isConfigOptions(value) {
  return value instanceof BaseOptions;
}
