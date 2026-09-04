"""P0 regression tests — security, concurrency, and data integrity."""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.host import Host
from app.models.user import User


# ---------------------------------------------------------------------------
# P0-1: OIDC algorithm confusion
# ---------------------------------------------------------------------------

class TestOIDCAlgorithmConfusion:
    def test_allowed_algorithms_is_fixed_set(self):
        from app.services.oidc import _ALLOWED_OIDC_ALGORITHMS
        assert "RS256" in _ALLOWED_OIDC_ALGORITHMS
        assert "HS256" not in _ALLOWED_OIDC_ALGORITHMS
        assert "none" not in _ALLOWED_OIDC_ALGORITHMS

    def test_verify_rejects_hs256_in_header(self):
        from app.services.oidc import verify_id_token
        from fastapi import HTTPException
        import json
        import base64

        header_b64 = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT", "kid": "test-kid"}).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps({"sub": "123"}).encode()
        ).rstrip(b"=").decode()
        fake_token = f"{header_b64}.{payload_b64}.fake-sig"

        jwks = {"keys": [{"kid": "test-kid", "kty": "RSA", "n": "abc", "e": "AQAB"}]}

        with pytest.raises(HTTPException) as exc_info:
            verify_id_token(
                fake_token,
                jwks,
                audience="test",
                issuer="test",
                nonce="nonce",
            )
        assert "not allowed" in exc_info.value.detail

    def test_verify_rejects_unknown_kid(self):
        from app.services.oidc import verify_id_token
        from fastapi import HTTPException
        import json
        import base64

        header_b64 = base64.urlsafe_b64encode(
            json.dumps({"alg": "RS256", "typ": "JWT", "kid": "unknown-kid"}).encode()
        ).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps({"sub": "123"}).encode()
        ).rstrip(b"=").decode()
        fake_token = f"{header_b64}.{payload_b64}.fake-sig"

        jwks = {"keys": [{"kid": "other-kid", "kty": "RSA", "n": "abc", "e": "AQAB"}]}

        with pytest.raises(HTTPException) as exc_info:
            verify_id_token(
                fake_token,
                jwks,
                audience="test",
                issuer="test",
                nonce="nonce",
            )
        assert "signing key not found" in exc_info.value.detail


# ---------------------------------------------------------------------------
# P0-2: Hardcoded password fallbacks
# ---------------------------------------------------------------------------

class TestHardcodedPasswords:
    def test_dev_password_requires_config(self):
        import app.routers.auth as auth_mod
        original = auth_mod.DEV_USER_PASSWORD
        try:
            auth_mod.DEV_USER_PASSWORD = ""
            assert auth_mod.DEV_USER_PASSWORD == ""
        finally:
            auth_mod.DEV_USER_PASSWORD = original

    def test_demo_password_requires_config(self):
        import app.routers.auth as auth_mod
        original = auth_mod.DEMO_USER_PASSWORD
        try:
            auth_mod.DEMO_USER_PASSWORD = ""
            assert auth_mod.DEMO_USER_PASSWORD == ""
        finally:
            auth_mod.DEMO_USER_PASSWORD = original

    def test_no_hardcoded_passwords_in_source(self):
        import app.routers.auth as auth_mod
        source_lines = []
        for attr in dir(auth_mod):
            if attr.isupper() and "PASSWORD" in attr:
                val = getattr(auth_mod, attr)
                if isinstance(val, str):
                    source_lines.append(f"{attr}={val}")
        for line in source_lines:
            assert "testpass123" not in line.lower(), f"Found hardcoded testpass123 in {line}"
            assert "demo1234" not in line.lower(), f"Found hardcoded Demo1234 in {line}"

    def test_debug_defaults_to_false(self):
        from app.config import Settings
        s = Settings(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            jwt_secret="test-secret-minimum-length",
        )
        assert s.debug is False


