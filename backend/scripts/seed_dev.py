import asyncio
import uuid
import hashlib
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# We use relative imports in the app, but here we need to handle paths
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.models.api_key import ApiKey
from app.utils.crypto import get_password_hash
from app.config import settings

async def seed():
    print(f"Connecting to {settings.DATABASE_URL}...")
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # 1. Create Dev User
        res = await session.execute(select(User).where(User.email == "dev@neurosleepnet.io"))
        user = res.scalars().first()
        
        if not user:
            print("Creating dev user...")
            user = User(
                id=uuid.uuid4(),
                email="dev@neurosleepnet.io",
                password_hash=get_password_hash("nsn-dev-123"),
                plan="pro",
                is_active=True
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            print("Dev user already exists.")
        
        # 2. Key creation is now handled by keygen.py for security.
        # Check if any keys exist
        res = await session.execute(select(ApiKey).where(ApiKey.user_id == user.id))
        key = res.scalars().first()
        if not key:
            print("No API keys found for dev user. Run `python scripts/keygen.py` to create one.")

if __name__ == "__main__":
    asyncio.run(seed())
