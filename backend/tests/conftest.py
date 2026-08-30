"""Shared fixtures for unit and HTTP integration tests.

Infrastructure policy (Phase 3O — no false-green CI):
  - If a test NEEDS PostgreSQL and PostgreSQL is unavailable → FAIL (not skip).
  - If a test NEEDS Redis and Redis is unavailable → FAIL (not skip).
  - Intentional skips are allowed (e.g. test marked @pytest.mark.skip).
  - Infrastructure failures are NOT intentional skips.
"""

import os
import socket

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

# ---------------------------------------------------------------------------
# Environment — must be set before any app import.
# ---------------------------------------------------------------------------
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("JOB_QUEUE_BACKEND", "memory")
os.environ.setdefault("WS_PUBSUB_BACKEND", "memory")
os.environ.setdefault("JWT_SECRET", "test-secret-key-minimum-length-required")
os.environ.setdefault("ASYNC_EVENT_PIPELINE", "false")

from app.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Infrastructure detection
# ---------------------------------------------------------------------------

def _pg_available() -> bool:
    url = settings.database_url
    if not url:
        return False
    try:
        host = url.split("@")[-1].split(":")[0] if "@" in url else "localhost"
        port = int(url.split(":")[-1].split("/")[0]) if ":" in url.split("@")[-1] else 5432
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False


def _redis_available() -> bool:
    url = settings.redis_url
    if not url:
        return False
    try:
        import redis as redis_sync
        r = redis_sync.Redis.from_url(url, socket_timeout=2)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


HAS_PG = _pg_available()
HAS_REDIS = _redis_available()

TEST_USERS = {
    "admin@test.local": "admin",
    "analyst@test.local": "analyst",
    "viewer@test.local": "viewer",
}
TEST_PASSWORD = "testpass123"

# Module-level flag to seed DB exactly once (avoids redundant migration runs).
_db_seeded = False
_db_failed = False


@pytest_asyncio.fixture
async def prepare_database():
    """Seed the database once per session. FAILS on infrastructure error."""
    global _db_seeded, _db_failed

    if _db_failed:
        pytest.fail(
            "PostgreSQL is not available. "
            "Start test services: docker compose -f docker-compose.test.yml up -d"
        )

    if not HAS_PG:
        _db_failed = True
        pytest.fail(
            "PostgreSQL is not available. "
            "Start test services: docker compose -f docker-compose.test.yml up -d"
        )

    from app.database import async_session, dispose_engines  # noqa: E402
    from app.models.role import Role  # noqa: E402
    from app.models.user import User  # noqa: E402
    from app.routers.auth import seed_roles  # noqa: E402
    from app.security import hash_password  # noqa: E402
    from app.services.detection import seed_alert_rules  # noqa: E402
    from app.services.migrate import migrate_schema  # noqa: E402

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
    except pytest.fail.Exception:
        raise
    except Exception as exc:
        _db_failed = True
        pytest.fail(f"Database setup failed: {exc}")
    yield


@pytest_asyncio.fixture
async def client(prepare_database):
    from app.main import app  # noqa: E402

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
    from app.main import app  # noqa: E402

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


# ---------------------------------------------------------------------------
# Redis fixtures — FAIL when Redis is unavailable
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def require_redis():
    """Yields a Redis connection or FAILS the test."""
    if not HAS_REDIS:
        pytest.fail(
            "Redis is not available. "
            "Start test services: docker compose -f docker-compose.test.yml up -d"
        )
    from redis.asyncio import Redis

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()
