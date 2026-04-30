import asyncio
import uuid
import hashlib
from sqlalchemy import select
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.project import Project
from app.deps import AsyncSessionLocal
from app.utils.crypto import generate_api_key

async def setup():
    async with AsyncSessionLocal() as session:
        # Create benchmark user
        stmt = select(User).where(User.email == "benchmark@nsn.io")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email="benchmark@nsn.io",
                plan="pro", # High rate limit (1000 req/min)
                is_active=True
            )
            session.add(user)
            await session.flush()
            print(f"Created benchmark user: {user.id}")
        else:
            user.plan = "pro"
            print(f"User exists, updated plan to pro: {user.id}")

        # Create API key
        stmt = select(ApiKey).where(ApiKey.user_id == user.id)
        result = await session.execute(stmt)
        api_key_model = result.scalar_one_or_none()
        
        plaintext, hashed, prefix = generate_api_key()
        
        if not api_key_model:
            api_key_model = ApiKey(
                user_id=user.id,
                key_prefix=prefix,
                key_hash=hashed,
                name="Benchmark Key"
            )
            session.add(api_key_model)
            await session.flush()
            print(f"Created benchmark API key. Plaintext: {plaintext}")
        else:
            api_key_model.key_prefix = prefix
            api_key_model.key_hash = hashed
            print(f"Updated benchmark API key. Plaintext: {plaintext}")
        
        # Create project
        stmt = select(Project).where(Project.name == "ab-test-harness")
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            project = Project(
                user_id=user.id,
                name="ab-test-harness",
                settings={"attention_weights": {"w_sim": 0.45, "w_rec": 0.15, "w_con": 0.25, "w_fb": 0.15}}
            )
            session.add(project)
            await session.flush()
            print("Created benchmark project")

        await session.commit()
        print("Setup complete.")

if __name__ == "__main__":
    asyncio.run(setup())
