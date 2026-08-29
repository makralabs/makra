"""Shared Rich terminal runner for the Makra extraction playground examples."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from makra import PRODUCTION_BASE_URL, Makra, MakraError, WorkflowEvent
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

MAX_TABLE_ROWS = 100
MAX_EVENT_ROWS = 12
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"


@dataclass(frozen=True)
class ExtractExample:
    """One fixed extraction request exposed by a playground script."""

    title: str
    urls: Sequence[str]
    schema: Mapping[str, Any]
    config: Any | None = None
    stream: bool = False


class WorkflowResultError(RuntimeError):
    """The API completed a workflow but reported an unsuccessful result."""


def run_example(example: ExtractExample) -> int:
    """Run an example and render its activity, usage, and extracted data."""
    args = _arguments(example.title)
    load_dotenv(DOTENV_PATH, override=False)
    api_key = os.getenv("MAKRA_API_KEY")
    if not api_key:
        _error(
            "MAKRA_API_KEY is required. Add it to playground/.env or set it in your shell."
        )
        return 2

    console = Console()
    events: list[WorkflowEvent] = []
    state = "Preparing request"
    run_id: str | None = None

    try:
        with Makra(api_key=api_key, base_url=args.base_url) as client, Live(
            _activity_view(example, state, events),
            console=console,
            refresh_per_second=8,
        ) as live:
            if example.stream:
                state = "Streaming workflow events"
                live.update(_activity_view(example, state, events))
                for event in client.extract_stream(
                    example.urls,
                    example.schema,
                    execution_mode="concurrent",
                    config=example.config,
                ):
                    events.append(event)
                    run_id = run_id or event.run_id or _event_run_id(event)
                    state = "Streaming workflow events"
                    live.update(_activity_view(example, state, events))
                _raise_if_terminal_failed(events)
                if not run_id:
                    raise WorkflowResultError(
                        "The event stream finished without a workflow run ID."
                    )
                state = "Downloading the final result"
                live.update(_activity_view(example, state, events))
                result = client.get_run_result(run_id)
            else:
                state = "Submitting the extraction"
                live.update(_activity_view(example, state, events))
                handle = client.submit_extract(
                    example.urls,
                    example.schema,
                    execution_mode="concurrent",
                    config=example.config,
                )
                run_id = handle.id
                if not run_id:
                    raise WorkflowResultError(
                        "Workflow admission did not include a run ID."
                    )
                state = "Streaming workflow events"
                live.update(_activity_view(example, state, events))
                for event in client.stream_run_events(run_id):
                    events.append(event)
                    state = "Streaming workflow events"
                    live.update(_activity_view(example, state, events))
                _raise_if_terminal_failed(events)
                state = "Downloading the final result"
                live.update(_activity_view(example, state, events))
                result = client.get_run_result(run_id)

        _raise_if_unsuccessful(result)
    except (MakraError, ValueError, WorkflowResultError) as error:
        _error(str(error), type(error).__name__)
        return 1
    except Exception as error:  # noqa: BLE001 - terminal examples must show all errors
        _error(str(error), type(error).__name__)
        return 1

    _render_result(console, example, result)
    return 0


def _arguments(title: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=title)
    parser.add_argument(
        "--base-url",
        default=os.getenv("MAKRA_BASE_URL", PRODUCTION_BASE_URL),
        help="Makra API base URL (defaults to the production gateway).",
    )
    return parser.parse_args()


def _activity_view(
    example: ExtractExample, state: str, events: Sequence[WorkflowEvent]
) -> Layout:
    details = Table.grid(padding=(0, 1))
    details.add_column(style="bold cyan")
    details.add_column()
    details.add_row("Request", example.title)
    details.add_row("URLs", str(len(example.urls)))
    details.add_row("State", state)

    event_table = Table(title="Live workflow events", expand=True)
    event_table.add_column("#", style="dim", width=5)
    event_table.add_column("Event", style="cyan", min_width=24)
    event_table.add_column("Status", style="green", width=16)
    event_table.add_column("Details", overflow="fold")
    if events:
        for event in events[-MAX_EVENT_ROWS:]:
            event_table.add_row(
                str(event.sequence or "–"),
                event.detail_type or event.type,
                event.status or "–",
                _event_details(event),
            )
    else:
        event_table.add_row("–", "No events yet", "–", "Waiting for the workflow.")
    layout = Layout()
    layout.split_column(
        Layout(
            Panel(details, title="Makra extraction", border_style="cyan"),
            name="request",
            size=7,
        ),
        Layout(event_table, name="events"),
    )
    return layout


def _event_details(event: WorkflowEvent) -> str:
    for field in ("message", "reason", "detail"):
        value = event.payload.get(field)
        if value is not None:
            return _cell(value, limit=180)
    return _cell(event.payload, limit=180)


def _event_run_id(event: WorkflowEvent) -> str | None:
    value = event.payload.get("run_id")
    return value if isinstance(value, str) and value else None


def _raise_if_terminal_failed(events: Sequence[WorkflowEvent]) -> None:
    terminal = next((event for event in reversed(events) if event.is_terminal), None)
    if terminal is None:
        raise WorkflowResultError("The event stream ended before a terminal event.")
    if terminal.success is False or terminal.status in {
        "failed",
        "cancelled",
        "budget_exhausted",
    }:
        raise WorkflowResultError(
            terminal.reason
            or _cell(terminal.payload, limit=500)
            or "The workflow reported failure."
        )


def _raise_if_unsuccessful(result: Any) -> None:
    if not isinstance(result, Mapping):
        return
    if result.get("success") is False:
        raise WorkflowResultError(_result_error_message(result))
    status = result.get("status")
    if status is not None and status not in {"succeeded", "partial", "completed"}:
        raise WorkflowResultError(_result_error_message(result))


def _result_error_message(result: Mapping[str, Any]) -> str:
    message = result.get("message") or result.get("error") or result.get("status")
    return _cell(message, limit=500) or "The workflow reported an unsuccessful result."


def _render_result(console: Console, example: ExtractExample, result: Any) -> None:
    payload = (
        result.get("data") if isinstance(result, Mapping) and "data" in result else result
    )
    console.print()
    console.rule("Extracted data")
    console.print(_data_table(example, payload))
    console.print()
    console.rule("Usage")
    console.print(
        _usage_table(result.get("usage") if isinstance(result, Mapping) else None)
    )


def _usage_table(usage: Any) -> Table:
    table = Table(
        title="API usage",
        box=box.SIMPLE,
        expand=True,
        show_header=False,
        padding=(0, 1),
    )
    table.add_column("Category", style="dim")
    table.add_column("Cost", justify="right")

    rows, total = _usage_costs(usage)
    if not rows:
        table.add_row("No billed usage returned", "")
        return table

    for label, cost in rows:
        table.add_row(label, _usd(cost))
    table.add_section()
    table.add_row("[bold]Total[/bold]", f"[bold]{_usd(total)}[/bold]")
    return table


def _usage_costs(usage: Any) -> tuple[list[tuple[str, float]], float]:
    """Return the billed category costs and the run total from a usage payload."""
    if not isinstance(usage, Mapping):
        return [], 0.0

    rows: list[tuple[str, float]] = []
    categories = usage.get("by_category")
    if isinstance(categories, list):
        for category in categories:
            if not isinstance(category, Mapping):
                continue
            cost = _number(category.get("cost_usd"))
            if cost is None:
                continue
            label = category.get("label") or category.get("category") or "Other"
            rows.append((str(label), cost))

    totals = usage.get("totals")
    total = _number(totals.get("cost_usd")) if isinstance(totals, Mapping) else None
    if total is None:
        total = sum(cost for _, cost in rows)
    return rows, total


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _usd(value: float) -> str:
    return f"${value:.4f}"


def _data_table(example: ExtractExample, payload: Any) -> Table:
    rows, expected_columns = _records_from_payload(example.schema, payload)
    if not rows:
        table = Table(title="Extracted data", expand=True)
        table.add_column("Result")
        table.add_row("No extracted records were returned.")
        return table

    columns = list(expected_columns)
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    table = Table(title="Extracted data", expand=True)
    for column in columns:
        table.add_column(column.replace(":$", "\n$"), overflow="fold")
    for row in rows[:MAX_TABLE_ROWS]:
        table.add_row(*[_cell(row.get(column)) for column in columns])
    if len(rows) > MAX_TABLE_ROWS:
        table.caption = f"Showing the first {MAX_TABLE_ROWS} of {len(rows)} extracted rows."
    return table


def _records_from_payload(
    schema: Mapping[str, Any], payload: Any
) -> tuple[list[Mapping[str, Any]], list[str]]:
    collection_fields = [key for key, value in schema.items() if isinstance(value, list)]
    expected_columns: list[str] = []
    for collection in collection_fields:
        items = schema.get(collection)
        if items and isinstance(items[0], Mapping):
            expected_columns = list(items[0])
            break

    records: list[Mapping[str, Any]] = []
    if collection_fields:
        _find_collection_records(payload, set(collection_fields), records)
    else:
        expected_columns = list(schema)
        _find_scalar_records(payload, set(expected_columns), records)
    return records, expected_columns


def _find_collection_records(
    value: Any, collection_fields: set[str], records: list[Mapping[str, Any]]
) -> None:
    if isinstance(value, Mapping):
        for field in collection_fields:
            items = value.get(field)
            if isinstance(items, list):
                records.extend(item for item in items if isinstance(item, Mapping))
        for key, child in value.items():
            if key not in collection_fields:
                _find_collection_records(child, collection_fields, records)
    elif isinstance(value, list):
        for item in value:
            _find_collection_records(item, collection_fields, records)


def _find_scalar_records(
    value: Any, fields: set[str], records: list[Mapping[str, Any]]
) -> None:
    if isinstance(value, Mapping):
        if fields.intersection(value):
            records.append(value)
            return
        for child in value.values():
            _find_scalar_records(child, fields, records)
    elif isinstance(value, list):
        for item in value:
            _find_scalar_records(item, fields, records)


def _cell(value: Any, limit: int = 160) -> str:
    if value is None:
        rendered = ""
    elif isinstance(value, (Mapping, list)):
        rendered = json.dumps(value, ensure_ascii=False, default=str)
    else:
        rendered = str(value)
    rendered = " ".join(rendered.split())
    return rendered if len(rendered) <= limit else rendered[: limit - 1] + "…"


def _error(message: str, error_type: str = "Configuration error") -> None:
    Console(stderr=True).print(
        Text.assemble(("Error: ", "bold red"), (error_type + ": ", "bold"), message)
    )
