"""Contract tests for the documented golden quickstart."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "golden_quickstart.py"
DOCS_FENCE_PATHS = [
    Path(__file__).resolve().parents[4]
    / "docs"
    / "docs"
    / "docs"
    / "v0.0.4-beta"
    / "makra-sdk"
    / "getting-started"
    / "first-extraction.md",
]

GOLDEN_URL = "https://shop.example/products/atlas-lamp"
GOLDEN_RESULT = {"name": "Atlas Lamp", "price": "$129.00"}


class _GoldenHandler(BaseHTTPRequestHandler):
    requests: List[Dict[str, Any]] = []

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b""
        self.requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": json.loads(raw_body) if raw_body else None,
            }
        )
        if self.path == "/workflows/extract":
            payload = {"run_id": "run-golden", "state": "queued"}
            body = json.dumps(payload).encode()
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        self.requests.append(
            {"path": self.path, "headers": dict(self.headers), "body": None}
        )
        if self.path == "/workflows/runs/run-golden":
            payload = {"id": "run-golden", "state": "completed", "success": True}
        elif self.path == "/workflows/runs/run-golden/result":
            payload = {
                "success": True,
                "status": "succeeded",
                "data": {GOLDEN_URL: GOLDEN_RESULT},
            }
        else:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@pytest.fixture()
def golden_server():
    _GoldenHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GoldenHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def _first_python_fence(markdown: str) -> str:
    match = re.search(r"```python\n(.*?)```", markdown, re.DOTALL)
    if not match:
        raise AssertionError("no python fence found")
    return match.group(1)


def test_golden_quickstart_matches_docs_fence():
    example = EXAMPLE.read_text()
    docs_path = next((path for path in DOCS_FENCE_PATHS if path.is_file()), None)
    if docs_path is None:
        pytest.skip("docs repository is not checked out beside makra")
    assert example == _first_python_fence(docs_path.read_text())


def test_golden_quickstart_runs_against_local_server(golden_server):
    env = os.environ.copy()
    env["MAKRA_BASE_URL"] = golden_server
    env["MAKRA_API_KEY"] = "makra-development-key"
    completed = subprocess.run(
        [sys.executable, str(EXAMPLE)],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert GOLDEN_RESULT["name"] in completed.stdout
    assert _GoldenHandler.requests, "the golden program made no HTTP request"
    request = _GoldenHandler.requests[0]
    assert request["path"] == "/workflows/extract"
    assert request["body"]["urls"] == [GOLDEN_URL]
    assert request["body"]["schema"]["name"] == "The main product name"
    assert request["headers"].get("Api-Key") == "makra-development-key"
    assert request["headers"].get("Prefer") == "respond-async"
    assert [request["path"] for request in _GoldenHandler.requests] == [
        "/workflows/extract",
        "/workflows/runs/run-golden",
        "/workflows/runs/run-golden/result",
    ]


@pytest.mark.integration
def test_golden_quickstart_against_public_api():
    if os.environ.get("MAKRA_INTEGRATION") != "1":
        pytest.skip("set MAKRA_INTEGRATION=1 to run the credentialed golden path")
    if not os.environ.get("MAKRA_API_KEY"):
        pytest.skip("MAKRA_API_KEY is required for the public integration job")
    completed = subprocess.run(
        [sys.executable, str(EXAMPLE)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip()
