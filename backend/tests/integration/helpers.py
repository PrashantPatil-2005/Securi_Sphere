"""Shared helpers for HTTP integration tests."""

import uuid
from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.host import Host
from app.models.user import User


async def admin_user_id() -> uuid.UUID:
    async with async_session() as db:
        user = (
            await db.execute(select(User).where(User.email == "admin@test.local"))
        ).scalar_one()
        return user.id


async def create_test_host(name: str, *, hostname: str | None = None) -> uuid.UUID:
    created_by = await admin_user_id()
    async with async_session() as db:
        host = Host(
            name=name,
            hostname=hostname or name,
            status="online",
            created_by=created_by,
        )
        db.add(host)
        await db.commit()
        await db.refresh(host)
        return host.id


async def enroll_test_host(client: AsyncClient, name: str) -> tuple[str, str]:
    host_res = await client.post("/api/v1/hosts", json={"name": name})
    assert host_res.status_code == 200, host_res.text
    host_id = host_res.json()["id"]

    token_res = await client.post(f"/api/v1/hosts/{host_id}/enrollment-token")
    assert token_res.status_code == 200, token_res.text
    token = token_res.json()["token"]

    reg_res = await client.post(
        "/api/v1/agent/register",
        json={
            "enrollment_token": token,
            "hostname": f"{name}.local",
            "ip_address": "10.0.0.10",
            "os_info": "Linux test",
        },
    )
    assert reg_res.status_code == 200, reg_res.text
    return host_id, reg_res.json()["api_key"]


def event_payload(
    event_type: str,
    *,
    severity: str = "medium",
    description: str | None = None,
    raw_log: str | None = None,
    offset_seconds: int = 0,
) -> dict:
    ts = datetime.now(timezone.utc)
    if offset_seconds:
        from datetime import timedelta
        ts = ts + timedelta(seconds=offset_seconds)
    return {
        "event_type": event_type,
        "severity": severity,
        "description": description or f"Test {event_type}",
        "source": "integration-test",
        "raw_log": raw_log or description or f"test {event_type}",
        "timestamp": ts.isoformat(),
    }


async def ingest_events(client: AsyncClient, api_key: str, events: list[dict]) -> dict:
    res = await client.post(
        "/api/v1/agent/events",
        headers={"X-API-Key": api_key},
        json={"events": events},
    )
    assert res.status_code == 200, res.text
    return res.json()