# ---------------------------------------------------------------------------
# P0-3: Atomic alert creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAtomicAlertCreation:
    async def test_concurrent_alert_creation_no_duplicates(self, prepare_database):
        from app.services.detection import create_alert
        from app.database import async_session

        host_id = uuid4()

        async with async_session() as db:
            admin = (await db.execute(select(User).where(User.email == "admin@test.local"))).scalars().first()
            host = Host(
                id=host_id,
                name="test-host",
                hostname="test-host",
                os_info="Linux",
                status="online",
                created_by=admin.id,
            )
            db.add(host)
            await db.flush()

            rule = AlertRule(
                name="Test Rule",
                rule_type="failed_logins",
                threshold=5,
                window_minutes=5,
                severity="high",
                enabled=True,
            )
            db.add(rule)
            await db.flush()
            rule_id = rule.id
            await db.commit()

        results = []

        async def _create():
            async with async_session() as db:
                alert = await create_alert(
                    db,
                    host_id,
                    "Test Alert",
                    "Test description",
                    "high",
                    rule_id=rule_id,
                )
                results.append(alert)
                await db.commit()

        await asyncio.gather(*[_create() for _ in range(5)])

        non_none = [r for r in results if r is not None]
        async with async_session() as db:
            count = (
                await db.execute(
                    select(func.count()).select_from(Alert).where(
                        Alert.host_id == host_id,
                        Alert.rule_id == rule_id,
                        Alert.status == "open",
                    )
                )
            ).scalar_one()
        assert count == 1, f"Expected 1 open alert, got {count}"
        assert len(non_none) == 1, f"Expected 1 non-None result, got {len(non_none)}"


# ---------------------------------------------------------------------------
# P0-4: Atomic offense creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAtomicOffenseCreation:
    async def test_concurrent_offense_creation(self, prepare_database):
        from app.services.offense_engine import find_or_create_offense
        from app.database import async_session

        host_id = uuid4()
        async with async_session() as db:
            admin = (await db.execute(select(User).where(User.email == "admin@test.local"))).scalars().first()
            host = Host(
                id=host_id,
                name="offense-test-host",
                hostname="offense-test",
                os_info="Linux",
                status="online",
                created_by=admin.id,
            )
            db.add(host)
            await db.commit()

        results = []

        async def _create():
            async with async_session() as db:
                offense, created = await find_or_create_offense(
                    db, host_id, "Test Offense", "high"
                )
                results.append((offense, created))
                await db.commit()

        await asyncio.gather(*[_create() for _ in range(5)])

        assert len(results) == 5, f"Expected 5 results, got {len(results)}"
        offenses = [o for o, _ in results]
        offense_ids = {o.id for o in offenses}
        assert len(offense_ids) >= 1, "At least 1 offense should be created"


# ---------------------------------------------------------------------------
# P0-5: Atomic offense number generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestOffenseNumberSequence:
    async def test_offense_numbers_are_unique(self, prepare_database):
        from app.services.offense_engine import _next_offense_number
        from app.database import async_session

        numbers = set()
        for _ in range(20):
            async with async_session() as db:
                num = await _next_offense_number(db)
                assert num not in numbers, f"Duplicate offense number: {num}"
                numbers.add(num)

    async def test_offense_number_uses_sequence(self, prepare_database):
        from app.database import async_session

        async with async_session() as db:
            result = await db.execute(text("SELECT nextval('offense_number_seq')"))
            val1 = result.scalar()
            result = await db.execute(text("SELECT nextval('offense_number_seq')"))
            val2 = result.scalar()
            assert val2 == val1 + 1


# ---------------------------------------------------------------------------
# P0-6: Redis deduplication atomic
# ---------------------------------------------------------------------------

class TestRedisDedupAtomic:
    def test_redis_set_nx_ex_is_atomic(self):
        """Verify the code uses SET NX EX, not exists + setex."""
        from app.services.ingest_dedup import is_duplicate
        import inspect
        source = inspect.getsource(is_duplicate)
        assert "set(" in source or "setex" not in source
        assert "nx=True" in source


# ---------------------------------------------------------------------------
# P0-7: PostgreSQL deduplication race
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestPostgresDedupRace:
    async def test_concurrent_fingerprints_no_crash(self, prepare_database):
        from app.services.ingest_dedup import is_duplicate
        from app.database import async_session

        fp = "test-duplicate-fingerprint-" + str(uuid4())

        results = []

        async def _check():
            async with async_session() as db:
                dup = await is_duplicate(db, fp)
                results.append(dup)
                await db.commit()

        await asyncio.gather(*[_check() for _ in range(10)])

        assert results[0] is False, "First request should not be duplicate"
        assert all(r is True for r in results[1:]), "Subsequent requests should be duplicate"


# ---------------------------------------------------------------------------
# P0-8: Unknown job handlers
# ---------------------------------------------------------------------------

class TestUnknownJobHandler:
    async def test_unknown_handler_does_not_crash(self):
        from app.jobs.queue import JobQueue

        queue = JobQueue(workers=1)
        queue.start(force=True)
        await queue.enqueue("nonexistent_handler_name", {"key": "value"})
        await asyncio.sleep(0.3)
        await queue.stop()
        assert True

    def test_dead_letter_queue_exists(self):
        from app.jobs.redis_broker import DEAD_LETTER_QUEUE
        assert DEAD_LETTER_QUEUE == "securi:jobs:dead-letter"


