import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db
from ...models.user import User
from ...models.audit_log import AuditLog
from ...core.sleep_engine import run_sleep_phase
from .auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sleep(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger the 'Sleep Phase' for memory consolidation.
    Typically run nightly via Celery, but can be forced.
    """
    # For a long-running process, this should ideally be a Celery task.
    # For now, we'll run it directly (blocking the API until done).
    result = await run_sleep_phase(db, current_user.id)
    return result


@router.get("/history", response_model=List[dict])
async def sleep_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Get history of past sleep runs for the user.
    """
    query = select(AuditLog).where(
        AuditLog.user_id == current_user.id,
        AuditLog.action == "sleep.phase.run"
    ).order_by(AuditLog.created_at.desc()).limit(10)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            "id": str(log.id),
            "date": log.created_at,
            "metadata": log.metadata
        } for log in logs
    ]
