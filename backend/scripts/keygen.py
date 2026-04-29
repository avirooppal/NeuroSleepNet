import asyncio
import uuid
import hashlib
import secrets
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.models.api_key import ApiKey
from app.config import settings

async def generate_key(email: str = "dev@neurosleepnet.io", name: str = "Default Key"):
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # 1. Find User
        res = await session.execute(select(User).where(User.email == email))
        user = res.scalars().first()
        
        if not user:
            print(f"User {email} not found. Run seed_dev.py first.")
            return
        
        # 2. Generate Random Key
        # Format: nsn_sk_<32_random_chars>
        raw_key = "nsn_sk_" + secrets.token_urlsafe(24)
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:10] # nsn_sk_...
        
        # 3. Store Key
        new_key = ApiKey(
            user_id=user.id,
            key_hash=hashed,
            key_prefix=prefix,
            name=name,
            is_active=True
        )
        session.add(new_key)
        await session.commit()
        
        print("─────────────────────────────────────────────────────────────")
        print("NEUROSLEEPNET API KEY GENERATED")
        print("─────────────────────────────────────────────────────────────")
        print(f"User:  {email}")
        print(f"Key:   {raw_key}")
        print("─────────────────────────────────────────────────────────────")
        print("SAVE THIS KEY NOW. It will never be shown again.")
        print("Use it in your SDK: nsn.init(api_key='...')")
        print("─────────────────────────────────────────────────────────────")

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "dev@neurosleepnet.io"
    asyncio.run(generate_key(email))
