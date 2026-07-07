"""Process shutdown coordination for health probes and graceful teardown."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone


class ShutdownState:
    def __init__(self) -> None:
        self._shutting_down = False
        self._started_at: datetime | None = None
        self._event = asyncio.Event()

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    @property
    def started_at(self) -> datetime | None:
        return self._started_at

    def begin(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._started_at = datetime.now(timezone.utc)
        self._event.set()

    async def wait_started(self, timeout: float | None = None) -> bool:
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


shutdown_state = ShutdownState()
