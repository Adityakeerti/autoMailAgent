from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

db_url = settings.DATABASE_URL
if db_url.startswith("sqlite://"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

connect_args = {}
if "sqlite" in db_url:
    connect_args["check_same_thread"] = False

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
