from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

from rich.console import Console

SCRIPT = Path(__file__).parents[1] / "scripts" / "github_repositories.py"
PRODUCTION_BASE_URL = "https://api.makralabs.org"


def load_script() -> ModuleType:
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("github_repositories", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_uses_production_gateway_and_makra_api_key(monkeypatch: Any) -> None:
    module = load_script()
    observed: dict[str, Any] = {}
    dotenv_call: dict[str, Any] = {}

    class FakeMakra:
        def __init__(self, **kwargs: Any) -> None:
            observed.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def submit_extract(
            self, urls: list[str], schema: dict[str, Any], **kwargs: Any
        ) -> SimpleNamespace:
            return SimpleNamespace(id="run-123")

        def stream_run_events(self, run_id: str) -> list[SimpleNamespace]:
            return [
                SimpleNamespace(
                    sequence=1,
                    detail_type="workflow.completed",
                    type="workflow.run.completed",
                    status="completed",
                    payload={"success": True},
                    run_id=run_id,
                    is_terminal=True,
                    success=True,
                )
            ]

        def get_run_result(self, run_id: str) -> dict[str, Any]:
            return {
                "success": True,
                "status": "succeeded",
                "data": {"repositories": []},
                "usage": {},
            }

    runner = sys.modules["_runner"]
    monkeypatch.setattr(runner, "Makra", FakeMakra)
    monkeypatch.setattr(
        runner,
        "load_dotenv",
        lambda path, override: dotenv_call.update(path=path, override=override),
    )
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.setenv("MAKRA_API_KEY", "test-key")
    monkeypatch.delenv("MAKRA_BASE_URL", raising=False)

    assert module.main() == 0
    assert dotenv_call == {"path": runner.DOTENV_PATH, "override": False}
    assert observed["api_key"] == "test-key"
    assert observed["base_url"] == PRODUCTION_BASE_URL


def test_usage_table_shows_category_costs_and_total_only() -> None:
    load_script()
    runner = sys.modules["_runner"]
    usage = {
        "rate_card_version": "2026-08-06",
        "by_category": [
            {"label": "Vision", "cost_usd": 0.0046},
            {"label": "Query", "cost_usd": 0.02},
            {"label": "Bandwidth", "cost_usd": 0},
        ],
        "totals": {"cost_usd": 0.0246},
    }

    console = Console(record=True, width=60)
    console.print(runner._usage_table(usage))
    rendered = console.export_text()

    assert "Vision" in rendered
    assert "Query" in rendered
    assert "Bandwidth" in rendered
    assert "Total" in rendered
    assert "$0.0246" in rendered
    assert "rate_card_version" not in rendered
