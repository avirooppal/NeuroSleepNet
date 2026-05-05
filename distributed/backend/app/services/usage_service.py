import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.usage_log import UsageLog
from ..models.user import User
from ..utils.errors import PlanLimitError

logger = logging.getLogger(__name__)

# Plan Limits
PLAN_LIMITS = {
    "free": {
        "monthly_ops": 10000,
        "storage_bytes": 500 * 1024 * 1024,  # 500 MB
        "max_tasks": 10,
        "max_api_keys": 2
    },
    "paid": {
        "monthly_ops": float("inf"),
        "storage_bytes": 50 * 1024 * 1024 * 1024,  # 50 GB
        "max_tasks": float("inf"),
        "max_api_keys": float("inf")
    }
}


async def get_current_usage(session: AsyncSession, user_id: str) -> UsageLog:
    """
    Fetch or create usage log for current month.
    """
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    
    query = select(UsageLog).where(
        UsageLog.user_id == user_id,
        UsageLog.month == month
    )
    result = await session.execute(query)
    usage = result.scalar_one_or_none()
    
    if not usage:
        usage = UsageLog(user_id=user_id, month=month)
        session.add(usage)
        await session.commit()
        await session.refresh(usage)
        
    return usage


async def check_and_inc_usage(
    session: AsyncSession,
    user: User,
    op_type: str = "read",  # 'read' | 'write'
    bytes_inc: int = 0
) -> None:
    """
    Check if user is within plan limits and increment usage.
    """
    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
    usage = await get_current_usage(session, user.id)
    
    current_ops = usage.memory_reads + usage.memory_writes
    
    if current_ops >= limits["monthly_ops"]:
        raise PlanLimitError(
            f"Monthly limit of {limits['monthly_ops']:,} operations reached. "
            "Upgrade to Architect plan for unlimited operations."
        )
        
    if usage.storage_bytes + bytes_inc >= limits["storage_bytes"]:
        raise PlanLimitError(
            f"Storage limit of {limits['storage_bytes'] / (1024*1024):.1f} MB reached."
        )
        
    # Increment usage
    if op_type == "read":
        usage.memory_reads += 1
    else:
        usage.memory_writes += 1
        
    usage.storage_bytes += bytes_inc
    usage.updated_at = datetime.now(timezone.utc)
    
    await session.commit()
