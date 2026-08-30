"""Real PostgreSQL concurrency tests.

These tests FAIL if PostgreSQL is not available (not skipped).
"""
import asyncio
import pytest
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.database import async_session
from app.models.alert import Alert
from app.models.host import Host
from app.models.role import Role
from app.models.siem import Offense
from app.models.user import User
from app.models.ingest_dedup import IngestDedup
from app.services.ingest_dedup import event_fingerprint
from uuid import uuid4
from datetime import datetime, timezone

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_concurrent_alert_creation_no_duplicates(prepare_database):
    async with async_session() as db:
        host = Host(name="concurrency-host", status="online", created_by=uuid4())
        db.add(host)
        await db.flush()
        host_id = host.id
        await db.commit()

    async def insert_alert(idx):
        async with async_session() as db:
            stmt = (
                pg_insert(Alert)
                .values(
                    host_id=host_id,
                    severity="high",
                    title="Concurrent Test Alert",
                    description=f"attempt {idx}",
                    status="open",
                )
                .on_conflict_do_nothing(
                    index_elements=["host_id", "title"],
                )
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

    results = await asyncio.gather(*[insert_alert(i) for i in range(20)])
    inserted = sum(1 for r in results if r > 0)
    assert inserted == 1

    async with async_session() as db:
        count = (
            await db.execute(
                select(Alert).where(
                    Alert.host_id == host_id,
                    Alert.title == "Concurrent Test Alert",
                )
            )
        ).scalars().all()
        assert len(count) == 1


@pytest.mark.asyncio
async def test_concurrent_offense_creation(prepare_database):
    async with async_session() as db:
        host = Host(name="offense-concurrency-host", status="online", created_by=uuid4())
        db.add(host)
        await db.flush()
        host_id = host.id
        await db.commit()

    async def try_create_offense(idx):
        async with async_session() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Offense)
                .where(
                    Offense.host_id == host_id,
                    Offense.status.in_(["open", "investigating"]),
                )
                .order_by(Offense.updated_at.desc())
                .limit(1)
                .with_for_update()
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.updated_at = now
                await db.commit()
                return False

            offense_num_result = await db.execute(
                text("SELECT nextval('offense_number_seq')")
            )
            offense_number = offense_num_result.scalar_one()
            offense = Offense(
                offense_number=offense_number,
                host_id=host_id,
                title="Concurrent Offense",
                risk_level="high",
                status="open",
                event_count=0,
                alert_count=0,
                related_hosts=[str(host_id)],
                related_users=[],
                timeline=[],
            )
            db.add(offense)
            await db.commit()
            return True

    results = await asyncio.gather(*[try_create_offense(i) for i in range(10)])
    created = sum(1 for r in results if r is True)
    assert created == 1

    async with async_session() as db:
        offenses = (
            await db.execute(
                select(Offense).where(Offense.host_id == host_id)
            )
        ).scalars().all()
        assert len(offenses) == 1


@pytest.mark.asyncio
async def test_offense_numbers_are_unique(prepare_database):
    async with async_session() as db:
        host = Host(name="offense-unique-host", status="online", created_by=uuid4())
        db.add(host)
        await db.flush()
        host_id = host.id
        await db.commit()

    async def create_offense(idx):
        async with async_session() as db:
            result = await db.execute(
                text("SELECT nextval('offense_number_seq')")
            )
            offense_number = result.scalar_one()
            offense = Offense(
                offense_number=offense_number,
                host_id=host_id,
                title=f"Unique Offense {idx}",
                risk_level="medium",
                status="open",
                event_count=0,
                alert_count=0,
                related_hosts=[str(host_id)],
                related_users=[],
                timeline=[],
            )
            db.add(offense)
            await db.commit()
            return offense_number

    numbers = await asyncio.gather(*[create_offense(i) for i in range(50)])
    assert len(numbers) == 50
    assert len(set(numbers)) == 50


@pytest.mark.asyncio
async def test_offense_number_uses_sequence(prepare_database):
    async with async_session() as db:
        result = await db.execute(
            text("SELECT nextval('offense_number_seq')")
        )
        first = result.scalar_one()
        result2 = await db.execute(
            text("SELECT nextval('offense_number_seq')")
        )
        second = result2.scalar_one()
        assert second == first + 1


