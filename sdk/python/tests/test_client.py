import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

import pytest

from makra import (
    AsyncMakra,
    DUMMY_API_KEY,
    ExtractConfig,
    ExtractOptions,
    Iso3166Alpha2,
    Makra,
    MakraAPIError,
    MakraResultError,
    MakraRunFailedError,
    MakraStreamError,
    MakraTimeoutError,
    ProxyRegion,
    ProxyRegionScopes,
    RunStates,
    SchemaConfig,
    SchemaOptions,
    ValidationModes,
    run_is_terminal,
    run_succeeded,
)


class _RequestHandler(BaseHTTPRequestHandler):
    requests: List[Dict[str, Any]] = []
    run_state = "completed"
    run_success = True
    result_payload: Dict[str, Any] = {
        "success": True,
        "status": "succeeded",
        "data": {"title": "Makra"},
    }

    def do_GET(self):
        self._record_request()
        if self.path == "/workflows/runs/run-extract":
            self._send_json(
                200,
                {
                    "id": "run-extract",
                    "state": self.run_state,
                    "success": self.run_success,
                    "poll_after_ms": 1,
                },
            )
            return
        if self.path == "/workflows/runs/run-extract/result":
            self._send_json(200, self.result_payload)
            return
        self._send_json(200, {"status": "ok"})

    def do_POST(self):
        self._record_request()
        if self.path == "/workflows/extract":
            if self.headers.get("Prefer") == "respond-async":
                self._send_json(
                    202,
                    {
                        "run_id": "run-extract",
                        "state": "queued",
                        "feature": "extract",
                    },
                )
                return
            self._send_json(200, self.result_payload)
            return
        if self.path == "/workflows/schema":
            self._send_json(422, {"detail": "Invalid URL"})
            return
        self._send_json(404, {"detail": "Not found"})

    def log_message(self, format, *args):
        return

    def _record_request(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b""
        request = {
            "method": self.command,
            "path": self.path,
            "headers": dict(self.headers),
            "body": json.loads(raw_body) if raw_body else None,
        }
        self.__class__.requests.append(request)
        return request

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def api_server():
    _RequestHandler.requests = []
    _RequestHandler.run_state = "completed"
    _RequestHandler.run_success = True
    _RequestHandler.result_payload = {
        "success": True,
        "status": "succeeded",
        "data": {"title": "Makra"},
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def test_ping_uses_healthz_and_sends_api_key(api_server):
    with Makra(api_key="test-key", base_url=f"{api_server}/") as client:
        assert client.ping() == {"status": "ok"}

    request = _RequestHandler.requests[0]
    assert request["path"] == "/healthz"
    assert request["headers"]["Api-Key"] == "test-key"


def test_extract_sends_the_workflow_wire_payload(api_server):
    config: ExtractConfig = {
        "validation_mode": "repair",
        "pagination": {"enabled": True, "additional_pages": 2},
        "crawler": {
            "post_ready_wait_ms": 1000,
            "proxy": {"region": {"scope": "country", "value": "DE"}},
            "recovery": {
                "retry": True,
                "retry_delay_ms": None,
            },
        },
    }
    with Makra(api_key="test-key", base_url=api_server) as client:
        result = client.extract(
            urls=["https://example.com"],
            schema={"title": "Title of the page"},
            execution_mode="sequential",
            config=config,
        )

    assert result == {
        "success": True,
        "status": "succeeded",
        "data": {"title": "Makra"},
    }
    request = _RequestHandler.requests[0]
    assert request["path"] == "/workflows/extract"
    assert request["headers"]["Prefer"] == "respond-async"
    assert request["body"] == {
        "urls": ["https://example.com"],
        "schema": {"title": "Title of the page"},
        "execution_mode": "sequential",
        "config": {
            "validation_mode": "repair",
            "pagination": {"enabled": True, "additional_pages": 2},
            "crawler": {
                "post_ready_wait_ms": 1000,
                "proxy": {"region": {"scope": "country", "value": "DE"}},
                "recovery": {
                    "one_last_retry": True,
                    "one_last_retry_delay_ms": None,
                },
            },
        },
    }
    assert [request["path"] for request in _RequestHandler.requests] == [
        "/workflows/extract",
        "/workflows/runs/run-extract",
        "/workflows/runs/run-extract/result",
    ]


def test_schema_sends_the_workflow_wire_payload(api_server):
    config: SchemaConfig = {"crawler": {"post_ready_wait_ms": 0}}
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(MakraAPIError) as captured:
            client.schema(
                "https://invalid.example",
                only_memoized=True,
                config=config,
            )

    error = captured.value
    assert error.status_code == 422
    assert error.message == "Invalid URL"
    assert error.body == {"detail": "Invalid URL"}
    assert error.method == "POST"
    assert error.path == "/workflows/schema"
    assert _RequestHandler.requests[0]["body"] == {
        "url": "https://invalid.example",
        "only_memoized": True,
        "config": {"crawler": {"post_ready_wait_ms": 0}},
    }


def test_client_side_validation_happens_before_network_io(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(ValueError, match="urls must contain at least one URL"):
            client.extract(urls=[], schema={"title": "Title"})
        with pytest.raises(ValueError, match="schema must be a non-empty"):
            client.extract(urls=["https://example.com"], schema={})

    assert _RequestHandler.requests == []


def test_removed_config_keys_fail_before_network_io(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(ValueError, match="config.memory is not supported"):
            client.extract(
                urls=["https://example.com"],
                schema={"title": "Title"},
                config={"memory": {"enabled": True}},  # type: ignore[arg-type]
            )
        with pytest.raises(ValueError, match="config.audit is not supported"):
            client.extract(
                urls=["https://example.com"],
                schema={"title": "Title"},
                config={"audit": {"enabled": True}},  # type: ignore[arg-type]
            )
        with pytest.raises(ValueError, match="config.selector_chain_version is not supported"):
            client.extract(
                urls=["https://example.com"],
                schema={"title": "Title"},
                config={"selector_chain_version": 2},  # type: ignore[arg-type]
            )
        with pytest.raises(ValueError, match="retry and retry_delay_ms"):
            client.extract(
                urls=["https://example.com"],
                schema={"title": "Title"},
                config={"crawler": {"recovery": {"one_last_retry": True}}},  # type: ignore[arg-type]
            )

    assert _RequestHandler.requests == []


def test_workflow_timeout_scales_with_pagination_and_sequential_urls():
    from makra._requests import resolve_workflow_timeout

    config = {"pagination": {"enabled": True, "additional_pages": 2}}
    assert resolve_workflow_timeout(None, 300, config=config) == 900
    assert resolve_workflow_timeout(120, 300, config=config) == 120
    assert (
        resolve_workflow_timeout(
            None, 300, config=config, url_count=2, execution_mode="sequential"
        )
        == 1800
    )


def test_iso3166_alpha2_exposes_country_codes():
    from makra import EventTypes, Iso3166Alpha2, StreamDetailTypes

    assert Iso3166Alpha2.DE == "DE"
    assert EventTypes.RUN_COMPLETED == "workflow.run.completed"
    assert StreamDetailTypes.RUN_TITLE_GENERATED == "run.title_generated"


def test_explicit_empty_base_url_is_invalid():
    with pytest.raises(ValueError, match="absolute HTTP or HTTPS URL"):
        Makra(base_url="")


def test_missing_api_key_sends_dummy_key(api_server, monkeypatch):
    monkeypatch.delenv("MAKRA_API_KEY", raising=False)

    with Makra(base_url=api_server) as client:
        client.ping()

    assert _RequestHandler.requests[0]["headers"]["Api-Key"] == DUMMY_API_KEY


def test_explicit_configuration_overrides_environment(api_server, monkeypatch):
    monkeypatch.setenv("MAKRA_API_KEY", "environment-key")
    monkeypatch.setenv("MAKRA_BASE_URL", "https://environment.invalid")

    with Makra(api_key="explicit-key", base_url=api_server) as client:
        client.ping()

    assert _RequestHandler.requests[0]["headers"]["Api-Key"] == "explicit-key"


def test_async_client_has_the_same_ping_contract(api_server):
    async def ping():
        async with AsyncMakra(api_key="test-key", base_url=api_server) as client:
            return await client.ping()

    assert asyncio.run(ping()) == {"status": "ok"}


def test_async_extract_uses_durable_submission_and_returns_result(api_server):
    async def extract():
        async with AsyncMakra(api_key="test-key", base_url=api_server) as client:
            return await client.extract(["https://example.com"], {"title": "Title"})

    assert asyncio.run(extract()) == _RequestHandler.result_payload
    assert [request["path"] for request in _RequestHandler.requests] == [
        "/workflows/extract",
        "/workflows/runs/run-extract",
        "/workflows/runs/run-extract/result",
    ]
    assert _RequestHandler.requests[0]["headers"]["Prefer"] == "respond-async"


def test_extract_returns_completed_domain_failure_result(api_server):
    _RequestHandler.run_success = False
    _RequestHandler.result_payload = {
        "success": False,
        "status": "failed",
        "message": "Page access was blocked",
    }

    with Makra(api_key="test-key", base_url=api_server) as client:
        result = client.extract(["https://example.com"], {"title": "Title"})

    assert result == _RequestHandler.result_payload


def test_extract_raises_for_non_completed_terminal_run(api_server):
    _RequestHandler.run_state = "cancelled"
    _RequestHandler.run_success = False

    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(MakraRunFailedError) as captured:
            client.extract(["https://example.com"], {"title": "Title"})

    assert captured.value.run_id == "run-extract"
    assert captured.value.state == "cancelled"
    assert all(
        request["path"] != "/workflows/runs/run-extract/result"
        for request in _RequestHandler.requests
    )


def test_extract_timeout_keeps_recoverable_run_id(api_server):
    _RequestHandler.run_state = "running"

    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(MakraTimeoutError) as captured:
            client.extract(
                ["https://example.com"],
                {"title": "Title"},
                timeout=0.001,
            )

    assert captured.value.run_id == "run-extract"
    assert "get_run('run-extract')" in str(captured.value)


def test_invalid_public_arguments_fail_before_network_io(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(ValueError, match="timeout must be greater than 0"):
            client.extract(
                urls=["https://example.com"],
                schema={"title": "Title"},
                timeout=0,
            )
        with pytest.raises(ValueError, match="timeout must be a number"):
            client.extract(
                urls=["https://example.com"],
                schema={"title": "Title"},
                timeout=True,
            )
        with pytest.raises(ValueError, match="idempotency_key must be a non-empty string"):
            client.extract(
                urls=["https://example.com"],
                schema={"title": "Title"},
                idempotency_key="",
            )
        with pytest.raises(ValueError, match="run_id must be a non-empty string"):
            client.get_run("  ")
        with pytest.raises(ValueError, match="poll_interval must be greater than 0"):
            client.wait_for_run("run-1", poll_interval=0)
        with pytest.raises(ValueError, match="last_event_id must be an integer"):
            client.stream_run_events("run-1", last_event_id=True)
        with pytest.raises(ValueError, match="last_event_id must not be negative"):
            client.stream_run_events("run-1", last_event_id=-1)
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            client.list_runs(limit=101)
        with pytest.raises(ValueError, match="feature must be one of"):
            client.list_runs(feature="crawl")
        with pytest.raises(ValueError, match="state must be one of"):
            client.list_runs(state="done")

    assert _RequestHandler.requests == []


def test_stream_argument_validation_happens_when_the_method_is_called(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(ValueError, match="urls must contain at least one URL"):
            client.extract_stream(urls=[], schema={"title": "Title"})
        with pytest.raises(ValueError, match="idempotency_key must be a non-empty string"):
            client.extract_stream(
                urls=["https://example.com"],
                schema={"title": "Title"},
                idempotency_key=" ",
            )
        with pytest.raises(ValueError, match="run_id must be a non-empty string"):
            client.stream_run_events("")

    assert _RequestHandler.requests == []


def test_async_stream_argument_validation_happens_when_the_method_is_called(api_server):
    async def invalid_stream():
        async with AsyncMakra(api_key="test-key", base_url=api_server) as client:
            client.extract_stream(urls=[], schema={"title": "Title"})

    with pytest.raises(ValueError, match="urls must contain at least one URL"):
        asyncio.run(invalid_stream())
    assert _RequestHandler.requests == []


def test_reserved_headers_are_rejected_case_insensitively():
    with pytest.raises(ValueError, match="pass api_key to the Makra constructor"):
        Makra(default_headers={"API-KEY": "other"})
    with pytest.raises(ValueError, match="the SDK sets Content-Type automatically"):
        Makra(default_headers={"Content-Type": "text/plain"})
    with pytest.raises(ValueError, match="pass idempotency_key to the workflow method"):
        Makra(default_headers={"idempotency-key": "abc"})
    with pytest.raises(ValueError, match="default_headers keys and values must be strings"):
        Makra(default_headers={1: "x"})  # type: ignore[dict-item]
    Makra(default_headers={"X-Trace-Id": "abc"}).close()


def test_constructor_rejects_boolean_timeouts():
    with pytest.raises(ValueError, match="timeout must be a number"):
        Makra(timeout=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="max_retries must be a number"):
        Makra(max_retries=True)  # type: ignore[arg-type]


def test_option_objects_emit_the_same_wire_payload_as_equivalent_dictionaries(api_server):
    urls = ["https://example.com"]
    schema = {"title": "Title of the page"}
    mapping: ExtractConfig = {
        "validation_mode": ValidationModes.REPAIR,
        "pagination": {"enabled": True, "additional_pages": 2},
        "crawler": {
            "post_ready_wait_ms": 1000,
            "proxy": {"region": {"scope": "country", "value": "DE"}},
            "recovery": {"retry": True},
        },
    }
    options = ExtractOptions(
        validation_mode=ValidationModes.REPAIR,
        additional_pages=2,
        post_ready_wait_ms=1000,
        proxy_region=ProxyRegion.country(Iso3166Alpha2.DE),
        recovery_retry=True,
    )

    with Makra(api_key="test-key", base_url=api_server) as client:
        mapped = client.extract(urls, schema, config=mapping)
        optioned = client.extract(urls, schema, config=options)

    assert mapped == optioned == _RequestHandler.result_payload
    submissions = [
        request for request in _RequestHandler.requests if request["method"] == "POST"
    ]
    assert submissions[0]["body"] == submissions[1]["body"]
    assert submissions[0]["body"]["config"]["crawler"]["recovery"] == {
        "one_last_retry": True,
    }


def test_schema_options_and_dictionaries_emit_the_same_wire_payload(api_server):
    config: SchemaConfig = {"crawler": {"post_ready_wait_ms": 0}}
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(MakraAPIError):
            client.schema(
                "https://invalid.example",
                config=SchemaOptions(post_ready_wait_ms=0),
            )
        with pytest.raises(MakraAPIError):
            client.schema(
                "https://invalid.example",
                config=config,
            )

    assert (
        _RequestHandler.requests[0]["body"]["config"]
        == _RequestHandler.requests[1]["body"]["config"]
    )


def test_additional_pages_zero_enables_pagination():
    config = ExtractOptions(additional_pages=0).to_config()
    assert config.get("pagination") == {"enabled": True, "additional_pages": 0}
    assert ExtractOptions().to_config() == {}
    assert ProxyRegion.worldwide().to_dict() == {"scope": ProxyRegionScopes.WORLDWIDE}


def test_extract_and_schema_options_share_base_options():
    from makra._options import BaseOptions

    proxy = ProxyRegion.country(Iso3166Alpha2.DE)
    extract = ExtractOptions(
        post_ready_wait_ms=1000,
        proxy_region=proxy,
        recovery_retry=True,
    )
    schema = SchemaOptions(
        post_ready_wait_ms=1000,
        proxy_region=proxy,
        recovery_retry=True,
    )
    assert isinstance(extract, BaseOptions)
    assert isinstance(schema, BaseOptions)
    assert not isinstance(extract, SchemaOptions)
    assert not isinstance(schema, ExtractOptions)
    assert extract.to_config().get("crawler") == schema.to_config().get("crawler")


def test_run_outcome_helpers_cover_documented_states():
    assert run_is_terminal({"state": RunStates.COMPLETED}) is True
    assert run_is_terminal({"state": RunStates.FAILED}) is True
    assert run_is_terminal({"state": RunStates.CANCELLED}) is True
    assert run_is_terminal({"state": RunStates.BUDGET_EXHAUSTED}) is True
    assert run_is_terminal({"state": RunStates.RUNNING}) is False
    assert run_is_terminal({"state": RunStates.QUEUED}) is False
    assert run_is_terminal({"state": RunStates.CANCEL_REQUESTED}) is False
    assert run_is_terminal({}) is False

    assert run_succeeded({"state": RunStates.COMPLETED, "success": True}) is True
    assert run_succeeded({"state": RunStates.COMPLETED}) is True
    assert run_succeeded({"state": RunStates.COMPLETED, "success": False}) is False
    assert run_succeeded({"state": RunStates.FAILED}) is False
    assert run_succeeded({"state": RunStates.CANCELLED, "success": True}) is False
    assert run_succeeded({"state": RunStates.BUDGET_EXHAUSTED}) is False
    assert run_succeeded({"state": RunStates.RUNNING, "success": True}) is False
    assert run_succeeded({}) is False


class _ResultRedirectHandler(BaseHTTPRequestHandler):
    requests: List[Dict[str, Any]] = []
    location: Optional[str] = None
    status = 303
    download_payload = {"success": True, "data": {"title": "Stored"}}

    def do_GET(self):
        self._record_request()
        if self.path.startswith("/workflows/runs/") and self.path.endswith("/result"):
            self.send_response(self.status)
            if self.location is not None:
                self.send_header("Location", self.location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = json.dumps(self.download_payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return

    def _record_request(self):
        request = {
            "method": self.command,
            "path": self.path,
            "headers": dict(self.headers),
        }
        self.__class__.requests.append(request)


@pytest.fixture()
def result_server():
    _ResultRedirectHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _ResultRedirectHandler)
    host, port = server.server_address[:2]
    _ResultRedirectHandler.location = (
        "http://{}:{}/storage/result?sig=super-secret".format(host, port)
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://{}:{}".format(host, port)
    finally:
        server.shutdown()
        thread.join()
        _ResultRedirectHandler.location = None


def test_result_redirect_does_not_forward_api_key(result_server):
    with Makra(api_key="secret-key", base_url=result_server) as client:
        payload = client.get_run_result("run-1")

    assert payload == {"success": True, "data": {"title": "Stored"}}
    gateway, download = _ResultRedirectHandler.requests
    assert gateway["path"] == "/workflows/runs/run-1/result"
    assert gateway["headers"]["Api-Key"] == "secret-key"
    assert download["path"] == "/storage/result?sig=super-secret"
    assert "Api-Key" not in download["headers"]
    assert "secret-key" not in str(download["headers"])


def test_missing_result_location_raises_result_error(result_server):
    _ResultRedirectHandler.location = None
    with Makra(api_key="secret-key", base_url=result_server) as client:
        with pytest.raises(
            MakraResultError, match="did not include a location"
        ) as captured:
            client.get_run_result("run-1")

    error = captured.value
    assert isinstance(error, MakraStreamError)
    assert error.run_id == "run-1"
    assert error.location is None
    assert "sig=" not in str(error)
    assert "super-secret" not in str(error)


def test_malformed_result_location_does_not_expose_query(result_server):
    _ResultRedirectHandler.location = "/relative?sig=super-secret"
    with Makra(api_key="secret-key", base_url=result_server) as client:
        with pytest.raises(MakraResultError) as captured:
            client.get_run_result("run-1")

    error = captured.value
    assert "super-secret" not in str(error)
    assert error.location is None or "super-secret" not in (error.location or "")
    assert isinstance(error, MakraStreamError)


def test_async_result_redirect_matches_sync(result_server):
    async def fetch():
        async with AsyncMakra(api_key="secret-key", base_url=result_server) as client:
            return await client.get_run_result("run-1")

    assert asyncio.run(fetch()) == {"success": True, "data": {"title": "Stored"}}
    assert "Api-Key" not in _ResultRedirectHandler.requests[1]["headers"]
