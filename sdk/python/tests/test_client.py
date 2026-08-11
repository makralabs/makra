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
    MakraConnectionError,
)


class _RequestHandler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):
        self._record_request()
        self._send_json(200, {"message": "pong"})

    def do_POST(self):
        request = self._record_request()
        if self.path == "/api/v1/extract":
            self._send_json(200, {"success": True, "data": {"title": "Makra"}})
            return
        if self.path == "/api/v1/preprocess":
            self._send_json(422, {"detail": "Invalid URL"})
            return
        if self.path == "/api/v0/format-markdown":
            if request["body"]["url"] == "https://json.example":
                self._send_json(200, "not markdown")
                return
            body = b"# Makra"
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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


def test_ping_uses_root_route_and_sends_bearer_api_key(api_server):
    with Makra(api_key="test-key", base_url=f"{api_server}/") as client:
        assert client.ping() == {"message": "pong"}

    request = _RequestHandler.requests[0]
    assert request["path"] == "/ping"
    assert request["headers"]["Authorization"] == "Bearer test-key"


def test_extract_sends_the_v1_wire_payload(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        result = client.extract(
            urls=["https://example.com"],
            output_schema={"title": "Title of the page"},
            actions=["pagination"],
            config={"use_cache": True},
        )

    assert result == {"success": True, "data": {"title": "Makra"}}
    request = _RequestHandler.requests[0]
    assert request["path"] == "/api/v1/extract"
    assert request["body"] == {
        "urls": ["https://example.com"],
        "output_schema": {"title": "Title of the page"},
        "actions": ["pagination"],
        "config": {"use_cache": True},
    }


def test_text_response_is_returned_as_text(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        result = client.format_markdown("https://example.com")

    assert result == "# Makra"


def test_markdown_rejects_a_non_text_content_type(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(MakraConnectionError, match="Expected a text/ response"):
            client.format_markdown("https://json.example")


def test_http_error_exposes_status_body_and_request_context(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(MakraAPIError) as captured:
            client.preprocess(["https://invalid.example"])

    error = captured.value
    assert error.status_code == 422
    assert error.message == "Invalid URL"
    assert error.body == {"detail": "Invalid URL"}
    assert error.method == "POST"
    assert error.path == "/api/v1/preprocess"


def test_client_side_validation_happens_before_network_io(api_server):
    with Makra(api_key="test-key", base_url=api_server) as client:
        with pytest.raises(ValueError, match="urls must contain at least one URL"):
            client.extract(urls=[], output_schema={"title": "Title"})

    assert _RequestHandler.requests == []


def test_explicit_empty_base_url_is_invalid():
    with pytest.raises(ValueError, match="absolute HTTP or HTTPS URL"):
        Makra(base_url="")


def test_missing_api_key_sends_dummy_key(api_server, monkeypatch):
    monkeypatch.delenv("MAKRA_API_KEY", raising=False)

    with Makra(base_url=api_server) as client:
        client.ping()

    assert _RequestHandler.requests[0]["headers"]["Authorization"] == (
        f"Bearer {DUMMY_API_KEY}"
    )


def test_explicit_configuration_overrides_environment(api_server, monkeypatch):
    monkeypatch.setenv("MAKRA_API_KEY", "environment-key")
    monkeypatch.setenv("MAKRA_BASE_URL", "https://environment.invalid")

    with Makra(api_key="explicit-key", base_url=api_server) as client:
        client.ping()

    assert _RequestHandler.requests[0]["headers"]["Authorization"] == (
        "Bearer explicit-key"
    )


def test_async_client_has_the_same_ping_contract(api_server):
    async def ping():
        async with AsyncMakra(api_key="test-key", base_url=api_server) as client:
            return await client.ping()

    assert asyncio.run(ping()) == {"message": "pong"}
