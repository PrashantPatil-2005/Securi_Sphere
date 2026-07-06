"""Regression tests for audit INET serialization and SIEM analytics endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.audit import AuditLog
from app.models.user import User
from app.services.audit import log_audit


@pytest.mark.asyncio
async def test_audit_list_returns_inet_as_string(admin_client: AsyncClient):
    async with async_session() as db:
        user = (await db.execute(select(User).where(User.email == "admin@test.local"))).scalar_one()
        await log_audit(db, "test_audit_inet", user_id=user.id, ip_address="127.0.0.1")
        await db.commit()

    res = await admin_client.get("/api/v1/audit")
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    entry = next((e for e in body if e["action"] == "test_audit_inet"), body[0])
    assert entry["ip_address"] == "127.0.0.1"


@pytest.mark.asyncio
async def test_siem_failed_logins_empty_db(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/siem/failed-logins")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "over_time" in body
    assert "by_host" in body
    assert "by_user" in body
    assert isinstance(body["over_time"], list)


@pytest.mark.asyncio
async def test_siem_executive_empty_db(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/siem/executive")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "total_hosts" in body
    assert "security_trend" in body
