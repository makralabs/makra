"""Handles for asynchronously submitted workflow runs.

A handle is the small, ergonomic object returned by ``submit_extract`` and
``submit_schema``. It remembers the run id so the caller does not have to
thread it through every follow-up call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Iterator, Optional

from ._events import WorkflowEvent
from ._types import AsyncAdmission, RunView

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from ._client import AsyncMakra, Makra


class _BaseRunHandle:
    """Identity and admission metadata shared by both handle flavours."""

    def __init__(self, admission: AsyncAdmission) -> None:
        self.id: str = str(admission.get("run_id", ""))
        self.feature: Optional[str] = admission.get("feature")
        self.state: Optional[str] = admission.get("state")
        self.status_url: Optional[str] = admission.get("status_url")
        self.events_url: Optional[str] = admission.get("events_url")
        self.result_url: Optional[str] = admission.get("result_url")
        self.admission: Dict[str, Any] = dict(admission)

    def __repr__(self) -> str:
        return "{}(id={!r}, feature={!r}, state={!r})".format(
            type(self).__name__, self.id, self.feature, self.state
        )


class RunHandle(_BaseRunHandle):
    """A submitted run, observable through the synchronous client."""

    def __init__(self, client: "Makra", admission: AsyncAdmission) -> None:
        super().__init__(admission)
        self._client = client

    def refresh(self) -> RunView:
        """Fetch current run metadata and update the cached state."""
        run = self._client.get_run(self.id)
        self.state = run.get("state", self.state)
        return run

    def wait(self, **kwargs: Any) -> RunView:
        """Poll until the run reaches a terminal state.

        Prefer :meth:`stream` when you want live progress; polling exists for
        reconciliation and for callers that cannot hold a connection open.
        """
        run = self._client.wait_for_run(self.id, **kwargs)
        self.state = run.get("state", self.state)
        return run

    def stream(self, *, last_event_id: int = 0) -> Iterator[WorkflowEvent]:
        """Attach to the run's live event stream."""
        return self._client.stream_run_events(self.id, last_event_id=last_event_id)

    def result(self) -> Any:
        """Download the stored result payload."""
        return self._client.get_run_result(self.id)

    def cancel(self) -> RunView:
        """Request cancellation. Idempotent; a terminal run is returned as-is."""
        run = self._client.cancel_run(self.id)
        self.state = run.get("state", self.state)
        return run


class AsyncRunHandle(_BaseRunHandle):
    """A submitted run, observable through the asynchronous client."""

    def __init__(self, client: "AsyncMakra", admission: AsyncAdmission) -> None:
        super().__init__(admission)
        self._client = client

    async def refresh(self) -> RunView:
        run = await self._client.get_run(self.id)
        self.state = run.get("state", self.state)
        return run

    async def wait(self, **kwargs: Any) -> RunView:
        run = await self._client.wait_for_run(self.id, **kwargs)
        self.state = run.get("state", self.state)
        return run

    def stream(self, *, last_event_id: int = 0) -> AsyncIterator[WorkflowEvent]:
        return self._client.stream_run_events(self.id, last_event_id=last_event_id)

    async def result(self) -> Any:
        return await self._client.get_run_result(self.id)

    async def cancel(self) -> RunView:
        run = await self._client.cancel_run(self.id)
        self.state = run.get("state", self.state)
        return run