@pytest.mark.asyncio
async def test_concurrent_fingerprints_no_crash(prepare_database):
    async with async_session() as db:
        host = Host(name="fingerprint-concurrency-host", status="online", created_by=uuid4())
        db.add(host)
        await db.flush()
        host_id = host.id
        await db.commit()

    fingerprint = event_fingerprint(host_id, datetime.now(timezone.utc), "ssh_login_failure", "test log")

    async def insert_dedup(idx):
        async with async_session() as db:
            stmt = (
                pg_insert(IngestDedup)
                .values(fingerprint=fingerprint)
                .on_conflict_do_nothing(index_elements=["fingerprint"])
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

    results = await asyncio.gather(*[insert_dedup(i) for i in range(20)])
    inserted = sum(1 for r in results if r > 0)
    assert inserted == 1

    async with async_session() as db:
        rows = (
            await db.execute(
                select(IngestDedup).where(IngestDedup.fingerprint == fingerprint)
            )
        ).scalars().all()
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_concurrent_different_fingerprints(prepare_database):
    async with async_session() as db:
        host = Host(name="diff-fp-host", status="online", created_by=uuid4())
        db.add(host)
        await db.flush()
        host_id = host.id
        await db.commit()

    async def insert_dedup(idx):
        fp = event_fingerprint(host_id, datetime.now(timezone.utc), f"event_{idx}", f"log_{idx}")
        async with async_session() as db:
            stmt = (
                pg_insert(IngestDedup)
                .values(fingerprint=fp)
                .on_conflict_do_nothing(index_elements=["fingerprint"])
            )
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

    results = await asyncio.gather(*[insert_dedup(i) for i in range(10)])
    inserted = sum(1 for r in results if r > 0)
    assert inserted == 10


@pytest.mark.asyncio
async def test_concurrent_refresh_token_rotation(prepare_database):
    from app.security import hash_password, create_refresh_token, hash_token
    from app.models.refresh_token import RefreshToken
    from app.models.user_session import UserSession

    async with async_session() as db:
        role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one()
        user = User(
            email="refresh_concurrent@test.local",
            hashed_password=hash_password("Test1234!"),
            role_id=role.id,
            full_name="Refresh Test",
            is_active=True,
        )
        db.add(user)
        await db.flush()
        user_id = user.id

        plain_token = create_refresh_token(str(user_id))
        token_hash_val = hash_token(plain_token)
        now = datetime.now(timezone.utc)
        rt = RefreshToken(
            user_id=user_id,
            token_hash=token_hash_val,
            expires_at=now.replace(year=now.year + 1),
            created_at=now,
        )
        db.add(rt)
        session = UserSession(
            user_id=user_id,
            refresh_token_hash=token_hash_val,
            expires_at=now.replace(year=now.year + 1),
        )
        db.add(session)
        await db.commit()

    async def attempt_refresh(idx):
        async with async_session() as db:
            result = await db.execute(
                select(RefreshToken)
                .where(RefreshToken.token_hash == hash_token(plain_token))
                .with_for_update()
            )
            stored = result.scalar_one_or_none()
            if not stored:
                return False
            await db.delete(stored)
            session_result = await db.execute(
                select(UserSession)
                .where(
                    UserSession.refresh_token_hash == hash_token(plain_token),
                    UserSession.revoked_at.is_(None),
                )
                .with_for_update()
            )
            sess = session_result.scalar_one_or_none()
            if not sess:
                await db.rollback()
                return False
            sess.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            return True

    results = await asyncio.gather(*[attempt_refresh(i) for i in range(5)])
    successes = sum(1 for r in results if r is True)
    assert successes == 1


@pytest.mark.asyncio
async def test_concurrent_password_reset(prepare_database):
    from app.security import hash_password, generate_reset_token, hash_token
    from app.models.password_reset import PasswordResetToken

    async with async_session() as db:
        role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one()
        user = User(
            email="reset_concurrent@test.local",
            hashed_password=hash_password("OldPass123!"),
            role_id=role.id,
            full_name="Reset Test",
            is_active=True,
        )
        db.add(user)
        await db.flush()
        user_id = user.id

        plain_token = generate_reset_token()
        token_hash_val = hash_token(plain_token)
        now = datetime.now(timezone.utc)
        prt = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash_val,
            expires_at=now.replace(hour=now.hour + 1),
        )
        db.add(prt)
        await db.commit()

    async def attempt_reset(idx):
        async with async_session() as db:
            from sqlalchemy import update as sa_update
            result = await db.execute(
                sa_update(PasswordResetToken)
                .where(
                    PasswordResetToken.token_hash == hash_token(plain_token),
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > datetime.now(timezone.utc),
                )
                .values(used_at=datetime.now(timezone.utc))
                .returning(PasswordResetToken.user_id)
            )
            row = result.first()
            if not row:
                await db.rollback()
                return False
            user_result = await db.execute(select(User).where(User.id == row[0]))
            u = user_result.scalar_one()
            u.hashed_password = hash_password(f"NewPass{idx}123!")
            await db.commit()
            return True

    results = await asyncio.gather(*[attempt_reset(i) for i in range(5)])
    successes = sum(1 for r in results if r is True)
    assert successes == 1
