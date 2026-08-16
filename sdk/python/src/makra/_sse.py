"""A line-oriented Server-Sent Events decoder.

The decoder is deliberately transport-agnostic: it is fed decoded text lines
and emits complete events, so the synchronous and asynchronous clients can
share one implementation of the framing rules from the WHATWG SSE spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ServerSentEvent:
    """One dispatched SSE message."""

    event: str
    data: str
    id: Optional[str] = None
    retry: Optional[int] = None


class SSEDecoder:
    """Accumulates SSE field lines and dispatches them on a blank line."""

    def __init__(self) -> None:
        self._event = ""
        self._data: list[str] = []
        self._id: Optional[str] = None
        self._retry: Optional[int] = None
        self.last_event_id: Optional[str] = None

    def feed(self, line: str) -> Optional[ServerSentEvent]:
        """Consume one line and return an event when the message is complete."""
        line = line.rstrip("\r").lstrip("﻿")
        if not line:
            return self._dispatch()
        # A line beginning with a colon is a comment. The gateway sends
        # ": keepalive" every 15 seconds to hold the connection open.
        if line.startswith(":"):
            return None
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            self._event = value
        elif field == "data":
            self._data.append(value)
        elif field == "id" and "\x00" not in value:
            self._id = value
            self.last_event_id = value
        elif field == "retry":
            try:
                self._retry = int(value)
            except ValueError:
                pass
        return None

    def _dispatch(self) -> Optional[ServerSentEvent]:
        if not self._data and not self._event:
            self._reset()
            return None
        event = ServerSentEvent(
            event=self._event or "message",
            data="\n".join(self._data),
            id=self._id,
            retry=self._retry,
        )
        self._reset()
        return event

    def _reset(self) -> None:
        self._event = ""
        self._data = []
        self._id = None
