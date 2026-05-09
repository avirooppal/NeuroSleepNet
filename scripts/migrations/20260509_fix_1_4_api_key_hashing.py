"""
Fix 1.4 Migration: Mark existing API keys as legacy SHA256 (v1).

Run this AFTER applying Alembic migration 009_add_api_key_hash_version.

This script is idempotent: running it twice has no additional effect.
"""
import os
import asyncio
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Ensure we can import backend models
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "distributed", "backend"))

from app.models.base import Base
from app.models.api_key import ApiKey
from app.config import settings


async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async with AsyncSession(engine) as session:
        # Idempotent: only touch rows that don't already have a version set
        stmt = (
            update(ApiKey)
            .where(ApiKey.hash_version.is_(None) | (ApiKey.hash_version == ""))
            .values(hash_version="v1")
        )
        result = await session.execute(stmt)
        await session.commit()
        print(f"[+] Marked {result.rowcount} legacy API keys as hash_version=v1 (SHA256).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
