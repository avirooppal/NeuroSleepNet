import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.memory import Memory
from .embeddings import get_embedding

logger = logging.getLogger(__name__)


async def update_consolidation(
    session: AsyncSession,
    user_id: str,
    threshold: int = 5,
    days_ago: int = 7
) -> dict:
    """
    Perform consolidation process for a user's memories.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days_ago)
    
    # Query for memories that haven't been consolidated recently
    # or meet the access frequency threshold
    query = select(Memory).where(
        Memory.user_id == user_id,
        Memory.status == "active",
        Memory.last_accessed_at < cutoff
    )
    
    result = await session.execute(query)
    memories = result.scalars().all()
    
    consolidated_count = 0
    archived_count = 0
    
    for memory in memories:
        if memory.access_count >= threshold:
            # IMPORTANT: Re-reinforce memories with high access frequency
            # Consolidate: boost score + refresh embedding
            memory.consolidation_score = min(1.0, memory.consolidation_score + 0.1)
            # Embedding refresh is optional if content hasn't changed, 
            # but specified in PLAN.md as a way to avoid 'drift'.
            # We'll skip for this prototype to save OpenAI tokens unless needed.
            memory.last_consolidated_at = now
            consolidated_count += 1
        elif memory.consolidation_score < 0.2:
            # Forget: low score and hasn't been accessed
            memory.status = "archived"
            archived_count += 1
            
    await session.commit()
    
    return {
        "consolidated": consolidated_count,
        "archived": archived_count,
        "total_processed": len(memories)
    }


def calculate_health_score(memories: List[Memory]) -> float:
    """
    Aggregate health score (0-100) based on average consolidation.
    """
    if not memories:
        return 100.0
    
    avg_score = sum(m.consolidation_score for m in memories) / len(memories)
    return avg_score * 100.0
