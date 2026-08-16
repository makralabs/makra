"""Request validation and payload construction.

Every check here happens before any network I/O, so a malformed call fails
locally with a `ValueError` instead of spending a round trip to learn the same
thing. Only the rules the API itself enforces are duplicated — the SDK never
invents constraints of its own.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ._constants import (
    EXECUTION_MODES,
    PROXY_REGION_SCOPES,
    SELECTOR_CHAIN_VERSIONS,
    VALIDATION_MODES,
)
from ._types import ExtractConfig, JsonSchema, SchemaConfig


def build_extract_payload(
    urls: Sequence[str],
    schema: JsonSchema,
    *,
    execution_mode: str,
    config: Optional[ExtractConfig],
    stream: bool = False,
) -> Dict[str, Any]:
    """Build the ``POST /workflows/extract`` body."""
    payload: Dict[str, Any] = {
        "urls": _validated_urls(urls),
        "schema": _validated_schema(schema),
        "execution_mode": _validated_choice(
            "execution_mode", execution_mode, EXECUTION_MODES
        ),
        "config": _validated_extract_config(config),
    }
    if stream:
        payload["stream"] = True
    return payload


def build_schema_payload(
    url: str,
    *,
    only_memoized: bool,
    config: Optional[SchemaConfig],
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
        "config": _validated_common_config(config, path="config"),
    }
    if stream:
        payload["stream"] = True
    return payload


def new_idempotency_key() -> str:
    """A fresh key so a retried submission replays instead of double-billing."""
    return "makra-sdk-" + uuid.uuid4().hex


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


def _validated_extract_config(config: Optional[ExtractConfig]) -> Dict[str, Any]:
    resolved = _validated_common_config(config, path="config")
    mode = resolved.get("validation_mode", _MISSING)
    if mode is not _MISSING and mode is not None:
        _validated_choice("config.validation_mode", mode, VALIDATION_MODES)
    _validate_flags(resolved.get("audit"), "config.audit", ("enabled", "use_cache"))
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
    _validate_memory(resolved.get("memory"))
    _validate_crawler(resolved.get("crawler"))
    return resolved


def _validate_memory(memory: Any) -> None:
    if memory is None:
        return
    _require_mapping(memory, "config.memory")
    version = memory.get("selector_chain_version")
    if version is not None:
        _validated_choice(
            "config.memory.selector_chain_version", version, SELECTOR_CHAIN_VERSIONS
        )
    _validate_flags(memory, "config.memory", ("enabled",))


def _validate_crawler(crawler: Any) -> None:
    if crawler is None:
        return
    _require_mapping(crawler, "config.crawler")
    _validate_bounded_ms(
        crawler.get("post_ready_wait_ms"), "config.crawler.post_ready_wait_ms", 120_000
    )
    recovery = crawler.get("recovery")
    if recovery is not None:
        _require_mapping(recovery, "config.crawler.recovery")
        _validate_flags(recovery, "config.crawler.recovery", ("one_last_retry",))
        _validate_bounded_ms(
            recovery.get("one_last_retry_delay_ms"),
            "config.crawler.recovery.one_last_retry_delay_ms",
            300_000,
        )
    proxy = crawler.get("proxy")
    if proxy is None:
        return
    _require_mapping(proxy, "config.crawler.proxy")
    region = proxy.get("region")
    if region is None:
        return
    _require_mapping(region, "config.crawler.proxy.region")
    scope = region.get("scope")
    if scope is not None:
        _validated_choice(
            "config.crawler.proxy.region.scope", scope, PROXY_REGION_SCOPES
        )
    value = region.get("value")
    if value is not None and not isinstance(value, str):
        raise ValueError("config.crawler.proxy.region.value must be a string or None")


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


def _validated_choice(name: str, value: Any, allowed: "frozenset[str]") -> str:
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
