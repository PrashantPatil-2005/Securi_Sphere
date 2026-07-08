from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.core.db_pool import engine_options

engine = create_async_engine(settings.database_url, echo=settings.sql_echo, **engine_options())
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

read_engine = None
read_async_session: async_sessionmaker[AsyncSession] | None = None

if settings.database_read_url.strip():
    read_engine = create_async_engine(
        settings.database_read_url,
        echo=settings.sql_echo,
        **engine_options(),
    )
    read_async_session = async_sessionmaker(read_engine, class_=AsyncSession, expire_on_commit=False)


def read_replica_configured() -> bool:
    return read_async_session is not None


def read_session_factory() -> async_sessionmaker[AsyncSession]:
    return read_async_session or async_session


async def dispose_engines() -> None:
    await engine.dispose()
    if read_engine is not None:
        await read_engine.dispose()


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_read() -> AsyncGenerator[AsyncSession, None]:
    """Read-only session — uses read replica when DATABASE_READ_URL is set."""
    async with read_session_factory()() as session:
        yield session