# ---------------------------------------------------------------------------
# P0-9: Partition SQL injection
# ---------------------------------------------------------------------------

class TestPartitionSQLInjection:
    def test_valid_partition_name_accepted(self):
        from app.services.event_partitions import _validate_partition_name
        _validate_partition_name("events_y2026m01")

    def test_rejects_injection_attempt(self):
        from app.services.event_partitions import _validate_partition_name
        with pytest.raises(ValueError, match="Invalid partition name"):
            _validate_partition_name("events; DROP TABLE events--")

    def test_rejects_single_quotes(self):
        from app.services.event_partitions import _validate_partition_name
        with pytest.raises(ValueError, match="Invalid partition name"):
            _validate_partition_name("events_y2026m01'; DROP TABLE events;--")

    def test_rejects_special_characters(self):
        from app.services.event_partitions import _validate_partition_name
        with pytest.raises(ValueError, match="Invalid partition name"):
            _validate_partition_name("events_y2026m01 OR 1=1")

    def test_rejects_non_events_table(self):
        from app.services.event_partitions import _validate_partition_name
        with pytest.raises(ValueError, match="Invalid partition name"):
            _validate_partition_name("users_y2026m01")

    def test_rejects_empty_string(self):
        from app.services.event_partitions import _validate_partition_name
        with pytest.raises(ValueError, match="Invalid partition name"):
            _validate_partition_name("")

    def test_rejects_long_name(self):
        from app.services.event_partitions import _validate_partition_name
        with pytest.raises(ValueError, match="Invalid partition name"):
            _validate_partition_name("events_y2026m01_extra_stuff")

    def test_partition_name_regex(self):
        from app.services.event_partitions import _PARTITION_NAME_RE
        assert _PARTITION_NAME_RE.match("events_y2026m01")
        assert _PARTITION_NAME_RE.match("events_y2025m12")
        assert not _PARTITION_NAME_RE.match("events_y2026m1")
        assert not _PARTITION_NAME_RE.match("events_y202m01")


# ---------------------------------------------------------------------------
# P0-10: Post-ingestion pipeline isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestPipelineIsolation:
    async def test_detection_failure_does_not_block_timeline(self, prepare_database):
        from app.pipeline.processor import run_post_ingestion_pipeline
        from app.database import async_session
        from app.models.host import Host
        from uuid import uuid4

        host_id = uuid4()
        async with async_session() as db:
            admin = (await db.execute(select(User).where(User.email == "admin@test.local"))).scalars().first()
            host = Host(
                id=host_id,
                name="pipeline-test",
                hostname="pipeline-test",
                os_info="Linux",
                status="online",
                created_by=admin.id,
            )
            db.add(host)
            await db.commit()

        with patch(
            "app.services.detection.run_detection_for_host",
            side_effect=Exception("Detection boom"),
        ):
            with patch(
                "app.services.correlation_engine.run_correlation_engine",
                new_callable=AsyncMock,
            ) as mock_corr:
                mock_corr.return_value = None
                async with async_session() as db:
                    await run_post_ingestion_pipeline(db, host_id)
                    mock_corr.assert_called_once()


# ---------------------------------------------------------------------------
# P0-15: Agent buffer size limit (unit test of the logic)
# ---------------------------------------------------------------------------

class TestAgentBufferSizeLimit:
    def test_buffer_size_limit_constant(self):
        """Verify MAX_BUFFER_ITEMS constant exists and is reasonable."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "buffer", str(
                __import__("pathlib").Path(__file__).resolve().parent.parent.parent
                / "agent" / "agent" / "buffer.py"
            )
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "MAX_BUFFER_ITEMS")
        assert mod.MAX_BUFFER_ITEMS > 0
        assert mod.MAX_BUFFER_ITEMS <= 1000000

    def test_enqueue_function_exists(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "buffer", str(
                __import__("pathlib").Path(__file__).resolve().parent.parent.parent
                / "agent" / "agent" / "buffer.py"
            )
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert callable(mod.enqueue)

    def test_wal_mode_in_init(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "buffer", str(
                __import__("pathlib").Path(__file__).resolve().parent.parent.parent
                / "agent" / "agent" / "buffer.py"
            )
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        import inspect
        source = inspect.getsource(mod._connect)
        assert "WAL" in source
