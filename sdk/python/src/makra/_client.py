import os
from typing import Any, Dict, List, Mapping, Optional, Union
from urllib.parse import urlparse

import httpx

from ._errors import MakraAPIError, MakraConnectionError

PRODUCTION_BASE_URL = "https://api.makralabs.org"
DEVELOPMENT_BASE_URL = "http://localhost:6900"
DUMMY_API_KEY = "makra-development-key"

JsonObject = Mapping[str, Any]
JsonSchema = Union[Mapping[str, Any], List[Any]]


def _resolve_config(
    api_key: Optional[str], base_url: Optional[str], api_version: str
) -> tuple[str, str, str]:
    resolved_api_key = api_key or os.getenv("MAKRA_API_KEY") or DUMMY_API_KEY
    resolved_base_url_value = (
        base_url
        if base_url is not None
        else os.getenv("MAKRA_BASE_URL") or PRODUCTION_BASE_URL
    )
    if not isinstance(resolved_base_url_value, str):
        raise ValueError("base_url must be an absolute HTTP or HTTPS URL")
    resolved_base_url = resolved_base_url_value.rstrip("/")
    parsed_url = urlparse(resolved_base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("base_url must be an absolute HTTP or HTTPS URL")

    if not isinstance(api_version, str):
        raise ValueError("api_version must be a non-empty string")
    resolved_api_version = api_version.strip("/")
    if not resolved_api_version:
        raise ValueError("api_version must not be empty")
    return resolved_api_key, resolved_base_url, resolved_api_version


def _validate_urls(urls: List[str]) -> None:
    if not urls:
        raise ValueError("urls must contain at least one URL")
    if any(not isinstance(url, str) or not url.strip() for url in urls):
        raise ValueError("each URL must be a non-empty string")


def _error_message(body: Any, fallback: str) -> str:
    if isinstance(body, dict):
        for field in ("message", "detail", "error"):
            value = body.get(field)
            if isinstance(value, str) and value:
                return value
    if isinstance(body, str) and body:
        return body
    return fallback


def _decode_response(response: httpx.Response) -> Any:
    if response.status_code == 204 or not response.content:
        return None
    content_type = response.headers.get("content-type", "").lower()
    if "json" in content_type:
        try:
            return response.json()
        except ValueError:
            pass
    return response.text


class _Endpoints:
    _api_version: str

    def _versioned_path(self, endpoint: str) -> str:
        return f"/api/{self._api_version}/{endpoint}"

    @staticmethod
    def _extract_payload(
        urls: List[str],
        output_schema: JsonSchema,
        actions: Optional[List[str]],
        config: Optional[JsonObject],
    ) -> Dict[str, Any]:
        _validate_urls(urls)
        if not isinstance(output_schema, (Mapping, list)) or not output_schema:
            raise ValueError("output_schema must be a non-empty JSON object or array")
        return {
            "urls": urls,
            "output_schema": output_schema,
            "actions": actions or [],
            "config": dict(config or {}),
        }

    @staticmethod
    def _preprocess_payload(
        urls: List[str], options: Optional[JsonObject]
    ) -> Dict[str, Any]:
        _validate_urls(urls)
        return {"urls": urls, "options": dict(options or {})}

    @staticmethod
    def _page_schema_payload(
        urls: List[str],
        output_type: str,
        debug_mode: bool,
        debug_output_type: str,
    ) -> Dict[str, Any]:
        _validate_urls(urls)
        if output_type not in {"json", "text"}:
            raise ValueError("output_type must be 'json' or 'text'")
        return {
            "urls": urls,
            "output_type": output_type,
            "debug_mode": debug_mode,
            "debug_output_type": debug_output_type,
        }


class Makra(_Endpoints):
    """Synchronous client for the Makra API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        api_version: str = "v1",
        timeout: float = 120.0,
    ) -> None:
        api_key, base_url, self._api_version = _resolve_config(
            api_key, base_url, api_version
        )
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._http = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, text/markdown",
                "User-Agent": "makra-python/0.1.0",
            },
        )

    def __enter__(self) -> "Makra":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def ping(self) -> Any:
        return self._request("GET", "/ping")

    def extract(
        self,
        urls: List[str],
        output_schema: JsonSchema,
        *,
        actions: Optional[List[str]] = None,
        config: Optional[JsonObject] = None,
    ) -> Any:
        payload = self._extract_payload(urls, output_schema, actions, config)
        return self._request("POST", self._versioned_path("extract"), json=payload)

    def preprocess(
        self, urls: List[str], *, options: Optional[JsonObject] = None
    ) -> Any:
        payload = self._preprocess_payload(urls, options)
        return self._request("POST", self._versioned_path("preprocess"), json=payload)

    def page_schema(
        self,
        urls: List[str],
        *,
        output_type: str = "json",
        debug_mode: bool = False,
        debug_output_type: str = "text",
    ) -> Any:
        payload = self._page_schema_payload(
            urls, output_type, debug_mode, debug_output_type
        )
        return self._request(
            "POST", self._versioned_path("page-schema"), json=payload
        )

    def format_markdown(self, url: str) -> str:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        result = self._request(
            "POST",
            "/api/v0/format-markdown",
            expected_content_type="text/",
            json={"url": url},
        )
        if not isinstance(result, str):
            raise MakraConnectionError(
                "Expected a text response from the Makra API",
                method="POST",
                path="/api/v0/format-markdown",
            )
        return result

    def _request(
        self,
        method: str,
        path: str,
        *,
        expected_content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise MakraConnectionError(
                f"Could not connect to the Makra API: {error}",
                method=method,
                path=path,
            ) from error
        return _handle_response(
            response,
            method,
            path,
            expected_content_type=expected_content_type,
        )


class AsyncMakra(_Endpoints):
    """Asynchronous client for the Makra API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        api_version: str = "v1",
        timeout: float = 120.0,
    ) -> None:
        api_key, base_url, self._api_version = _resolve_config(
            api_key, base_url, api_version
        )
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, text/markdown",
                "User-Agent": "makra-python/0.1.0",
            },
        )

    async def __aenter__(self) -> "AsyncMakra":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    async def ping(self) -> Any:
        return await self._request("GET", "/ping")

    async def extract(
        self,
        urls: List[str],
        output_schema: JsonSchema,
        *,
        actions: Optional[List[str]] = None,
        config: Optional[JsonObject] = None,
    ) -> Any:
        payload = self._extract_payload(urls, output_schema, actions, config)
        return await self._request(
            "POST", self._versioned_path("extract"), json=payload
        )

    async def preprocess(
        self, urls: List[str], *, options: Optional[JsonObject] = None
    ) -> Any:
        payload = self._preprocess_payload(urls, options)
        return await self._request(
            "POST", self._versioned_path("preprocess"), json=payload
        )

    async def page_schema(
        self,
        urls: List[str],
        *,
        output_type: str = "json",
        debug_mode: bool = False,
        debug_output_type: str = "text",
    ) -> Any:
        payload = self._page_schema_payload(
            urls, output_type, debug_mode, debug_output_type
        )
        return await self._request(
            "POST", self._versioned_path("page-schema"), json=payload
        )

    async def format_markdown(self, url: str) -> str:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        path = "/api/v0/format-markdown"
        result = await self._request(
            "POST", path, expected_content_type="text/", json={"url": url}
        )
        if not isinstance(result, str):
            raise MakraConnectionError(
                "Expected a text response from the Makra API",
                method="POST",
                path=path,
            )
        return result

    async def _request(
        self,
        method: str,
        path: str,
        *,
        expected_content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise MakraConnectionError(
                f"Could not connect to the Makra API: {error}",
                method=method,
                path=path,
            ) from error
        return _handle_response(
            response,
            method,
            path,
            expected_content_type=expected_content_type,
        )


def _handle_response(
    response: httpx.Response,
    method: str,
    path: str,
    *,
    expected_content_type: Optional[str] = None,
) -> Any:
    body = _decode_response(response)
    if response.is_error:
        message = _error_message(body, f"Makra API returned HTTP {response.status_code}")
        raise MakraAPIError(
            message,
            status_code=response.status_code,
            body=body,
            method=method,
            path=path,
            request_id=response.headers.get("x-request-id"),
        )
    content_type = response.headers.get("content-type", "").lower()
    if expected_content_type and not content_type.startswith(expected_content_type):
        raise MakraConnectionError(
            f"Expected a {expected_content_type} response from the Makra API",
            method=method,
            path=path,
        )
    return body
