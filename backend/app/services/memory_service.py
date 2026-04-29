import logging
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from cryptography.fernet import Fernet

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from ..models.memory import Memory
from ..models.user import User
from ..models.project import Project
from ..core.embeddings import get_embedding
from ..core.attention import compute_recency_weight, generate_explanation, score_memory
from .usage_service import check_and_inc_usage
from ..config import settings

logger = logging.getLogger(__name__)

# Fallback symmetric key for AES-256
_KEY = settings.NSN_ENCRYPTION_KEY.encode()[:32]
import base64
_FERNET_KEY = base64.urlsafe_b64encode(_KEY.ljust(32, b'0'))
_fernet = Fernet(_FERNET_KEY)

class MemoryService:
    @staticmethod
    async def create_memory(
        session: AsyncSession,
        user: User,
        content: str,
        project_id: Optional[uuid.UUID] = None,
        session_id: Optional[str] = None,
        tags: list = [],
        metadata: dict = {},
        importance: float = 1.0,
        ttl_days: Optional[int] = None
    ) -> Memory:
        # Enforce plan limits
        bytes_size = len(content.encode()) + len(str(metadata).encode())
        await check_and_inc_usage(session, user, op_type="write", bytes_inc=bytes_size)
        
        # Get embedding
        embedding = await get_embedding(content)
        
        # Encrypt content
        encrypted_content = _fernet.encrypt(content.encode()).decode()
        
        # Calculate TTL
        expires_at = None
        if ttl_days is not None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
            
        # Save memory
        memory = Memory(
            user_id=user.id,
            project_id=project_id,
            session_id=session_id,
            content=encrypted_content,
            tags=tags,
            embedding=embedding,
            metadata_=metadata,
            consolidation_score=0.5,  
            status="active",
            expires_at=expires_at
        )
        session.add(memory)
        await session.commit()
        await session.refresh(memory)

        # Trigger Consolidation Async via Redis Streams
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            await redis.xadd(
                "nsn_consolidation_stream",
                {"project_id": str(project_id) if project_id else "global"}
            )
        except Exception as e:
            logger.warning(f"Failed to post to redis streams: {e}")

        return memory

    @staticmethod
    async def list_memories(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 50
    ) -> Tuple[List[Memory], int]:
        query = select(Memory).where(
            Memory.user_id == user_id,
            Memory.status == "active"
        )
        if project_id:
            query = query.where(Memory.project_id == project_id)
            
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query) or 0
        
        query = query.order_by(Memory.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        memories = result.scalars().all()
        
        # Decrypt memory contents
        for mem in memories:
            try:
                mem.content = _fernet.decrypt(mem.content.encode()).decode()
            except Exception:
                pass # Already plaintext or corrupted
        
        return list(memories), total

    @staticmethod
    async def search_memories(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        min_attention_score: float = 0.3,
        dry_run: bool = False
    ) -> List[dict]:
        query_embedding = await get_embedding(query)
        
        # Get attention weights for this project
        proj = await session.scalar(select(Project).where(Project.id == project_id))
        weights = proj.attention_weights if proj and proj.attention_weights else {"w1": 0.5, "w2": 0.2, "w3": 0.2, "w4": 0.1}

        stmt = select(
            Memory,
            (1 - Memory.embedding.cosine_distance(query_embedding)).label("similarity")
        ).where(
            Memory.user_id == user_id,
            Memory.project_id == project_id,
            Memory.status == "active"
        )
            
        stmt = stmt.order_by("similarity").limit(top_k * 2) 
        
        result = await session.execute(stmt)
        candidates = result.all()
        
        scored_results = []
        for mem, similarity in candidates:
            # We skip detailed recency function setup here, dummy compute for simplicity
            recency_weight = compute_recency_weight(mem.last_accessed_at)
            
            # Simple manual score calculation to use custom weights
            # AttentionScore = w1 * Similarity + w2 * Recency + w3 * Consolidation
            # AttentionScore = w1*Sim + w2*Recency + w3*Consolidation + w4*Feedback + w5*Importance
            # Standard weights: 0.4, 0.1, 0.2, 0.2, 0.1
            attention_score = (
                (weights.get("w1", 0.4) * float(similarity)) +
                (weights.get("w2", 0.1) * float(recency_weight)) +
                (weights.get("w3", 0.2) * float(mem.consolidation_score)) +
                (weights.get("w4", 0.2) * float((mem.feedback_score + 1.0) / 2.0)) +
                (weights.get("w5", 0.1) * float(min(1.0, mem.importance / 2.0)))
            )
            
            if attention_score >= min_attention_score:
                now_utc = datetime.now(timezone.utc)
                if not dry_run:
                    mem.access_count += 1
                    mem.last_accessed_at = now_utc
                
                # Decrypt content in-memory for response, without committing decrypted state
                try:
                    decrypted_content = _fernet.decrypt(mem.content.encode()).decode()
                except Exception:
                    decrypted_content = mem.content
                
                # Check 48h mini-consolidation fallback
                if not dry_run:
                    last_col = mem.last_consolidated_at or mem.created_at
                    if (now_utc - last_col).total_seconds() > 172800: # 48 hours
                        # Mini-consolidation bump automatically because Celery has clearly failed
                        mem.consolidation_score = min(1.0, mem.consolidation_score + 0.1)
                        mem.last_consolidated_at = now_utc

                mem_dict = {
                    "id": mem.id,
                    "user_id": mem.user_id,
                    "content": decrypted_content,
                    "tags": mem.tags,
                    "metadata": mem.metadata_ if hasattr(mem, 'metadata_') else {},
                    "importance": getattr(mem, 'importance', 1.0),
                    "project_id": mem.project_id,
                    "session_id": mem.session_id,
                    "created_at": mem.created_at,
                    "last_accessed_at": mem.last_accessed_at,
                    "last_consolidated_at": mem.last_consolidated_at,
                    "consolidation_score": mem.consolidation_score,
                    "feedback_score": mem.feedback_score,
                    "access_count": mem.access_count,
                    "status": mem.status,
                    "expires_at": mem.expires_at,
                    "schema_version": getattr(mem, 'schema_version', 1)
                }
                
                res = {
                    "memory": mem_dict,
                    "attention_score": attention_score,
                    "why_retrieved": "Score passed threshold"
                }
                scored_results.append(res)
                
        if not dry_run:
            await session.commit()
        
        scored_results.sort(key=lambda x: x["attention_score"], reverse=True)
        return scored_results[:top_k]

    @staticmethod
    async def forget_by_query(
        session: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        older_than_days: Optional[int] = None
    ) -> int:
        """
        Semantic forget: find memories matching query and mark them as deleted.
        """
        # We use a lower threshold for forgetting to be thorough
        memories = await MemoryService.search_memories(
            session=session,
            user_id=user_id,
            project_id=uuid.UUID(int=0), # Global search if project not specified
            query=query,
            top_k=50,
            min_attention_score=0.25,
            dry_run=True
        )
        
        count = 0
        now = datetime.now(timezone.utc)
        for m_res in memories:
            m_id = m_res["memory"]["id"]
            
            # Re-fetch the model instance to update it
            stmt = select(Memory).where(Memory.id == m_id, Memory.user_id == user_id)
            res = await session.execute(stmt)
            mem = res.scalar_one_or_none()
            
            if mem:
                if older_than_days:
                    age = now - mem.created_at
                    if age.days < older_than_days:
                        continue
                
                mem.status = "deleted"
                count += 1
        
        await session.commit()
        return count

    @staticmethod
    async def apply_feedback(
        session: AsyncSession,
        user_id: uuid.UUID,
        memory_id: uuid.UUID,
        helpful: bool
    ) -> bool:
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await session.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            return False
        
        # Adjust feedback_score: +/- 0.1 per signal, clamped to [-1.0, 1.0]
        adjustment = 0.1 if helpful else -0.1
        mem.feedback_score = max(-1.0, min(1.0, mem.feedback_score + adjustment))
        
        # Also bump/decay consolidation score slightly
        mem.consolidation_score = max(0.0, min(1.0, mem.consolidation_score + (adjustment * 0.5)))
        
        await session.commit()
        return True

    @staticmethod
    async def pin_memory(
        session: AsyncSession,
        user_id: uuid.UUID,
        memory_id: uuid.UUID
    ) -> bool:
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await session.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            return False
        
        tags = list(mem.tags)
        if "pinned" not in tags:
            mem.tags = tags + ["pinned"]
            mem.consolidation_score = 1.0 # Pinned memories are permanent
        
        await session.commit()
        return True

    @staticmethod
    async def unpin_memory(
        session: AsyncSession,
        user_id: uuid.UUID,
        memory_id: uuid.UUID
    ) -> bool:
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await session.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            return False
        
        tags = list(mem.tags)
        if "pinned" in tags:
            tags.remove("pinned")
            mem.tags = tags
            mem.consolidation_score = 0.5 # Reset to default
        
        await session.commit()
        return True

    @staticmethod
    async def delete_memory(
        session: AsyncSession,
        user_id: uuid.UUID,
        memory_id: uuid.UUID
    ) -> bool:
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await session.execute(stmt)
        mem = res.scalar_one_or_none()
        if not mem:
            return False
        
        await session.delete(mem)
        await session.commit()
        return True


memory_service = MemoryService()
