import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.config import settings

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


class MemoryJobBackend:
    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[Job] = asyncio.PriorityQueue()

    async def enqueue(self, job: Job) -> None:
        await self._queue.put(job)

    async def dequeue(self, timeout: float = 1.0) -> Job | None:
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def pending_count(self) -> int:
        return self._queue.qsize()


class JobQueue:
    """Async job queue with in-memory or Redis broker backends."""

    PRIORITY_MAP = {JobPriority.HIGH: 0, JobPriority.NORMAL: 5, JobPriority.LOW: 10}

    def __init__(self, workers: int | None = None):
        self._handlers: dict[str, JobHandler] = {}
        self._workers = workers if workers is not None else settings.job_queue_workers
        self._tasks: list[asyncio.Task] = []
        self._in_flight = 0
        self.is_running = False
        self.backend_name = "memory"
        self._memory = MemoryJobBackend()
        self._use_redis = (
            settings.job_queue_backend == "redis"
            and bool(settings.redis_url)
        )
        if settings.job_queue_backend == "redis" and not settings.redis_url:
            logger.warning("JOB_QUEUE_BACKEND=redis but REDIS_URL is unset; using memory queue")
        elif self._use_redis:
            self.backend_name = "redis"

    def register(self, name: str, handler: JobHandler) -> None:
        self._handlers[name] = handler

    async def enqueue(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> str:
        job = Job(priority=self.PRIORITY_MAP[priority], name=name, payload=payload or {})
        if self._use_redis:
            from app.jobs.redis_broker import enqueue_job

            await enqueue_job(job)
        else:
            await self._memory.enqueue(job)
        logger.info("job enqueued", extra={"job_name": name, "job_id": job.id, "backend": self.backend_name})
        return job.id

    async def _dequeue(self, timeout: float = 1.0) -> Job | None:
        if self._use_redis:
            from app.jobs.redis_broker import dequeue_job

            return await dequeue_job(timeout=max(1, int(timeout)))
        return await self._memory.dequeue(timeout)

    async def _requeue(self, job: Job) -> None:
        if self._use_redis:
            from app.jobs.redis_broker import enqueue_job

            await enqueue_job(job)
        else:
            await self._memory.enqueue(job)

    async def pending_count(self) -> int:
        if self._use_redis:
            from app.jobs.redis_broker import pending_job_count

            return await pending_job_count()
        return await self._memory.pending_count()

    async def _worker(self, worker_id: int) -> None:
        while self.is_running:
            job = await self._dequeue(timeout=1.0)
            if job is None:
                continue
            handler = self._handlers.get(job.name)
            if not handler:
                logger.error("unknown job handler", extra={"job_name": job.name})
                continue
            try:
                self._in_flight += 1
                await handler(**job.payload)
                logger.info(
                    "job completed",
                    extra={"job_name": job.name, "job_id": job.id, "worker_id": worker_id},
                    )
            except Exception:
                job.retry_count += 1
                if job.retry_count <= job.max_retries:
                    await self._requeue(job)
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
            finally:
                self._in_flight = max(0, self._in_flight - 1)

    def start(self, *, force: bool = False) -> None:
        if self.is_running or (not settings.job_queue_run_workers and not force):
            return
        self.is_running = True
        for i in range(self._workers):
            self._tasks.append(asyncio.create_task(self._worker(i)))
        logger.info(
            "job workers started",
            extra={"workers": self._workers, "backend": self.backend_name},
        )

    async def stop(self, *, grace_seconds: float | None = None) -> None:
        grace = settings.shutdown_grace_seconds if grace_seconds is None else grace_seconds
        self.is_running = False
        if grace > 0:
            deadline = asyncio.get_running_loop().time() + grace
            while self._in_flight > 0 and asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.1)
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()


job_queue = JobQueue()
