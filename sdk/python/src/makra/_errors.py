from typing import Any, Optional


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
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body
        self.method = method
        self.path = path
        self.request_id = request_id


class MakraConnectionError(MakraError):
    """The request could not reach the Makra API."""

    def __init__(self, message: str, *, method: str, path: str) -> None:
        super().__init__(message)
        self.message = message
        self.method = method
        self.path = path
