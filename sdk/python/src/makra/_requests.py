"""Request validation and payload construction.

Every check here happens before any network I/O, so a malformed call fails
locally with a `ValueError` instead of spending a round trip to learn the same
thing. Only the rules the API itself enforces are duplicated — the SDK never
invents constraints of its own.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Union

from ._constants import (
    EXECUTION_MODES,
    FEATURES,
    LIST_RUNS_MAX_LIMIT,
    LIST_RUNS_MIN_LIMIT,
    PROXY_CONTINENTS,
    PROXY_REGION_SCOPES,
    RUN_STATES,
    VALIDATION_MODES,
    ExecutionModes,
    ProxyRegionScopes,
)
from ._iso3166 import ISO_3166_ALPHA2_CODES
from ._options import ExtractOptions, SchemaOptions
from ._types import ExtractConfig, JsonSchema, SchemaConfig

ExtractConfigInput = Union[ExtractConfig, ExtractOptions]
SchemaConfigInput = Union[SchemaConfig, SchemaOptions]

# Keys the contract removed from the public config object. Unknown keys that
# are not in these sets are forwarded so future server flags can be used
# before an SDK release.
REMOVED_COMMON_CONFIG_KEYS: FrozenSet[str] = frozenset(
    {"memory", "selector_chain_version"}
)
REMOVED_EXTRACT_CONFIG_KEYS: FrozenSet[str] = frozenset({"audit"})


def build_extract_payload(
    urls: Sequence[str],
    schema: JsonSchema,
    *,
    execution_mode: str,
    config: Optional[ExtractConfigInput],
    stream: bool = False,
) -> Dict[str, Any]:
    """Build the ``POST /workflows/extract`` body."""
    payload: Dict[str, Any] = {
        "urls": _validated_urls(urls),
        "schema": _validated_schema(schema),
        "execution_mode": _validated_choice(
            "execution_mode", execution_mode, EXECUTION_MODES
        ),
        "config": _validated_extract_config(_as_config_mapping(config)),
    }
    if stream:
        payload["stream"] = True
    return payload


def build_schema_payload(
    url: str,
    *,
    only_memoized: bool,
    config: Optional[SchemaConfigInput],
    stream: bool = False,
) -> Dict[str, Any]:
    """Build the ``POST /workflows/schema`` body."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")
    if not isinstance(only_memoized, bool):
        raise ValueError("only_memoized must be a boolean")
    payload: Dict[str, Any] = {
        "url": url,
        "only_memoized": only_memoized,
        "config": _validated_common_config(
            _as_config_mapping(config), path="config"
        ),
    }
    if stream:
        payload["stream"] = True
    return payload


def new_idempotency_key() -> str:
    """A fresh key so a retried submission replays instead of double-billing."""
    return "makra-sdk-" + uuid.uuid4().hex


def resolve_workflow_timeout(
    explicit: Optional[float],
    base: float,
    *,
    config: Optional[Mapping[str, Any]] = None,
    url_count: int = 1,
    execution_mode: str = ExecutionModes.CONCURRENT,
) -> float:
    """Resolve how long a workflow request may occupy the connection.

    An explicit timeout always wins. Otherwise the client default is treated
    as a *per-page* budget: pagination adds one unit per additional page, and
    sequential multi-URL extracts multiply by the URL count. Concurrent URLs
    share wall-clock, so they do not multiply the budget.
    """
    if explicit is not None:
        return require_positive_number("timeout", explicit)
    pages = 1
    pagination = config.get("pagination") if isinstance(config, Mapping) else None
    if isinstance(pagination, Mapping) and pagination.get("enabled"):
        extra = pagination.get("additional_pages") or 0
        if isinstance(extra, int) and not isinstance(extra, bool) and extra > 0:
            pages = 1 + extra
    urls = (
        url_count
        if execution_mode == ExecutionModes.SEQUENTIAL and url_count > 0
        else 1
    )
    return base * pages * urls


def validate_optional_timeout(timeout: Optional[float]) -> Optional[float]:
    if timeout is None:
        return None
    return require_positive_number("timeout", timeout)


