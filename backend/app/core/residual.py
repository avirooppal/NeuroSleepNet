import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task
from ..models.memory import Memory

logger = logging.getLogger(__name__)


async def generate_residual_context(
    session: AsyncSession,
    task_id: str,
    top_k: int = 5
) -> dict:
    """
    Generate a 'residual context' blob for a task.
    Summarizes the most important memories in that task.
    """
    # Fetch top memories by consolidation score + frequency
    query = select(Memory).where(
        Memory.task_id == task_id,
        Memory.status == "active"
    ).order_by(
        Memory.consolidation_score.desc(),
        Memory.access_count.desc()
    ).limit(top_k)
    
    result = await session.execute(query)
    memories = result.scalars().all()
    
    if not memories:
        return {}
        
    # Compress context: concatenated content + average embedding (optional)
    # For now, just top keywords or snippets
    snippets = [m.content[:100] for m in memories]
    
    return {
        "summary": " | ".join(snippets),
        "memory_ids": [str(m.id) for m in memories],
        "avg_score": sum(m.consolidation_score for m in memories) / len(memories)
    }


async def apply_residual_prior(
    session: AsyncSession,
    user_id: str,
    current_task_id: Optional[str] = None
) -> Optional[dict]:
    """
    Fetch residual context from the most related past task.
    Used during search to 'inform' retrieval across tasks.
    """
    # Simply get the most recent consolidated task for now
    # In a full implementation, we'd use semantic similarity between tasks
    query = select(Task).where(
        Task.user_id == user_id,
        Task.residual_context != None
    ).order_by(Task.created_at.desc()).limit(1)
    
    if current_task_id:
        query = query.where(Task.id != current_task_id)
        
    result = await session.execute(query)
    related_task = result.scalar_one_or_none()
    
    if related_task:
        return related_task.residual_context
    return None
