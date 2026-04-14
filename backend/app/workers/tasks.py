import asyncio
import logging
from celery import shared_task
from sqlalchemy import select

from ..deps import AsyncSessionLocal
from ..models.user import User
from ..core.sleep_engine import run_sleep_phase

logger = logging.getLogger(__name__)


@shared_task
def run_nightly_sleep():
    """
    Periodic task to trigger the sleep phase for all users.
    """
    return asyncio.run(_run_all_sleep())


async def _run_all_sleep():
    """
    Async helper for consolidation across all users.
    """
    async with AsyncSessionLocal() as session:
        # Find all active users
        query = select(User).where(User.is_active == True)
        result = await session.execute(query)
        users = result.scalars().all()
        
        results = []
        for user in users:
            try:
                # Use current session for run_sleep_phase
                # But it has its own commit/rollback inside core
                stats = await run_sleep_phase(session, str(user.id))
                results.append({"user_id": str(user.id), "status": "success", "stats": stats})
            except Exception as e:
                logger.error(f"Sleep failed for user {user.id}: {e}")
                results.append({"user_id": str(user.id), "status": "failed", "error": str(e)})
                
        return results


@shared_task
def process_memory_re_embedding(memory_id: str):
    """
    Async task to update an embedding if content is refreshed.
    """
    # ... logic here ...
    pass
