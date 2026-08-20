"""Workflow events, the domain layer on top of SSE framing."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ._constants import TERMINAL_EVENT_TYPES, RunStates
from ._sse import ServerSentEvent


@dataclass(frozen=True)
class WorkflowEvent:
    """One progress or lifecycle event from a workflow run.

    ``payload`` is the event body exactly as the API sent it. The named
    properties are conveniences over the fields the gateway guarantees on
    terminal events; anything else stays reachable through ``payload``.
    """

    type: str
    sequence: int
    payload: Dict[str, Any] = field(default_factory=dict)
    run_id: Optional[str] = None

    @property
    def is_terminal(self) -> bool:
        """Whether this event closes the stream."""
        return self.type in TERMINAL_EVENT_TYPES

    @property
    def detail_type(self) -> Optional[str]:
        """The fine-grained step name; compare with ``StreamDetailTypes``."""
        value = self.payload.get("stream_event_type")
        return value if isinstance(value, str) else None

    @property
    def status(self) -> Optional[str]:
        value = self.payload.get("status")
        return value if isinstance(value, str) else None

    @property
    def reason(self) -> Optional[str]:
        value = self.payload.get("reason")
        return value if isinstance(value, str) else None

    @property
    def success(self) -> Optional[bool]:
        """Domain success on a terminal event. ``None`` before the run ends."""
        value = self.payload.get("success")
        return value if isinstance(value, bool) else None


def parse_event(message: ServerSentEvent, run_id: Optional[str]) -> WorkflowEvent:
    """Convert a raw SSE message into a workflow event."""
    payload: Dict[str, Any] = {}
    if message.data:
        try:
            decoded = json.loads(message.data)
        except ValueError:
            decoded = {"raw": message.data}
        payload = decoded if isinstance(decoded, dict) else {"data": decoded}
    return WorkflowEvent(
        type=message.event,
        sequence=_sequence(message.id),
        payload=payload,
        run_id=run_id,
    )


def terminal_state(event: WorkflowEvent) -> str:
    """The run state implied by a terminal event."""
    status = event.status
    if status:
        return status
    return {
        "workflow.run.completed": RunStates.COMPLETED,
        "workflow.run.failed": RunStates.FAILED,
        "workflow.run.cancelled": RunStates.CANCELLED,
        "workflow.run.budget_exhausted": RunStates.BUDGET_EXHAUSTED,
    }.get(event.type, RunStates.COMPLETED)


def _sequence(raw: Optional[str]) -> int:
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0
