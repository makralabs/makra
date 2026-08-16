"""Synchronous and asynchronous clients for the Makra API.

Both clients expose the same three ways to run a workflow:

* ``extract`` / ``schema`` — blocking REST. One request, one result.
* ``extract_stream`` / ``schema_stream`` — live progress events over SSE.
* ``submit_extract`` / ``submit_schema`` — fire and forget, returning a handle
  that can be polled, streamed, or cancelled later.

The pure logic they share (payload building, response decoding, error mapping,
retry timing, SSE framing) lives in the sibling modules; what is written twice
here is only the I/O plumbing, which cannot be shared between sync and async.
"""

from __future__ import annotations

import asyncio
import time
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
)

import httpx

from ._constants import (
    CONTENT_TYPE_SSE,
    DEFAULT_POLL_INTERVAL,
    HEADER_IDEMPOTENCY_KEY,
    HEADER_LAST_EVENT_ID,
    HEADER_PREFER,
    HEADER_RUN_ID,
    PATH_EXTRACT,
    PATH_HEALTH,
    PATH_READY,
    PATH_RUNS,
    PATH_SCHEMA,
    PREFER_RESPOND_ASYNC,
    TERMINAL_RUN_STATES,
    ExecutionModes,
    RunStates,
    run_path,
)
from ._config import ClientConfig, resolve_config
from ._errors import (
    MakraConnectionError,
    MakraRunFailedError,
    MakraStreamError,
    MakraTimeoutError,
)
from ._events import WorkflowEvent, parse_event
from ._requests import (
    build_extract_payload,
    build_schema_payload,
    new_idempotency_key,
)
from ._response import api_error, decode_body
from ._retry import is_retryable_status, retry_delay
from ._runs import AsyncRunHandle, RunHandle
from ._sse import SSEDecoder
from ._types import (
    AsyncAdmission,
    ExecutionMode,
    ExtractConfig,
    JsonSchema,
    RunPage,
    RunView,
    SchemaConfig,
)

_REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})


