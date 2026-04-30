import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db
from ...models.user import User
from ...models.memory import Memory
from ...models.usage_log import UsageLog
from ...models.audit_log import AuditLog
from ...schemas import dashboard as dashboard_schema
from ...services.usage_service import get_current_usage, PLAN_LIMITS
from .auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stats", response_model=dashboard_schema.DashboardStats)
async def get_dashboard_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated usage and health stats for the dashboard.
    """
    # 1. Total memory count
    count_query = select(func.count(Memory.id)).where(
        Memory.user_id == current_user.id,
        Memory.status == "active"
    )
    total_memories = await db.scalar(count_query) or 0
    
    # 2. Current monthly usage
    usage = await get_current_usage(db, str(current_user.id))
    monthly_ops = usage.memory_reads + usage.memory_writes
    
    # 3. Plan limits
    limits = PLAN_LIMITS.get(current_user.plan, PLAN_LIMITS["free"])
    ops_limit = limits["monthly_ops"] if limits["monthly_ops"] != float("inf") else None
    
    # 4. Last sleep run
    last_sleep_query = select(AuditLog).where(
        AuditLog.user_id == current_user.id,
        AuditLog.action == "sleep.phase.run"
    ).order_by(AuditLog.created_at.desc()).limit(1)
    
    last_sleep = await db.execute(last_sleep_query)
    last_sleep_log = last_sleep.scalar_one_or_none()
    
    # 5. Memory Health (Avg consolidation score)
    health_query = select(func.avg(Memory.consolidation_score)).where(
        Memory.user_id == current_user.id,
        Memory.status == "active"
    )
    avg_score = await db.scalar(health_query) or 0.0

    # 6. Misses from AuditLog
    miss_query = select(func.count(AuditLog.id)).where(
        AuditLog.user_id == current_user.id,
        AuditLog.action == "memory.missed"
    )
    miss_count = await db.scalar(miss_query) or 0

    # 7. Token Savings and Hits from Projects
    from ...models.project import Project
    project_stats_query = select(
        func.sum(Project.token_savings),
        # We approximate hits as the sum of access_count on memories
        select(func.sum(Memory.access_count)).where(Memory.user_id == current_user.id).scalar_subquery()
    ).where(Project.user_id == current_user.id)
    
    res = await db.execute(project_stats_query)
    savings, hits = res.first() or (0, 0)
    
    return {
        "total_memories": total_memories,
        "monthly_ops": monthly_ops,
        "monthly_ops_limit": ops_limit,
        "memory_health_score": round(avg_score * 100, 2),
        "miss_count": int(miss_count),
        "recall_hit_count": int(hits or 0),
        "token_savings_estimate": int(savings or 0),
        "last_sleep_run": last_sleep_log.created_at if last_sleep_log else None,
        "last_sleep_status": "success" if last_sleep_log else "pending"
    }
