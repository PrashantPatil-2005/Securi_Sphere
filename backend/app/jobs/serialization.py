"""Serialize jobs for Redis transport."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.jobs.queue import Job


def job_to_json(job: Job) -> str:
    return json.dumps(
        {
            "id": job.id,
            "name": job.name,
            "payload": job.payload,
            "priority": job.priority,
            "created_at": job.created_at.isoformat(),
            "max_retries": job.max_retries,
            "retry_count": job.retry_count,
        }
    )


def job_from_json(raw: str | bytes) -> Job:
    data: dict[str, Any] = json.loads(raw)
    created_at = datetime.fromisoformat(data["created_at"])
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return Job(
        priority=int(data["priority"]),
        name=data["name"],
        payload=dict(data.get("payload") or {}),
        id=data["id"],
        created_at=created_at,
        max_retries=int(data.get("max_retries", 3)),
        retry_count=int(data.get("retry_count", 0)),
    )