class _BaseClient:
    """Configuration and request shaping shared by both clients."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        stream_idle_timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_backoff: Optional[float] = None,
        default_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._config: ClientConfig = resolve_config(
            api_key,
            base_url=base_url,
            timeout=timeout,
            connect_timeout=connect_timeout,
            stream_idle_timeout=stream_idle_timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            default_headers=default_headers,
        )

    @property
    def config(self) -> ClientConfig:
        return self._config

    @property
    def api_key(self) -> str:
        return self._config.api_key

    @property
    def base_url(self) -> str:
        return self._config.base_url

    @property
    def timeout(self) -> float:
        return self._config.timeout

    def _request_timeout(self, timeout: Optional[float]) -> httpx.Timeout:
        return httpx.Timeout(
            timeout if timeout is not None else self._config.timeout,
            connect=self._config.connect_timeout,
        )

    def _stream_timeout(self) -> httpx.Timeout:
        # No overall deadline: a run may legitimately take minutes. The read
        # timeout bounds the gap between events instead, and the gateway's
        # 15-second heartbeat keeps that gap small while the run is alive.
        return httpx.Timeout(
            self._config.stream_idle_timeout, connect=self._config.connect_timeout
        )

    def _submit_headers(
        self,
        idempotency_key: Optional[str],
        *,
        prefer_async: bool = False,
        stream: bool = False,
    ) -> Dict[str, str]:
        headers = {HEADER_IDEMPOTENCY_KEY: idempotency_key or new_idempotency_key()}
        if prefer_async:
            headers[HEADER_PREFER] = PREFER_RESPOND_ASYNC
        if stream:
            headers["Accept"] = CONTENT_TYPE_SSE
        return headers

    @staticmethod
    def _list_params(
        limit: Optional[int],
        cursor: Optional[str],
        feature: Optional[str],
        state: Optional[str],
    ) -> Dict[str, Any]:
        params = {
            "limit": limit,
            "cursor": cursor,
            "feature": feature,
            "state": state,
        }
        return {key: value for key, value in params.items() if value is not None}

    @staticmethod
    def _next_poll_delay(run: Mapping[str, Any], poll_interval: Optional[float]) -> float:
        """Respect the server's minimum reconciliation interval."""
        floor = DEFAULT_POLL_INTERVAL if poll_interval is None else poll_interval
        suggested = run.get("poll_after_ms")
        if isinstance(suggested, (int, float)) and suggested > 0:
            return max(floor, float(suggested) / 1000.0)
        return floor

    @staticmethod
    def _check_terminal_state(run: RunView, run_id: str, raise_on_failure: bool) -> RunView:
        state = str(run.get("state", ""))
        if raise_on_failure and state != RunStates.COMPLETED:
            raise MakraRunFailedError(
                "Workflow run {} ended in state {!r}: {}".format(
                    run_id, state, run.get("terminal_reason") or "no reason reported"
                ),
                run_id=run_id,
                state=state,
                run=run,
            )
        return run

    def _connection_error(
        self, error: Exception, method: str, path: str
    ) -> MakraConnectionError:
        if isinstance(error, httpx.TimeoutException):
            return MakraTimeoutError(
                "Request to the Makra API timed out: {}".format(error),
                method=method,
                path=path,
            )
        return MakraConnectionError(
            "Could not connect to the Makra API: {}".format(error),
            method=method,
            path=path,
        )

    def _decode(self, response: httpx.Response, method: str, path: str) -> Any:
        body = decode_body(
            response.status_code,
            response.headers.get("content-type", ""),
            response.text,
        )
        if response.status_code >= 400:
            raise api_error(
                status_code=response.status_code,
                headers=response.headers,
                body=body,
                method=method,
                path=path,
            )
        return body

    def _stream_response_error(
        self, response: httpx.Response, method: str, path: str
    ) -> Optional[Exception]:
        """Validate the response that should have opened an event stream."""
        if response.status_code >= 400:
            return api_error(
                status_code=response.status_code,
                headers=response.headers,
                body=decode_body(
                    response.status_code,
                    response.headers.get("content-type", ""),
                    response.text,
                ),
                method=method,
                path=path,
            )
        content_type = response.headers.get("content-type", "")
        if CONTENT_TYPE_SSE not in content_type:
            return MakraStreamError(
                "Expected an event stream but the API returned {!r}".format(
                    content_type or "no content type"
                ),
                run_id=response.headers.get(HEADER_RUN_ID),
            )
        return None


