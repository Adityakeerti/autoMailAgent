import asyncio
import ssl
from logging.config import fileConfig
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.config import settings
from app.database import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_db_url() -> str:
    """
    Normalize DATABASE_URL for asyncpg:
    - Replace postgresql:// -> postgresql+asyncpg://
    - Replace sqlite:// -> sqlite+aiosqlite://
    - Strip SSL query params unsupported by asyncpg (sslmode, ssl, channel_binding)
    """
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    if "asyncpg" in url:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        qs.pop("sslmode", None)
        qs.pop("ssl", None)
        qs.pop("channel_binding", None)
        url = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))

    return url


def run_migrations_offline() -> None:
    url = _get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    db_url = _get_db_url()
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = db_url

    connect_args = {}
    if "asyncpg" in db_url:
        ssl_ctx = ssl.create_default_context()
        connect_args["ssl"] = ssl_ctx

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