def validate_optional_poll_interval(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return require_positive_number("poll_interval", value)


def validate_last_event_id(value: object) -> int:
    return require_non_negative_int("last_event_id", value)


def validate_run_id(run_id: object) -> str:
    return require_non_empty_string("run_id", run_id)


def validate_idempotency_key(key: Optional[str]) -> Optional[str]:
    if key is None:
        return None
    return require_non_empty_string("idempotency_key", key)


def validate_list_runs_args(
    limit: Optional[int],
    cursor: Optional[str],
    feature: Optional[str],
    state: Optional[str],
) -> None:
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be an integer")
        if not LIST_RUNS_MIN_LIMIT <= limit <= LIST_RUNS_MAX_LIMIT:
            raise ValueError(
                "limit must be between {} and {}".format(
                    LIST_RUNS_MIN_LIMIT, LIST_RUNS_MAX_LIMIT
                )
            )
    if cursor is not None and not isinstance(cursor, str):
        raise ValueError("cursor must be a string")
    if feature is not None:
        _validated_choice("feature", feature, FEATURES)
    if state is not None:
        _validated_choice("state", state, RUN_STATES)


def require_positive_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} must be a number".format(name))
    number = float(value)
    if number <= 0:
        raise ValueError("{} must be greater than 0".format(name))
    return number


def require_non_negative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("{} must be an integer".format(name))
    if value < 0:
        raise ValueError("{} must not be negative".format(name))
    return value


def require_non_empty_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("{} must be a non-empty string".format(name))
    return value


def _as_config_mapping(
    config: Optional[Union[Mapping[str, Any], SchemaOptions, ExtractOptions]],
) -> Optional[Mapping[str, Any]]:
    if config is None:
        return None
    if isinstance(config, (ExtractOptions, SchemaOptions)):
        return config.to_config()
    return config


def _validated_urls(urls: Sequence[str]) -> List[str]:
    if isinstance(urls, str) or not isinstance(urls, Sequence):
        raise ValueError("urls must be a list of URL strings")
    if not urls:
        raise ValueError("urls must contain at least one URL")
    for url in urls:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("each URL must be a non-empty string")
    return list(urls)


def _validated_schema(schema: JsonSchema) -> JsonSchema:
    if not isinstance(schema, (Mapping, list)) or not schema:
        raise ValueError("schema must be a non-empty JSON object or array")
    return schema


