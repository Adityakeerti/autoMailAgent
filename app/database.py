from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

import ssl
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

db_url = settings.DATABASE_URL
if db_url.startswith("sqlite://"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

connect_args = {}
if "sqlite" in db_url:
    connect_args["check_same_thread"] = False
elif "asyncpg" in db_url:
    # asyncpg does NOT accept sslmode/ssl as URL query params.
    # Strip them out and pass ssl context via connect_args instead.
    parsed = urlparse(db_url)
    qs = parse_qs(parsed.query)
    qs.pop("sslmode", None)
    qs.pop("ssl", None)
    qs.pop("channel_binding", None)
    clean_url = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
    db_url = clean_url
    ssl_ctx = ssl.create_default_context()
    connect_args["ssl"] = ssl_ctx

engine = create_async_engine(db_url, echo=False, connect_args=connect_args)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    import app.models  # Register all models with Base
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE context_profile ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);"))
        except Exception:
            try:
                await conn.execute(text("ALTER TABLE context_profile ADD COLUMN full_name VARCHAR(255);"))
            except Exception:
                pass

