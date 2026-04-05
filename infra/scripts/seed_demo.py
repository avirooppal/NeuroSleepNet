import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import sys
import os

# Add backend to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

from app.config import settings
from app.models.user import User
from app.models.task import Task
from app.models.memory import Memory
from app.utils.crypto import get_password_hash
from app.core.embeddings import get_embedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use host-side DB URL for seeding from host
DATABASE_URL = settings.DATABASE_URL.replace("db:5432", "localhost:5433")

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Create Demo User
        logger.info("Creating demo user...")
        user_query = select(User).where(User.email == "demo@neurosleepnet.com")
        result = await session.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email="demo@neurosleepnet.com",
                password_hash=get_password_hash("demo123"),
                plan="paid"  # Paid for unlimited ops during demo
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            logger.info("✅ Demo user created: demo@neurosleepnet.com / demo123")
        else:
            logger.info("⚠️ Demo user already exists.")

        # 2. Create Tasks
        logger.info("Creating sample tasks...")
        tasks = ["Tech Stack Research", "Marketing Strategy", "Daily Journal"]
        task_objs = []
        for name in tasks:
            task_query = select(Task).where(Task.name == name, Task.user_id == user.id)
            result = await session.execute(task_query)
            t = result.scalar_one_or_none()
            if not t:
                t = Task(user_id=user.id, name=name)
                session.add(t)
                task_objs.append(t)
            else:
                task_objs.append(t)
        
        await session.commit()
        for t in task_objs:
            await session.refresh(t)
        logger.info(f"✅ {len(task_objs)} Tasks ready.")

        # 3. Add memories with embeddings
        logger.info("Adding sample memories (this may take a moment for embeddings)...")
        sample_memories = [
            ("We use FastAPI for the backend and Vite for the frontend.", task_objs[0].id),
            ("The memory engine uses pgvector for semantic search.", task_objs[0].id),
            ("Our primary target audience is solo developers and AI researchers.", task_objs[1].id),
            ("Had a great coffee today and read about neural plasticity.", task_objs[2].id),
        ]

        for content, t_id in sample_memories:
            # Check if exists
            mem_query = select(Memory).where(Memory.content == content, Memory.user_id == user.id)
            result = await session.execute(mem_query)
            if not result.scalar_one_or_none():
                emb = await get_embedding(content)
                m = Memory(
                    user_id=user.id,
                    task_id=t_id,
                    content=content,
                    embedding=emb,
                    consolidation_score=0.5
                )
                session.add(m)
        
        await session.commit()
        logger.info("✅ Sample memories seeded.")
        logger.info("🚀 Seeding complete! You can now login with demo@neurosleepnet.com")


if __name__ == "__main__":
    asyncio.run(seed())
