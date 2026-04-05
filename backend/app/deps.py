from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis.asyncio import Redis

from .config import settings

# Database setup
engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Redis setup
redis_client = Redis.from_url(str(settings.REDIS_URL), decode_responses=True)


async def get_redis() -> Redis:
    return redis_client
