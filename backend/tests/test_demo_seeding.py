"""DEMO_MODE=true + DEMO_USER_PASSWORD set: demo admin, password and a runnable host."""

import pytest_asyncio
from sqlalchemy import delete, select

import app.routers.auth as auth_mod
from app.config import settings
from app.database import async_session
from app.models.host import Host
from app.models.user import User
from app.routers.auth import DEMO_USER_EMAIL, seed_demo_users
from app.routers.hosts import DEMO_HOST_NAME, seed_demo_host
from app.security import verify_password

DEMO_PASSWORD = "Demo1234!"


@pytest_asyncio.fixture
async def demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "testing", False)
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(auth_mod, "DEMO_USER_PASSWORD", DEMO_PASSWORD)
    yield
    async with async_session() as db:
        await db.execute(delete(Host).where(Host.name == DEMO_HOST_NAME))
        await db.execute(delete(User).where(User.email == DEMO_USER_EMAIL))
        await db.commit()


async def test_demo_mode_seeds_the_documented_admin(prepare_database, demo_mode):
    async with async_session() as db:
        await db.execute(delete(User).where(User.email == DEMO_USER_EMAIL))
        await db.commit()

    async with async_session() as db:
        await seed_demo_users(db)
        await db.commit()

    async with async_session() as db:
        user = (
            await db.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        ).scalar_one_or_none()

    assert user is not None, "DEMO_MODE=true must seed demo@securi.local"
    assert user.is_active
    assert verify_password(DEMO_PASSWORD, user.hashed_password)


async def test_seeding_is_skipped_without_demo_password(prepare_database, monkeypatch):
    """No hardcoded fallback — DEMO_USER_PASSWORD must be configured."""
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "testing", False)
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(auth_mod, "DEMO_USER_PASSWORD", "")

    async with async_session() as db:
        await db.execute(delete(User).where(User.email == DEMO_USER_EMAIL))
        await db.commit()

    async with async_session() as db:
        await seed_demo_users(db)
        await db.commit()

    async with async_session() as db:
        user = (
            await db.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        ).scalar_one_or_none()

    assert user is None, "Seeding must not create a demo user without DEMO_USER_PASSWORD"


async def test_demo_mode_seeds_a_runnable_host(prepare_database, demo_mode):
    async with async_session() as db:
        await db.execute(delete(Host).where(Host.name == DEMO_HOST_NAME))
        await db.execute(delete(User).where(User.email == DEMO_USER_EMAIL))
        await db.commit()

    async with async_session() as db:
        await seed_demo_users(db)
        await seed_demo_host(db)
        await db.commit()

    async with async_session() as db:
        host = (
            await db.execute(select(Host).where(Host.name == DEMO_HOST_NAME))
        ).scalar_one_or_none()

    assert host is not None, "DEMO_MODE=true must seed a target host for Attack Lab"
    assert host.status == "online"
    assert host.created_by is not None


async def test_seeding_is_a_noop_without_demo_mode(prepare_database, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "testing", False)

    async with async_session() as db:
        await db.execute(delete(Host).where(Host.name == DEMO_HOST_NAME))
        await db.execute(delete(User).where(User.email == DEMO_USER_EMAIL))
        await db.commit()

    async with async_session() as db:
        await seed_demo_users(db)
        await seed_demo_host(db)
        await db.commit()

    async with async_session() as db:
        user = (
            await db.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        ).scalar_one_or_none()
        host = (
            await db.execute(select(Host).where(Host.name == DEMO_HOST_NAME))
        ).scalar_one_or_none()

    assert user is None
    assert host is None
