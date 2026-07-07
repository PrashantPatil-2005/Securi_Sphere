"""Worker process health check for container probes."""

from __future__ import annotations

import asyncio
import sys

from app.config import settings
from app.jobs.redis_broker import redis_ping


async def check() -> bool:
    if settings.job_queue_backend != "redis" or not settings.redis_url:
        return False
    return await redis_ping()


def main() -> None:
    ok = asyncio.run(check())
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
