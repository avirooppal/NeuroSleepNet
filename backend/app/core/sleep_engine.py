import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.memory import Memory
from ..models.audit_log import AuditLog
from .consolidation import update_consolidation

logger = logging.getLogger(__name__)


async def run_sleep_phase(
    session: AsyncSession,
    user_id: str,
    max_prune_percent: float = 0.2,
    min_task_memories: int = 50,
    min_age_hours: int = 72
) -> dict:
    """
    Coordinator for the nightly 'Sleep Phase'. 
    Includes safety checks from PLAN.md Section 11.4.
    """
    now = datetime.now(timezone.utc)
    age_cutoff = now - timedelta(hours=min_age_hours)
    
    # 1. Update consolidation scores
    # This boosts scores for frequently accessed memories
    consolidation_stats = await update_consolidation(session, user_id)
    
    # 2. Pruning & Archiving with Safety Guards
    # Guard 1: Count total active memories for stats and capping
    count_query = select(func.count(Memory.id)).where(
        Memory.user_id == user_id,
        Memory.status == "active"
    )
    total_active = await session.scalar(count_query) or 0
    
    # Guard 2: Max prune limit (20% of user's total)
    max_to_prune = int(total_active * max_prune_percent)
    
    # Guard 3: Fetch candidate memories for archiving
    # Rules: consolidation < 0.15 AND access_count == 0 AND age > 72hr
    prune_query = select(Memory).where(
        Memory.user_id == user_id,
        Memory.status == "active",
        Memory.consolidation_score < 0.15,
        Memory.access_count == 0,
        Memory.created_at < age_cutoff
    ).limit(max_to_prune)
    
    result = await session.execute(prune_query)
    to_archive = result.scalars().all()
    
    archived_count = 0
    for memory in to_archive:
        # Guard 4: Never prune memories that would dip task count below 50
        # Check task memory count
        if memory.task_id:
            count_task_query = select(func.count(Memory.id)).where(
                Memory.task_id == memory.task_id,
                Memory.status == "active"
            )
            task_total = await session.scalar(count_task_query) or 0
            if task_total <= min_task_memories:
                continue
                
        # Mark as archived (soft-delete)
        memory.status = "archived"
        archived_count += 1
        
    await session.commit()
    
    # 3. Log the sleep run (Audit Log)
    audit = AuditLog(
        user_id=user_id,
        action="sleep.phase.run",
        metadata={
            "consolidated": consolidation_stats["consolidated"],
            "archived": archived_count,
            "total_processed": consolidation_stats["total_processed"],
            "active_memories_before": total_active
        }
    )
    session.add(audit)
    await session.commit()
    
    return {
        "status": "success",
        "consolidated": consolidation_stats["consolidated"],
        "archived": archived_count,
        "ts": now.isoformat()
    }
