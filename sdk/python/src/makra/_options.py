"""Ergonomic builders for workflow ``config`` objects.

``ExtractOptions`` and ``SchemaOptions`` hide the nested wire shape. They
convert to ordinary dictionaries; request construction then runs the same
normalization and validation used for caller-supplied mappings. Unset fields
are omitted so deployment defaults stay in effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ._constants import ProxyRegionScopes
from ._types import (
    CrawlerConfig,
    CrawlerRecoveryConfig,
    ExtractConfig,
    PaginationConfig,
    ProxyContinent,
    ProxyRegionConfig,
    ProxyRegionScope,
    SchemaConfig,
    ValidationMode,
)


@dataclass(frozen=True)
class ProxyRegion:
    """Proxy egress region: worldwide, a continent slug, or an ISO country."""

    scope: ProxyRegionScope
    value: Optional[str] = None

    @classmethod
    def worldwide(cls) -> "ProxyRegion":
        return cls(scope=ProxyRegionScopes.WORLDWIDE)

    @classmethod
    def continent(cls, value: ProxyContinent) -> "ProxyRegion":
        return cls(scope=ProxyRegionScopes.CONTINENT, value=value)

    @classmethod
    def country(cls, value: str) -> "ProxyRegion":
        return cls(scope=ProxyRegionScopes.COUNTRY, value=value)

    def to_dict(self) -> ProxyRegionConfig:
        region: ProxyRegionConfig = {"scope": self.scope}
        if self.value is not None:
            region["value"] = self.value
        return region


@dataclass(frozen=True)
class BaseOptions:
    """Crawler and recovery fields shared by extract and schema options."""

    post_ready_wait_ms: Optional[int] = None
    proxy_region: Optional[ProxyRegion] = None
    recovery_retry: Optional[bool] = None
    recovery_retry_delay_ms: Optional[int] = None

    def _common_config(self) -> SchemaConfig:
        crawler: CrawlerConfig = {}
        if self.post_ready_wait_ms is not None:
            crawler["post_ready_wait_ms"] = self.post_ready_wait_ms
        if self.proxy_region is not None:
            crawler["proxy"] = {"region": self.proxy_region.to_dict()}
        recovery: CrawlerRecoveryConfig = {}
        if self.recovery_retry is not None:
            recovery["retry"] = self.recovery_retry
        if self.recovery_retry_delay_ms is not None:
            recovery["retry_delay_ms"] = self.recovery_retry_delay_ms
        if recovery:
            crawler["recovery"] = recovery
        if not crawler:
            return {}
        return {"crawler": crawler}

    def to_config(self) -> SchemaConfig:
        return self._common_config()


@dataclass(frozen=True)
class SchemaOptions(BaseOptions):
    """Request-overridable config for the schema workflow."""


@dataclass(frozen=True)
class ExtractOptions(BaseOptions):
    """Extract workflow config, including extract-only controls.

    ``additional_pages=None`` leaves pagination unspecified. Setting
    ``additional_pages`` without ``pagination_enabled`` enables pagination.
    ``additional_pages=0`` with that implied enablement is an explicit
    enabled-with-zero-extra-pages request, distinct from omitting pagination.
    """

    validation_mode: Optional[ValidationMode] = None
    additional_pages: Optional[int] = None
    pagination_enabled: Optional[bool] = None
    title_enabled: Optional[bool] = None

    def to_config(self) -> ExtractConfig:
        config: ExtractConfig = {}
        crawler = self._common_config().get("crawler")
        if crawler is not None:
            config["crawler"] = crawler
        if self.validation_mode is not None:
            config["validation_mode"] = self.validation_mode
        if self.pagination_enabled is not None or self.additional_pages is not None:
            pagination: PaginationConfig = {}
            if self.pagination_enabled is not None:
                pagination["enabled"] = self.pagination_enabled
            else:
                pagination["enabled"] = True
            if self.additional_pages is not None:
                pagination["additional_pages"] = self.additional_pages
            config["pagination"] = pagination
        if self.title_enabled is not None:
            config["title"] = {"enabled": self.title_enabled}
        return config


__all__ = [
    "BaseOptions",
    "ExtractOptions",
    "ProxyRegion",
    "SchemaOptions",
]
