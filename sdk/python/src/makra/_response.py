"""Response decoding, shared by the synchronous and asynchronous clients."""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from ._constants import HEADER_REQUEST_ID, HEADER_RETRY_AFTER
from ._errors import MakraAPIError, build_api_error
from ._retry import parse_retry_after


def decode_body(status_code: int, content_type: str, text: str) -> Any:
    """Decode a response body without ever discarding what the server sent.

    JSON is parsed, anything else is returned as text, and a body that claims
    to be JSON but is not falls back to its text rather than raising.
    """
    if status_code == 204 or not text:
        return None
    if "json" in content_type.lower():
        try:
            return json.loads(text)
        except ValueError:
            return text
    return text


def api_error(
    *,
    status_code: int,
    headers: Mapping[str, str],
    body: Any,
    method: str,
    path: str,
) -> MakraAPIError:
    return build_api_error(
        status_code=status_code,
        body=body,
        method=method,
        path=path,
        request_id=_header(headers, HEADER_REQUEST_ID),
        retry_after=parse_retry_after(_header(headers, HEADER_RETRY_AFTER)),
    )


def _header(headers: Mapping[str, str], name: str) -> Optional[str]:
    # httpx headers are case-insensitive; a plain dict from a test fixture may
    # not be, so fall back to a lowercase lookup.
    value = headers.get(name)
    if value is None:
        value = headers.get(name.lower())
    return value