def _validated_extract_config(config: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    resolved = _validated_common_config(config, path="config")
    _reject_removed_keys(resolved, REMOVED_EXTRACT_CONFIG_KEYS)
    mode = resolved.get("validation_mode", _MISSING)
    if mode is not _MISSING and mode is not None:
        _validated_choice("config.validation_mode", mode, VALIDATION_MODES)
    _validate_pagination(resolved.get("pagination"))
    _validate_flags(resolved.get("title"), "config.title", ("enabled",))
    return resolved


def _validated_common_config(
    config: Optional[Mapping[str, Any]], *, path: str
) -> Dict[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, Mapping):
        raise ValueError("{} must be a mapping".format(path))
    resolved = dict(config)
    _reject_removed_keys(resolved, REMOVED_COMMON_CONFIG_KEYS)
    crawler = resolved.get("crawler")
    if crawler is not None:
        resolved["crawler"] = _normalized_crawler(crawler)
    return resolved


def _reject_removed_keys(config: Mapping[str, Any], keys: FrozenSet[str]) -> None:
    for key in keys:
        if key in config:
            raise ValueError("config.{} is not supported".format(key))


def _normalized_crawler(crawler: Any) -> Dict[str, Any]:
    _require_mapping(crawler, "config.crawler")
    resolved = dict(crawler)
    _validate_bounded_ms(
        resolved.get("post_ready_wait_ms"), "config.crawler.post_ready_wait_ms", 120_000
    )
    recovery = resolved.get("recovery")
    if recovery is not None:
        resolved["recovery"] = _recovery_to_wire(recovery)
    proxy = resolved.get("proxy")
    if proxy is not None:
        resolved["proxy"] = _normalized_proxy(proxy)
    return resolved


def _recovery_to_wire(recovery: Any) -> Dict[str, Any]:
    """Map SDK ``retry`` / ``retry_delay_ms`` onto the API's recovery fields."""
    _require_mapping(recovery, "config.crawler.recovery")
    extra = set(recovery) - {"retry", "retry_delay_ms"}
    if extra:
        raise ValueError(
            "config.crawler.recovery only accepts retry and retry_delay_ms; "
            "unknown keys: {}".format(", ".join(sorted(extra)))
        )
    wire: Dict[str, Any] = {}
    if "retry" in recovery:
        retry = recovery["retry"]
        if retry is not None and not isinstance(retry, bool):
            raise ValueError("config.crawler.recovery.retry must be a boolean")
        if retry is not None:
            wire["one_last_retry"] = retry
    if "retry_delay_ms" in recovery:
        _validate_bounded_ms(
            recovery["retry_delay_ms"],
            "config.crawler.recovery.retry_delay_ms",
            300_000,
        )
        wire["one_last_retry_delay_ms"] = recovery["retry_delay_ms"]
    return wire


def _normalized_proxy(proxy: Any) -> Dict[str, Any]:
    _require_mapping(proxy, "config.crawler.proxy")
    resolved = dict(proxy)
    region = resolved.get("region")
    if region is None:
        return resolved
    resolved["region"] = _normalized_region(region)
    return resolved


def _normalized_region(region: Any) -> Dict[str, Any]:
    _require_mapping(region, "config.crawler.proxy.region")
    resolved = dict(region)
    scope = resolved.get("scope")
    if scope is not None:
        _validated_choice(
            "config.crawler.proxy.region.scope", scope, PROXY_REGION_SCOPES
        )
    value = resolved.get("value")
    if value is not None and not isinstance(value, str):
        raise ValueError("config.crawler.proxy.region.value must be a string or None")
    if scope == ProxyRegionScopes.WORLDWIDE and value is not None:
        raise ValueError(
            "config.crawler.proxy.region.value must be None when scope is worldwide"
        )
    if scope == ProxyRegionScopes.COUNTRY:
        if not value:
            raise ValueError(
                "config.crawler.proxy.region.value is required when scope is country"
            )
        normalized = value.strip().upper()
        if normalized not in ISO_3166_ALPHA2_CODES:
            raise ValueError(
                "config.crawler.proxy.region.value must be an ISO 3166-1 alpha-2 "
                "country code such as Iso3166Alpha2.DE"
            )
        resolved["value"] = normalized
    if scope == ProxyRegionScopes.CONTINENT:
        if not value:
            raise ValueError(
                "config.crawler.proxy.region.value is required when scope is continent"
            )
        normalized = value.strip().lower()
        if normalized not in PROXY_CONTINENTS:
            raise ValueError(
                "config.crawler.proxy.region.value must be a ProxyContinents slug "
                "such as ProxyContinents.EUROPE"
            )
        resolved["value"] = normalized
    return resolved


def _validate_pagination(pagination: Any) -> None:
    if pagination is None:
        return
    _require_mapping(pagination, "config.pagination")
    _validate_flags(pagination, "config.pagination", ("enabled",))
    pages = pagination.get("additional_pages")
    if pages is None:
        return
    if not isinstance(pages, int) or isinstance(pages, bool) or pages < 0:
        raise ValueError(
            "config.pagination.additional_pages must be an integer >= 0"
        )


def _validate_flags(
    container: Any, path: str, names: Sequence[str]
) -> None:
    if container is None:
        return
    _require_mapping(container, path)
    for name in names:
        value = container.get(name)
        if value is not None and not isinstance(value, bool):
            raise ValueError("{}.{} must be a boolean".format(path, name))


def _validate_bounded_ms(value: Any, path: str, maximum: int) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("{} must be an integer or None".format(path))
    if not 0 <= value <= maximum:
        raise ValueError("{} must be between 0 and {}".format(path, maximum))


def _validated_choice(name: str, value: Any, allowed: FrozenSet[str]) -> str:
    if value not in allowed:
        raise ValueError(
            "{} must be one of: {}".format(name, ", ".join(sorted(allowed)))
        )
    return value


def _require_mapping(value: Any, path: str) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("{} must be a mapping".format(path))


class _Missing:
    pass


_MISSING = _Missing()
