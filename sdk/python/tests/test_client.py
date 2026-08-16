import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from makra import (
    AsyncMakra,
    DUMMY_API_KEY,
    Makra,
    MakraAPIError,
)


class _RequestHandler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        self._record_request()
        self._send_json(200, {"status": "ok"})

    def do_POST(self):
        self._record_request()
        if self.path == "/workflows/extract":
            self._send_json(200, {"success": True, "data": {"title": "Makra"}})
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
    with Makra(api_key="test-key", base_url=api_server) as client:
        result = client.extract(
            urls=["https://example.com"],
            schema={"title": "Title of the page"},
            execution_mode="sequential",
            config={
                "validation_mode": "repair",
                "memory": {"enabled": True, "selector_chain_version": "v2"},
                "pagination": {"enabled": True, "additional_pages": 2},
                "crawler": {
                    "post_ready_wait_ms": 1000,
                    "proxy": {"region": {"scope": "country", "value": "DE"}},
                    "recovery": {
                        "one_last_retry": True,
                        "one_last_retry_delay_ms": None,
                    },
                },
                "audit": {"enabled": False, "use_cache": True},
            },
        )

    assert result == {"success": True, "data": {"title": "Makra"}}
    request = _RequestHandler.requests[0]
    assert request["path"] == "/workflows/extract"
    assert request["body"] == {
        "urls": ["https://example.com"],
        "schema": {"title": "Title of the page"},
        "execution_mode": "sequential",
        "config": {
            "validation_mode": "repair",
            "memory": {"enabled": True, "selector_chain_version": "v2"},
            "pagination": {"enabled": True, "additional_pages": 2},
            "crawler": {
                "post_ready_wait_ms": 1000,
                "proxy": {"region": {"scope": "country", "value": "DE"}},
                "recovery": {
                    "one_last_retry": True,
                    "one_last_retry_delay_ms": None,
                },
            },
            "audit": {"enabled": False, "use_cache": True},
        },
    }


def test_schema_sends_the_workflow_wire_payload(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(MakraAPIError) as captured:
            client.schema(
                "https://invalid.example",
                only_memoized=True,
                config={"memory": {"enabled": False}},
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
        "config": {"memory": {"enabled": False}},
    }


def test_client_side_validation_happens_before_network_io(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(ValueError, match="urls must contain at least one URL"):
            client.extract(urls=[], schema={"title": "Title"})
        with pytest.raises(ValueError, match="schema must be a non-empty"):
            client.extract(urls=["https://example.com"], schema={})

    assert _RequestHandler.requests == []


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
