"""Integration tests for audit chain integrity API."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.services.audit import log_audit


@pytest.mark.asyncio
async def test_audit_integrity_valid(admin_client: AsyncClient):
    async with async_session() as db:
        user = (await db.execute(select(User).where(User.email == "admin@test.local"))).scalar_one()
        await log_audit(db, "integrity_fixture", user_id=user.id, ip_address="127.0.0.1")
        await db.commit()

    res = await admin_client.get("/api/v1/audit/integrity?limit=100")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["valid"] is True
    assert body["immutable_enabled"] is True
    assert body["entries_checked"] >= 1
    assert body["chain_head_hash"]


@pytest.mark.asyncio
async def test_viewer_cannot_verify_audit_integrity(viewer_client: AsyncClient):
    res = await viewer_client.get("/api/v1/audit/integrity")
    assert res.status_code == 403