class Makra(_BaseClient):
    """Synchronous client for the Makra API.

    ``Makra`` owns an HTTP connection pool, so reuse one instance for the
    lifetime of your application and close it when done — either explicitly or
    with a ``with`` block.
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        self._http = httpx.Client(
            headers=self._config.headers(),
            timeout=self._request_timeout(None),
            follow_redirects=False,
        )

    def __enter__(self) -> "Makra":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    # --- Health ------------------------------------------------------------

    def ping(self) -> Any:
        """Check that the API gateway is reachable."""
        return self._request("GET", PATH_HEALTH, retryable=True)

    def ready(self) -> Any:
        """Check that result storage is reachable, not just the gateway."""
        return self._request("GET", PATH_READY, retryable=True)

    # --- Blocking workflows ------------------------------------------------

    def extract(
        self,
        urls: Sequence[str],
        schema: JsonSchema,
        *,
        execution_mode: ExecutionMode = ExecutionModes.CONCURRENT,
        config: Optional[ExtractConfig] = None,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Extract structured data and wait for the result.

        The connection is held until the run is terminal, so ``timeout`` is
        effectively the longest a workflow may take.
        """
        payload = build_extract_payload(
            urls, schema, execution_mode=execution_mode, config=config
        )
        return self._request(
            "POST",
            PATH_EXTRACT,
            json=payload,
            headers=self._submit_headers(idempotency_key),
            timeout=timeout,
            retryable=True,
        )

    def schema(
        self,
        url: str,
        *,
        only_memoized: bool = False,
        config: Optional[SchemaConfig] = None,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Build a JSON Schema describing everything one page contains."""
        payload = build_schema_payload(
            url, only_memoized=only_memoized, config=config
        )
        return self._request(
            "POST",
            PATH_SCHEMA,
            json=payload,
            headers=self._submit_headers(idempotency_key),
            timeout=timeout,
            retryable=True,
        )

    # --- Streaming workflows ------------------------------------------------

    def extract_stream(
        self,
        urls: Sequence[str],
        schema: JsonSchema,
        *,
        execution_mode: ExecutionMode = ExecutionModes.CONCURRENT,
        config: Optional[ExtractConfig] = None,
        idempotency_key: Optional[str] = None,
    ) -> Iterator[WorkflowEvent]:
        """Run an extraction and iterate its progress events as they happen.

        The stream carries lifecycle and progress events, not the payload. Read
        ``event.run_id`` from any event and call :meth:`get_run_result` once a
        terminal event arrives.
        """
        payload = build_extract_payload(
            urls, schema, execution_mode=execution_mode, config=config, stream=True
        )
        return self._stream_events(
            "POST", PATH_EXTRACT, json=payload, idempotency_key=idempotency_key
        )

    def schema_stream(
        self,
        url: str,
        *,
        only_memoized: bool = False,
        config: Optional[SchemaConfig] = None,
        idempotency_key: Optional[str] = None,
    ) -> Iterator[WorkflowEvent]:
        """Run schema generation and iterate its progress events."""
        payload = build_schema_payload(
            url, only_memoized=only_memoized, config=config, stream=True
        )
        return self._stream_events(
            "POST", PATH_SCHEMA, json=payload, idempotency_key=idempotency_key
        )

    def stream_run_events(
        self, run_id: str, *, last_event_id: int = 0
    ) -> Iterator[WorkflowEvent]:
        """Attach to an existing run's event stream, optionally resuming."""
        return self._stream_events(
            "GET", run_path(run_id, "/events"), run_id=run_id, last_event_id=last_event_id
        )

    # --- Asynchronous submission --------------------------------------------

    def submit_extract(
        self,
        urls: Sequence[str],
        schema: JsonSchema,
        *,
        execution_mode: ExecutionMode = ExecutionModes.CONCURRENT,
        config: Optional[ExtractConfig] = None,
        idempotency_key: Optional[str] = None,
    ) -> RunHandle:
        """Queue an extraction and return immediately with a run handle."""
        payload = build_extract_payload(
            urls, schema, execution_mode=execution_mode, config=config
        )
        return RunHandle(self, self._submit(PATH_EXTRACT, payload, idempotency_key))

    def submit_schema(
        self,
        url: str,
        *,
        only_memoized: bool = False,
        config: Optional[SchemaConfig] = None,
        idempotency_key: Optional[str] = None,
    ) -> RunHandle:
        """Queue a schema build and return immediately with a run handle."""
        payload = build_schema_payload(
            url, only_memoized=only_memoized, config=config
        )
        return RunHandle(self, self._submit(PATH_SCHEMA, payload, idempotency_key))

    # --- Run management -----------------------------------------------------

    def get_run(self, run_id: str) -> RunView:
        """Fetch run metadata. Never the result payload."""
        return self._request("GET", run_path(run_id), retryable=True)

    def list_runs(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        feature: Optional[str] = None,
        state: Optional[str] = None,
    ) -> RunPage:
        """List the caller's non-archived runs, newest first."""
        return self._request(
            "GET",
            PATH_RUNS,
            params=self._list_params(limit, cursor, feature, state),
            retryable=True,
        )

    def cancel_run(self, run_id: str) -> RunView:
        """Request cancellation of a run. Safe to call more than once."""
        return self._request("POST", run_path(run_id, "/cancel"), retryable=True)

    def wait_for_run(
        self,
        run_id: str,
        *,
        timeout: Optional[float] = None,
        poll_interval: Optional[float] = None,
        raise_on_failure: bool = True,
    ) -> RunView:
        """Poll until the run is terminal.

        A ``completed`` run whose payload reports ``success: false`` is a
        domain failure, not an infrastructure one, so it is returned rather
        than raised.
        """
        deadline = time.monotonic() + (
            timeout if timeout is not None else self._config.timeout
        )
        while True:
            run = self.get_run(run_id)
            if str(run.get("state", "")) in TERMINAL_RUN_STATES:
                return self._check_terminal_state(run, run_id, raise_on_failure)
            delay = self._next_poll_delay(run, poll_interval)
            if time.monotonic() + delay > deadline:
                raise MakraTimeoutError(
                    "Workflow run {} did not finish in time".format(run_id),
                    method="GET",
                    path=run_path(run_id),
                )
            time.sleep(delay)

    def get_run_result(self, run_id: str) -> Any:
        """Download a terminal run's stored result payload."""
        path = run_path(run_id, "/result")
        response = self._send("GET", path, retryable=True)
        if response.status_code in _REDIRECT_STATUS:
            return self._download_redirect(response, path)
        return self._decode(response, "GET", path)

    # --- Internals ----------------------------------------------------------

    def _submit(
        self, path: str, payload: Dict[str, Any], idempotency_key: Optional[str]
    ) -> AsyncAdmission:
        admission = self._request(
            "POST",
            path,
            json=payload,
            headers=self._submit_headers(idempotency_key, prefer_async=True),
            retryable=True,
        )
        return admission if isinstance(admission, dict) else {}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._send(method, path, **kwargs)
        return self._decode(response, method, path)

    def _send(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        retryable: bool = False,
    ) -> httpx.Response:
        attempt = 0
        while True:
            error: Optional[Exception] = None
            cause: Optional[Exception] = None
            try:
                response = self._http.request(
                    method,
                    self._config.url(path),
                    json=json,
                    params=params,
                    headers=dict(headers or {}),
                    timeout=self._request_timeout(timeout),
                )
            except httpx.HTTPError as exc:
                cause = exc
                error = self._connection_error(exc, method, path)
            else:
                if response.status_code < 400:
                    return response
                error = self._decode_error(response, method, path)
                if not is_retryable_status(
                    response.status_code, getattr(error, "code", None)
                ):
                    raise error
            attempt += 1
            if not retryable or attempt > self._config.max_retries:
                raise error from cause
            time.sleep(
                retry_delay(
                    attempt,
                    backoff=self._config.retry_backoff,
                    retry_after=getattr(error, "retry_after", None),
                )
            )

    def _decode_error(
        self, response: httpx.Response, method: str, path: str
    ) -> Exception:
        try:
            self._decode(response, method, path)
        except Exception as exc:  # noqa: BLE001 - the error is the return value
            return exc
        return MakraStreamError("unexpected error state")  # pragma: no cover

    def _download_redirect(self, response: httpx.Response, path: str) -> Any:
        """Follow a result redirect without leaking credentials to storage.

        Production stores results in object storage and redirects to a
        short-lived presigned URL. That URL authenticates itself, so the
        download must not carry the Makra API key.
        """
        location = response.headers.get("location")
        if not location:
            raise MakraStreamError("Result redirect did not include a location")
        with httpx.Client(timeout=self._request_timeout(None)) as anonymous:
            try:
                download = anonymous.get(location, follow_redirects=True)
            except httpx.HTTPError as exc:
                raise self._connection_error(exc, "GET", path) from exc
        return self._decode(download, "GET", path)

    def _stream_events(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        run_id: Optional[str] = None,
        last_event_id: int = 0,
    ) -> Iterator[WorkflowEvent]:
        headers = (
            self._submit_headers(idempotency_key, stream=True)
            if method == "POST"
            else {"Accept": CONTENT_TYPE_SSE}
        )
        attempt = 0
        while True:
            cause: Optional[Exception] = None
            try:
                with self._http.stream(
                    method,
                    self._config.url(path),
                    json=json,
                    headers=_with_resume(headers, last_event_id),
                    timeout=self._stream_timeout(),
                ) as response:
                    failure = self._stream_response_error(response, method, path)
                    if failure is not None:
                        raise failure
                    run_id = run_id or response.headers.get(HEADER_RUN_ID)
                    for event in _decode_stream(response.iter_lines(), run_id):
                        attempt = 0
                        last_event_id = event.sequence or last_event_id
                        yield event
                        if event.is_terminal:
                            return
            except httpx.HTTPError as exc:
                cause = exc
            # Reaching here means the stream ended without a terminal event.
            method, path, json, headers = _resume_target(run_id)
            attempt += 1
            if run_id is None or attempt > self._config.max_retries:
                raise MakraStreamError(
                    "Event stream ended before the run finished", run_id=run_id
                ) from cause
            time.sleep(retry_delay(attempt, backoff=self._config.retry_backoff))


class AsyncMakra(_BaseClient):
    """Asynchronous client for the Makra API.

    Mirrors :class:`Makra` exactly; every operation is awaitable and the two
    stream helpers return async iterators.
    """

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)
        self._http = httpx.AsyncClient(
            headers=self._config.headers(),
            timeout=self._request_timeout(None),
            follow_redirects=False,
        )

    async def __aenter__(self) -> "AsyncMakra":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    # --- Health ------------------------------------------------------------

    async def ping(self) -> Any:
        return await self._request("GET", PATH_HEALTH, retryable=True)

    async def ready(self) -> Any:
        return await self._request("GET", PATH_READY, retryable=True)

    # --- Blocking workflows ------------------------------------------------

    async def extract(
        self,
        urls: Sequence[str],
        schema: JsonSchema,
        *,
        execution_mode: ExecutionMode = ExecutionModes.CONCURRENT,
        config: Optional[ExtractConfig] = None,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        payload = build_extract_payload(
            urls, schema, execution_mode=execution_mode, config=config
        )
        return await self._request(
            "POST",
            PATH_EXTRACT,
            json=payload,
            headers=self._submit_headers(idempotency_key),
            timeout=timeout,
            retryable=True,
        )

    async def schema(
        self,
        url: str,
        *,
        only_memoized: bool = False,
        config: Optional[SchemaConfig] = None,
        idempotency_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        payload = build_schema_payload(
            url, only_memoized=only_memoized, config=config
        )
        return await self._request(
            "POST",
            PATH_SCHEMA,
            json=payload,
            headers=self._submit_headers(idempotency_key),
            timeout=timeout,
            retryable=True,
        )

    # --- Streaming workflows ------------------------------------------------

    def extract_stream(
        self,
        urls: Sequence[str],
        schema: JsonSchema,
        *,
        execution_mode: ExecutionMode = ExecutionModes.CONCURRENT,
        config: Optional[ExtractConfig] = None,
        idempotency_key: Optional[str] = None,
    ) -> AsyncIterator[WorkflowEvent]:
        payload = build_extract_payload(
            urls, schema, execution_mode=execution_mode, config=config, stream=True
        )
        return self._stream_events(
            "POST", PATH_EXTRACT, json=payload, idempotency_key=idempotency_key
        )

    def schema_stream(
        self,
        url: str,
        *,
        only_memoized: bool = False,
        config: Optional[SchemaConfig] = None,
        idempotency_key: Optional[str] = None,
    ) -> AsyncIterator[WorkflowEvent]:
        payload = build_schema_payload(
            url, only_memoized=only_memoized, config=config, stream=True
        )
        return self._stream_events(
            "POST", PATH_SCHEMA, json=payload, idempotency_key=idempotency_key
        )

    def stream_run_events(
        self, run_id: str, *, last_event_id: int = 0
    ) -> AsyncIterator[WorkflowEvent]:
        return self._stream_events(
            "GET", run_path(run_id, "/events"), run_id=run_id, last_event_id=last_event_id
        )

    # --- Asynchronous submission --------------------------------------------

    async def submit_extract(
        self,
        urls: Sequence[str],
        schema: JsonSchema,
        *,
        execution_mode: ExecutionMode = ExecutionModes.CONCURRENT,
        config: Optional[ExtractConfig] = None,
        idempotency_key: Optional[str] = None,
    ) -> AsyncRunHandle:
        payload = build_extract_payload(
            urls, schema, execution_mode=execution_mode, config=config
        )
        admission = await self._submit(PATH_EXTRACT, payload, idempotency_key)
        return AsyncRunHandle(self, admission)

    async def submit_schema(
        self,
        url: str,
        *,
        only_memoized: bool = False,
        config: Optional[SchemaConfig] = None,
        idempotency_key: Optional[str] = None,
    ) -> AsyncRunHandle:
        payload = build_schema_payload(
            url, only_memoized=only_memoized, config=config
        )
        admission = await self._submit(PATH_SCHEMA, payload, idempotency_key)
        return AsyncRunHandle(self, admission)

    # --- Run management -----------------------------------------------------

    async def get_run(self, run_id: str) -> RunView:
        return await self._request("GET", run_path(run_id), retryable=True)

    async def list_runs(
        self,
        *,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        feature: Optional[str] = None,
        state: Optional[str] = None,
    ) -> RunPage:
        return await self._request(
            "GET",
            PATH_RUNS,
            params=self._list_params(limit, cursor, feature, state),
            retryable=True,
        )

    async def cancel_run(self, run_id: str) -> RunView:
        return await self._request("POST", run_path(run_id, "/cancel"), retryable=True)

    async def wait_for_run(
        self,
        run_id: str,
        *,
        timeout: Optional[float] = None,
        poll_interval: Optional[float] = None,
        raise_on_failure: bool = True,
    ) -> RunView:
        deadline = time.monotonic() + (
            timeout if timeout is not None else self._config.timeout
        )
        while True:
            run = await self.get_run(run_id)
            if str(run.get("state", "")) in TERMINAL_RUN_STATES:
                return self._check_terminal_state(run, run_id, raise_on_failure)
            delay = self._next_poll_delay(run, poll_interval)
            if time.monotonic() + delay > deadline:
                raise MakraTimeoutError(
                    "Workflow run {} did not finish in time".format(run_id),
                    method="GET",
                    path=run_path(run_id),
                )
            await asyncio.sleep(delay)

    async def get_run_result(self, run_id: str) -> Any:
        path = run_path(run_id, "/result")
        response = await self._send("GET", path, retryable=True)
        if response.status_code in _REDIRECT_STATUS:
            return await self._download_redirect(response, path)
        return self._decode(response, "GET", path)

    # --- Internals ----------------------------------------------------------

    async def _submit(
        self, path: str, payload: Dict[str, Any], idempotency_key: Optional[str]
    ) -> AsyncAdmission:
        admission = await self._request(
            "POST",
            path,
            json=payload,
            headers=self._submit_headers(idempotency_key, prefer_async=True),
            retryable=True,
        )
        return admission if isinstance(admission, dict) else {}

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._send(method, path, **kwargs)
        return self._decode(response, method, path)

    async def _send(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        retryable: bool = False,
    ) -> httpx.Response:
        attempt = 0
        while True:
            error: Optional[Exception] = None
            cause: Optional[Exception] = None
            try:
                response = await self._http.request(
                    method,
                    self._config.url(path),
                    json=json,
                    params=params,
                    headers=dict(headers or {}),
                    timeout=self._request_timeout(timeout),
                )
            except httpx.HTTPError as exc:
                cause = exc
                error = self._connection_error(exc, method, path)
            else:
                if response.status_code < 400:
                    return response
                error = self._decode_error(response, method, path)
                if not is_retryable_status(
                    response.status_code, getattr(error, "code", None)
                ):
                    raise error
            attempt += 1
            if not retryable or attempt > self._config.max_retries:
                raise error from cause
            await asyncio.sleep(
                retry_delay(
                    attempt,
                    backoff=self._config.retry_backoff,
                    retry_after=getattr(error, "retry_after", None),
                )
            )

    def _decode_error(
        self, response: httpx.Response, method: str, path: str
    ) -> Exception:
        try:
            self._decode(response, method, path)
        except Exception as exc:  # noqa: BLE001 - the error is the return value
            return exc
        return MakraStreamError("unexpected error state")  # pragma: no cover

    async def _download_redirect(self, response: httpx.Response, path: str) -> Any:
        location = response.headers.get("location")
        if not location:
            raise MakraStreamError("Result redirect did not include a location")
        async with httpx.AsyncClient(
            timeout=self._request_timeout(None)
        ) as anonymous:
            try:
                download = await anonymous.get(location, follow_redirects=True)
            except httpx.HTTPError as exc:
                raise self._connection_error(exc, "GET", path) from exc
        return self._decode(download, "GET", path)

    async def _stream_events(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        run_id: Optional[str] = None,
        last_event_id: int = 0,
    ) -> AsyncIterator[WorkflowEvent]:
        headers = (
            self._submit_headers(idempotency_key, stream=True)
            if method == "POST"
            else {"Accept": CONTENT_TYPE_SSE}
        )
        attempt = 0
        while True:
            cause: Optional[Exception] = None
            try:
                async with self._http.stream(
                    method,
                    self._config.url(path),
                    json=json,
                    headers=_with_resume(headers, last_event_id),
                    timeout=self._stream_timeout(),
                ) as response:
                    if response.status_code >= 400:
                        await response.aread()
                    failure = self._stream_response_error(response, method, path)
                    if failure is not None:
                        raise failure
                    run_id = run_id or response.headers.get(HEADER_RUN_ID)
                    decoder = SSEDecoder()
                    async for line in response.aiter_lines():
                        message = decoder.feed(line)
                        if message is None:
                            continue
                        event = parse_event(message, run_id)
                        attempt = 0
                        last_event_id = event.sequence or last_event_id
                        yield event
                        if event.is_terminal:
                            return
            except httpx.HTTPError as exc:
                cause = exc
            method, path, json, headers = _resume_target(run_id)
            attempt += 1
            if run_id is None or attempt > self._config.max_retries:
                raise MakraStreamError(
                    "Event stream ended before the run finished", run_id=run_id
                ) from cause
            await asyncio.sleep(retry_delay(attempt, backoff=self._config.retry_backoff))


def _decode_stream(
    lines: Iterable[str], run_id: Optional[str]
) -> Iterator[WorkflowEvent]:
    decoder = SSEDecoder()
    for line in lines:
        message = decoder.feed(line)
        if message is not None:
            yield parse_event(message, run_id)


def _with_resume(headers: Mapping[str, str], last_event_id: int) -> Dict[str, str]:
    resolved = dict(headers)
    if last_event_id > 0:
        resolved[HEADER_LAST_EVENT_ID] = str(last_event_id)
    return resolved


def _resume_target(run_id: Optional[str]):
    """Where to reconnect after a dropped stream.

    A resumed stream is always a plain GET on the run's event endpoint: the
    original submission already created the run, and repeating it would be a
    second workflow.
    """
    path = run_path(run_id, "/events") if run_id else ""
    return "GET", path, None, {"Accept": CONTENT_TYPE_SSE}
