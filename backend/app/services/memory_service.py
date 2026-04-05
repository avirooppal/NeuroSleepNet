import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


from ..models.memory import Memory
from ..models.user import User
from ..models.task import Task
from ..core.embeddings import get_embedding
from ..core.attention import compute_recency_weight, generate_explanation, score_memory
from ..core.residual import apply_residual_prior
from .usage_service import check_and_inc_usage

logger = logging.getLogger(__name__)


class MemoryService:
    @staticmethod
    async def create_memory(
        session: AsyncSession,
        user: User,
        content: str,
        task_id: Optional[uuid.UUID] = None,
        metadata: dict = {}
    ) -> Memory:
        """
        Create a new memory, generate embedding, and track usage.
        """
        # 1. Enforce plan limits
        # Approximate size of content + metadata
        bytes_size = len(content.encode()) + len(str(metadata).encode())
        await check_and_inc_usage(session, user, op_type="write", bytes_inc=bytes_size)
        
        # 2. Get embedding
        embedding = await get_embedding(content)
        
        # 3. Save memory
        memory = Memory(
            user_id=user.id,
            task_id=task_id,
            content=content,
            embedding=embedding,
            metadata=metadata,
            consolidation_score=0.5,  # initial score
            status="active"
        )
        session.add(memory)
        await session.commit()
        await session.refresh(memory)
        return memory

    @staticmethod
    async def list_memories(
        session: AsyncSession,
        user_id: uuid.UUID,
        task_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[Memory], int]:
        """
        List memories with pagination and optional task filter.
        """
        query = select(Memory).where(
            Memory.user_id == user_id,
            Memory.status == "active"
        )
        if task_id:
            query = query.where(Memory.task_id == task_id)
            
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0
        
        # Paginate
        query = query.order_by(Memory.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        memories = result.scalars().all()
        
        return list(memories), total

    @staticmethod
    async def search_memories(
        session: AsyncSession,
        user: User,
        query: str,
        task_id: Optional[uuid.UUID] = None,
        top_k: int = 5,
        min_attention_score: float = 0.3
    ) -> Tuple[List[dict], bool]:
        """
        Perform semantic search with attention scoring.
        """
        # 1. Record usage
        await check_and_inc_usage(session, user, op_type="read")
        
        # 2. Get query embedding
        query_embedding = await get_embedding(query)
        
        # 3. Check for residual context (cross-task prior)
        residual_prior = await apply_residual_prior(session, user.id, task_id)
        # In a full impl, we'd inject this prior into the query or reranker.
        # For now, just mark it as applied.
        
        # 4. Semantic Search (pgvector cosine similarity)
        # pgvector uses `<=>` for cosine distance, `1 - distance` = similarity
        # sqlalchemy-pgvector supports `<=>`
        stmt = select(
            Memory,
            (1 - Memory.embedding.cosine_distance(query_embedding)).label("similarity")
        ).where(
            Memory.user_id == user.id,
            Memory.status == "active"
        )
        
        if task_id:
            stmt = stmt.where(Memory.task_id == task_id)
            
        stmt = stmt.order_by("similarity").limit(top_k * 2) # Get more candidates for attention reranking
        
        result = await session.execute(stmt)
        candidates = result.all()
        
        # 5. Attention Reranking
        scored_results = []
        for mem, similarity in candidates:
            recency_weight = compute_recency_weight(mem.last_accessed_at)
            
            # Weighted aggregation
            attention_score = score_memory(
                similarity,
                recency_weight,
                mem.consolidation_score
            )
            
            if attention_score >= min_attention_score:
                # Update access stats (don't block for this async)
                mem.access_count += 1
                mem.last_accessed_at = datetime.now(timezone.utc)
                # Keep session updated but commit at the end if needed
                
                res = {
                    "memory": mem,
                    "attention_score": attention_score,
                    "why_retrieved": generate_explanation(
                        similarity,
                        recency_weight,
                        mem.consolidation_score
                    )
                }
                scored_results.append(res)
                
        await session.commit()
        
        # Return top K sorted by attention score
        scored_results.sort(key=lambda x: x["attention_score"], reverse=True)
        return scored_results[:top_k], residual_prior is not None


memory_service = MemoryService()
