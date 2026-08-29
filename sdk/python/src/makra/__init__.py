"""Makra Python SDK.

Structured web data extraction, in three shapes:

    from makra import Makra

    with Makra("mk_live_...") as makra:
        # 1. Convenient — durable submission, one call in, one result out.
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
    DUMMY_API_KEY,
    PRODUCTION_BASE_URL,
    SDK_VERSION,
    ErrorCodes,
    EventTypes,
    ExecutionModes,
    Features,
    ProxyContinents,
    ProxyRegionScopes,
    RunStates,
    StreamDetailTypes,
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
    MakraResultError,
    MakraRunFailedError,
    MakraServerError,
    MakraStreamError,
    MakraTimeoutError,
)
from ._events import WorkflowEvent
from ._iso3166 import ISO_3166_ALPHA2_CODES, Iso3166Alpha2
from ._options import ExtractOptions, ProxyRegion, SchemaOptions
from ._runs import AsyncRunHandle, RunHandle, run_is_terminal, run_succeeded
from ._types import (
    AsyncAdmission,
    CommonConfig,
    CrawlerConfig,
    CrawlerRecoveryConfig,
    ExecutionMode,
    ExtractConfig,
    ExtractResponse,
    Feature,
    HealthResponse,
    JsonSchema,
    PaginationConfig,
    ProxyConfig,
    ProxyContinent,
    ProxyRegionConfig,
    ProxyRegionScope,
    ResponseBody,
    RunPage,
    RunResult,
    RunState,
    RunView,
    SchemaConfig,
    SchemaResponse,
    TitleConfig,
    ValidationMode,
    WorkflowEnvelope,
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
    "run_is_terminal",
    "run_succeeded",
    # Options
    "ExtractOptions",
    "SchemaOptions",
    "ProxyRegion",
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
    "MakraResultError",
    "MakraRunFailedError",
    # Constants
    "SDK_VERSION",
    "PRODUCTION_BASE_URL",
    "DEVELOPMENT_BASE_URL",
    "DUMMY_API_KEY",
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "ExecutionModes",
    "ValidationModes",
    "Iso3166Alpha2",
    "ISO_3166_ALPHA2_CODES",
    "ProxyRegionScopes",
    "ProxyContinents",
    "Features",
    "RunStates",
    "EventTypes",
    "StreamDetailTypes",
    "ErrorCodes",
    # Types
    "JsonSchema",
    "ExecutionMode",
    "ValidationMode",
    "ProxyRegionScope",
    "ProxyContinent",
    "Feature",
    "RunState",
    "ResponseBody",
    "HealthResponse",
    "WorkflowEnvelope",
    "ExtractResponse",
    "SchemaResponse",
    "RunResult",
    "CommonConfig",
    "ExtractConfig",
    "SchemaConfig",
    "CrawlerConfig",
    "CrawlerRecoveryConfig",
    "ProxyConfig",
    "ProxyRegionConfig",
    "PaginationConfig",
    "TitleConfig",
    "RunView",
    "RunPage",
    "AsyncAdmission",
    "__version__",
]
