"""Tests for audit log export."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.audit import AuditLog
from app.models.user import User
from app.services.audit import log_audit


@pytest.mark.asyncio
async def test_audit_export_csv(admin_client: AsyncClient):
    async with async_session() as db:
        user = (await db.execute(select(User).where(User.email == "admin@test.local"))).scalar_one()
        await log_audit(db, "export_fixture_action", user_id=user.id, ip_address="10.0.0.1")
        await db.commit()

    res = await admin_client.get("/api/v1/audit/export?format=csv&action=export_fixture_action")
    assert res.status_code == 200, res.text
    assert "text/csv" in res.headers.get("content-type", "")
    body = res.text
    assert "export_fixture_action" in body
    assert "attachment" in res.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_audit_export_json(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/audit/export?format=json&limit=10")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("application/json")
    payload = res.json()
    assert isinstance(payload, list)


@pytest.mark.asyncio
async def test_audit_export_logs_meta_audit(admin_client: AsyncClient):
    res = await admin_client.get("/api/v1/audit/export?format=json&limit=5")
    assert res.status_code == 200

    async with async_session() as db:
        entry = (
            await db.execute(select(AuditLog).where(AuditLog.action == "audit_export").order_by(AuditLog.timestamp.desc()))
        ).scalars().first()
    assert entry is not None
    assert entry.details is not None
    assert entry.details.get("format") == "json"


@pytest.mark.asyncio
async def test_viewer_cannot_export_audit(viewer_client: AsyncClient):
    res = await viewer_client.get("/api/v1/audit/export?format=csv")
    assert res.status_code == 403
