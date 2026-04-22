"""
Celery task definitions for the `sleep` queue.

Queue: sleep
Workers: 1 (long-running, CPU-bound nightly batch)
Schedule: 0 3 * * *  (3am UTC, configurable via NSN_SLEEP_SCHEDULE)
"""
import logging
import os

from ...workers.celery_app import celery_app
from ...core.sleep_engine import run_sleep_phase, mini_consolidation, run_ttl_expiry

logger = logging.getLogger(__name__)


def _get_async_session():
    """Create a new async DB session for Celery task context."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    engine = create_async_engine(os.environ["DATABASE_URL"])
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="tasks.sleep.run_consolidation", bind=True)
def run_consolidation(self, user_id: str = None, project_id: str = None):
    """
    Full nightly sleep consolidation pass.
    If user_id is None, runs for ALL active users (nightly batch).
    """
    import asyncio

    async def _run():
        SessionLocal = _get_async_session()
        from sqlalchemy import select
        from ...models.user import User

        async with SessionLocal() as session:
            if user_id:
                users = [user_id]
            else:
                # Nightly batch — all users
                result = await session.execute(select(User.id))
                users = [str(row[0]) for row in result.fetchall()]

            results = []
            for uid in users:
                try:
                    result = await run_sleep_phase(
                        session=session,
                        user_id=uid,
                        project_id=project_id,
                        run_type="nightly" if not user_id else "manual",
                    )
                    results.append({"user_id": uid, **result})
                    logger.info(f"[Sleep] Consolidation complete for user {uid}: {result}")
                except Exception as e:
                    logger.error(f"[Sleep] Consolidation failed for user {uid}: {e}")
                    results.append({"user_id": uid, "status": "error", "error": str(e)})

            return results

    return asyncio.get_event_loop().run_until_complete(_run())


@celery_app.task(name="tasks.sleep.run_ttl_expiry", bind=True)
def run_ttl_expiry_task(self, user_id: str = None):
    """
    Standalone TTL expiry task — hard-delete all TTL-expired memory records.
    Can run independently of full consolidation.
    """
    import asyncio

    async def _run():
        SessionLocal = _get_async_session()
        from sqlalchemy import select
        from ...models.user import User

        async with SessionLocal() as session:
            if user_id:
                users = [user_id]
            else:
                result = await session.execute(select(User.id))
                users = [str(row[0]) for row in result.fetchall()]

            total_deleted = 0
            for uid in users:
                try:
                    deleted = await run_ttl_expiry(session, uid)
                    await session.commit()
                    total_deleted += deleted
                except Exception as e:
                    logger.error(f"[Sleep] TTL expiry failed for user {uid}: {e}")

            return {"deleted": total_deleted}

    return asyncio.get_event_loop().run_until_complete(_run())


@celery_app.task(name="tasks.sleep.mini_consolidation", bind=True)
def run_mini_consolidation(self, user_id: str, project_id: str = None):
    """
    Lightweight sync fallback — triggered when last sleep run was > 48h ago.
    Only runs TTL expiry + basic score decay. No full consolidation pass.
    """
    import asyncio

    async def _run():
        SessionLocal = _get_async_session()
        async with SessionLocal() as session:
            return await mini_consolidation(session, user_id, project_id)

    return asyncio.get_event_loop().run_until_complete(_run())
