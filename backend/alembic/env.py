from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app.models import *  # noqa: F401, F403

config = context.config
_sync_url = settings.database_url.replace("+asyncpg", "+psycopg2").replace("@localhost:", "@127.0.0.1:")
if "connect_timeout" not in _sync_url:
    sep = "&" if "?" in _sync_url else "?"
    _sync_url = f"{_sync_url}{sep}connect_timeout=10"
config.set_main_option("sqlalchemy.url", _sync_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_engine(url, poolclass=pool.NullPool, connect_args={"connect_timeout": 10})
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
