import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

JobHandler = Callable[..., Awaitable[Any]]


class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(order=True)
class Job:
    priority: int
    name: str = field(compare=False)
    payload: dict[str, Any] = field(default_factory=dict, compare=False)
    id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), compare=False)
    max_retries: int = field(default=3, compare=False)
    retry_count: int = field(default=0, compare=False)


class JobQueue:
    """Async priority job queue. Workers run inside the API process; scale out via Redis broker."""

    PRIORITY_MAP = {JobPriority.HIGH: 0, JobPriority.NORMAL: 5, JobPriority.LOW: 10}

    def __init__(self, workers: int = 2):
        self._queue: asyncio.PriorityQueue[Job] = asyncio.PriorityQueue()
        self._handlers: dict[str, JobHandler] = {}
        self._workers = workers
        self._tasks: list[asyncio.Task] = []
        self.is_running = False

    def register(self, name: str, handler: JobHandler) -> None:
        self._handlers[name] = handler

    async def enqueue(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> str:
        job = Job(priority=self.PRIORITY_MAP[priority], name=name, payload=payload or {})
        await self._queue.put(job)
        logger.info("job enqueued", extra={"job_name": name, "job_id": job.id})
        return job.id

    async def _worker(self, worker_id: int) -> None:
        while self.is_running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            handler = self._handlers.get(job.name)
            if not handler:
                logger.error("unknown job handler", extra={"job_name": job.name})
                continue
            try:
                await handler(**job.payload)
                logger.info("job completed", extra={"job_name": job.name, "job_id": job.id})
            except Exception:
                job.retry_count += 1
                if job.retry_count <= job.max_retries:
                    await self._queue.put(job)
                    logger.warning(
                        "job retry scheduled",
                        extra={"job_name": job.name, "retry": job.retry_count},
                        exc_info=True,
                    )
                else:
                    logger.error(
                        "job failed permanently",
                        extra={"job_name": job.name, "job_id": job.id},
                        exc_info=True,
                    )

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        for i in range(self._workers):
            self._tasks.append(asyncio.create_task(self._worker(i)))

    async def stop(self) -> None:
        self.is_running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()


job_queue = JobQueue(workers=2)
