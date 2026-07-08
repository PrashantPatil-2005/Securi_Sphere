"""Run Alembic migrations programmatically (sync driver)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import settings

logger = logging.getLogger(__name__)


def _sync_database_url() -> str:
    url = settings.database_url
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg2")
    return url


def alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", _sync_database_url())
    return cfg


def upgrade_head() -> None:
    command.upgrade(alembic_config(), "heads")
    logger.info("Alembic upgrade heads complete")


def current_revision() -> str | None:
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    engine = create_engine(_sync_database_url(), poolclass=None)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


async def upgrade_head_async() -> None:
    await asyncio.to_thread(upgrade_head)
