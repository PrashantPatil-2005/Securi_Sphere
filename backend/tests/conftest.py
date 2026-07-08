"""Shared fixtures for unit and HTTP integration tests."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

# Must be set before app import so Settings and lifespan behave for tests.
os.environ["TESTING"] = "true"
os.environ["REDIS_URL"] = ""
os.environ["JOB_QUEUE_BACKEND"] = "memory"
os.environ["WS_PUBSUB_BACKEND"] = "memory"
os.environ.setdefault("JWT_SECRET", "test-secret-key-minimum-length-required")
os.environ.setdefault("ASYNC_EVENT_PIPELINE", "false")

from app.database import async_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routers.auth import seed_roles  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.detection import seed_alert_rules  # noqa: E402
from app.services.migrate import migrate_schema  # noqa: E402

TEST_USERS = {
    "admin@test.local": "admin",
    "analyst@test.local": "analyst",
    "viewer@test.local": "viewer",
}
TEST_PASSWORD = "testpass123"


_db_seeded = False


@pytest_asyncio.fixture
async def prepare_database():
    global _db_seeded
    from app.database import dispose_engines, engine

    await dispose_engines()
    try:
        if not _db_seeded:
            await migrate_schema()
            _db_seeded = True

        async with async_session() as db:
            await seed_roles(db)
            await seed_alert_rules(db)
            roles = {r.name: r for r in (await db.execute(select(Role))).scalars().all()}
            for email, role_name in TEST_USERS.items():
                existing = (
                    await db.execute(select(User).where(User.email == email))
                ).scalar_one_or_none()
                if existing:
                    existing.hashed_password = hash_password(TEST_PASSWORD)
                    existing.role_id = roles[role_name].id
                    existing.is_active = True
                    existing.failed_login_attempts = 0
                    existing.locked_until = None
                else:
                    db.add(
                        User(
                            email=email,
                            hashed_password=hash_password(TEST_PASSWORD),
                            role_id=roles[role_name].id,
                            full_name=role_name.capitalize(),
                        )
                    )
            await db.commit()
    except Exception as exc:
        pytest.skip(f"Database unavailable for integration tests: {exc}")
    yield


@pytest_asyncio.fixture
async def client(prepare_database):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def _login(ac: AsyncClient, email: str) -> AsyncClient:
    res = await ac.post(
        "/api/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert res.status_code == 200, res.text
    return ac


async def _role_client(email: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await _login(ac, email)
        yield ac


@pytest_asyncio.fixture
async def admin_client(prepare_database):
    async for ac in _role_client("admin@test.local"):
        yield ac


@pytest_asyncio.fixture
async def analyst_client(prepare_database):
    async for ac in _role_client("analyst@test.local"):
        yield ac


@pytest_asyncio.fixture
async def viewer_client(prepare_database):
    async for ac in _role_client("viewer@test.local"):
        yield ac
