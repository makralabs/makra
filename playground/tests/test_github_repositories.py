from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

SCRIPT = Path(__file__).parents[1] / "scripts" / "github_repositories.py"
DEVELOPMENT_BASE_URL = "http://localhost:8080"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("github_repositories", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_defaults_to_local_gateway(monkeypatch: Any) -> None:
    module = load_script()
    observed: dict[str, Any] = {}

    class FakeMakra:
        def __init__(self, **kwargs: Any) -> None:
            observed.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def extract(self, urls: list[str], schema: dict[str, Any]) -> dict[str, Any]:
            return {
                "success": True,
                "status": "succeeded",
                "data": {urls[0]: {"repositories": []}},
                "usage": {},
            }

    monkeypatch.setattr(module, "Makra", FakeMakra)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.delenv("MAKRA_BASE_URL", raising=False)

    assert module.main() == 0
    assert observed["base_url"] == DEVELOPMENT_BASE_URL
