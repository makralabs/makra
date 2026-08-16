"""Makra Python SDK.

Structured web data extraction, in three shapes:

    from makra import Makra

    with Makra("mk_live_...") as makra:
        # 1. Blocking REST — simplest, one call in, one result out.
        data = makra.extract(["https://example.com"], {"title": "string"})

        # 2. Streaming — watch a run happen, then read the stored result.
        for event in makra.extract_stream(["https://example.com"], schema):
            print(event.type, event.detail_type)
        data = makra.get_run_result(event.run_id)

        # 3. Deferred — submit now, collect later from anywhere.
        run = makra.submit_extract(["https://example.com"], schema)
        run.wait()
        data = run.result()

Everything above exists on ``AsyncMakra`` too, with ``await``.
"""

from ._client import AsyncMakra, Makra
from ._config import ClientConfig, resolve_config
from ._constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    DEVELOPMENT_BASE_URL,
    PRODUCTION_BASE_URL,
    SDK_VERSION,
    ErrorCodes,
    EventTypes,
    ExecutionModes,
    Features,
    ProxyRegionScopes,
    RunStates,
    SelectorChainVersions,
    ValidationModes,
)
from ._errors import (
    MakraAPIError,
    MakraAuthenticationError,
    MakraConnectionError,
    MakraError,
    MakraInsufficientCreditsError,
    MakraInvalidRequestError,
    MakraNotFoundError,
    MakraPermissionError,
    MakraRateLimitError,
    MakraRunFailedError,
    MakraServerError,
    MakraStreamError,
    MakraTimeoutError,
)
from ._events import WorkflowEvent
from ._runs import AsyncRunHandle, RunHandle
from ._types import (
    AsyncAdmission,
    AuditConfig,
    CommonConfig,
    CrawlerConfig,
    CrawlerRecoveryConfig,
    ExecutionMode,
    ExtractConfig,
    Feature,
    JsonSchema,
    MemoryConfig,
    PaginationConfig,
    ProxyConfig,
    ProxyRegionConfig,
    ProxyRegionScope,
    RunPage,
    RunState,
    RunView,
    SchemaConfig,
    SelectorChainVersion,
    TitleConfig,
    ValidationMode,
)

__version__ = SDK_VERSION

__all__ = [
    # Clients
    "Makra",
    "AsyncMakra",
    "ClientConfig",
    "resolve_config",
    # Runs and events
    "RunHandle",
    "AsyncRunHandle",
    "WorkflowEvent",
    # Errors
    "MakraError",
    "MakraAPIError",
    "MakraAuthenticationError",
    "MakraPermissionError",
    "MakraNotFoundError",
    "MakraInvalidRequestError",
    "MakraInsufficientCreditsError",
    "MakraRateLimitError",
    "MakraServerError",
    "MakraConnectionError",
    "MakraTimeoutError",
    "MakraStreamError",
    "MakraRunFailedError",
    # Constants
    "SDK_VERSION",
    "PRODUCTION_BASE_URL",
    "DEVELOPMENT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "ExecutionModes",
    "ValidationModes",
    "SelectorChainVersions",
    "ProxyRegionScopes",
    "Features",
    "RunStates",
    "EventTypes",
    "ErrorCodes",
    # Types
    "JsonSchema",
    "ExecutionMode",
    "ValidationMode",
    "SelectorChainVersion",
    "ProxyRegionScope",
    "Feature",
    "RunState",
    "CommonConfig",
    "ExtractConfig",
    "SchemaConfig",
    "MemoryConfig",
    "CrawlerConfig",
    "CrawlerRecoveryConfig",
    "ProxyConfig",
    "ProxyRegionConfig",
    "AuditConfig",
    "PaginationConfig",
    "TitleConfig",
    "RunView",
    "RunPage",
    "AsyncAdmission",
    "__version__",
]
