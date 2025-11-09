from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from app.config import DATABASE_URL
from app.db.base import Base


engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
