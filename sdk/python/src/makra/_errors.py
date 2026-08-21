"""Exception hierarchy for the Makra SDK.

Callers can catch the base :class:`MakraError` for anything the SDK raises, or
a specific subclass to branch on a condition worth handling — a missing key, an
empty balance, a rate limit. Every HTTP failure carries the decoded body so no
information is lost behind the exception type. Result-retrieval contract
failures raise :class:`MakraResultError`, a temporary subclass of
:class:`MakraStreamError` so existing stream catches still work.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

from ._constants import ErrorCodes


class MakraError(Exception):
    """Base class for all errors raised by the Makra SDK."""


class MakraAPIError(MakraError):
    """An HTTP error response returned by the Makra API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        body: Any,
        method: str,
        path: str,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body
        self.method = method
        self.path = path
        self.code = code
        self.request_id = request_id


class MakraAuthenticationError(MakraAPIError):
    """The API key or session token is missing, invalid, revoked, or expired."""


class MakraPermissionError(MakraAPIError):
    """The credential is valid but lacks the required workflow permission."""


class MakraNotFoundError(MakraAPIError):
    """The run or result does not exist, or belongs to another principal."""


class MakraInvalidRequestError(MakraAPIError):
    """The request was rejected before execution.

    ``field`` and ``reason`` are populated for contract and URL-admission
    failures, which name the offending part of the request without echoing it.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        detail = _error_detail(self.body)
        self.field = detail.get("field")
        self.reason = detail.get("reason")
        self.index = detail.get("index")


class MakraInsufficientCreditsError(MakraAPIError):
    """The account balance cannot cover the workflow's credit hold."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        detail = _error_detail(self.body)
        self.required_credits = detail.get("required_credits")
        self.available_credits = detail.get("available_credits")


class MakraRateLimitError(MakraAPIError):
    """Too many requests, or too many workflow runs active at once."""

    def __init__(
        self, message: str, *, retry_after: Optional[float] = None, **kwargs: Any
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.concurrency = _error_detail(self.body).get("concurrency")


class MakraServerError(MakraAPIError):
    """The API, or an upstream service it depends on, failed."""


class MakraConnectionError(MakraError):
    """The request could not reach the Makra API."""

    def __init__(
        self, message: str, *, method: str = "", path: str = ""
    ) -> None:
        super().__init__(message)
        self.message = message
        self.method = method
        self.path = path


class MakraTimeoutError(MakraConnectionError):
    """The request or an event stream exceeded its configured timeout."""


class MakraStreamError(MakraError):
    """An event stream ended before a terminal event and could not resume."""

    def __init__(self, message: str, *, run_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.run_id = run_id


class MakraResultError(MakraStreamError):
    """A stored-result redirect or download contract failed.

    Temporarily a ``MakraStreamError`` subclass so existing ``except
    MakraStreamError`` handlers still catch result-retrieval failures. A
    future major version may reparent this class directly under
    ``MakraError``.
    """

    def __init__(
        self,
        message: str,
        *,
        run_id: Optional[str] = None,
        location: Optional[str] = None,
    ) -> None:
        super().__init__(message, run_id=run_id)
        self.location = location


class MakraRunFailedError(MakraError):
    """A run reached a terminal state other than ``completed``."""

    def __init__(self, message: str, *, run_id: str, state: str, run: Any) -> None:
        super().__init__(message)
        self.message = message
        self.run_id = run_id
        self.state = state
        self.run = run


_STATUS_ERRORS: Tuple[Tuple[int, type], ...] = (
    (401, MakraAuthenticationError),
    (402, MakraInsufficientCreditsError),
    (403, MakraPermissionError),
    (404, MakraNotFoundError),
    (429, MakraRateLimitError),
)


def _error_detail(body: Any) -> Mapping[str, Any]:
    """Return the structured ``{"error": {...}}`` object, or an empty mapping."""
    if isinstance(body, Mapping):
        error = body.get("error")
        if isinstance(error, Mapping):
            return error
    return {}


def error_code(body: Any) -> Optional[str]:
    code = _error_detail(body).get("code")
    return code if isinstance(code, str) and code else None


def error_message(body: Any, fallback: str) -> str:
    """Pick the most specific human-readable message the body offers.

    The API has several error envelopes: a structured ``{"error": {...}}``
    object, a flat ``{"error": "..."}`` string, and the FastAPI ``detail`` form
    that Morpheus responses pass through.
    """
    detail = _error_detail(body)
    message = detail.get("message")
    if isinstance(message, str) and message:
        return message
    if isinstance(body, Mapping):
        for field in ("message", "detail", "error"):
            value = body.get(field)
            if isinstance(value, str) and value:
                return value
    if isinstance(body, str) and body:
        return body
    return fallback


def build_api_error(
    *,
    status_code: int,
    body: Any,
    method: str,
    path: str,
    request_id: Optional[str] = None,
    retry_after: Optional[float] = None,
) -> MakraAPIError:
    """Map an HTTP error response onto the most specific SDK exception."""
    message = error_message(
        body, "Makra API returned HTTP {}".format(status_code)
    )
    code = error_code(body)
    kwargs: Dict[str, Any] = {
        "status_code": status_code,
        "body": body,
        "method": method,
        "path": path,
        "code": code,
        "request_id": request_id,
    }
    if status_code == 429 or code == ErrorCodes.TOO_MANY_CONCURRENT_RUNS:
        return MakraRateLimitError(message, retry_after=retry_after, **kwargs)
    for status, error_class in _STATUS_ERRORS:
        if status_code == status:
            return error_class(message, **kwargs)
    if status_code >= 500:
        return MakraServerError(message, **kwargs)
    if status_code >= 400:
        return MakraInvalidRequestError(message, **kwargs)
    return MakraAPIError(message, **kwargs)
