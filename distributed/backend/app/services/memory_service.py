import logging
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select, update, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from ..models.memory import Memory
from ..models.user import User
from ..models.project import Project
from ..models.audit_log import AuditLog
from ..core.embeddings import get_embedding
from ..core.attention import normalize_recency, generate_explanation, score_memory
from ..core.content_encryption import encrypt_content, decrypt_content
from .usage_service import check_and_inc_usage
from ..config import settings

logger = logging.getLogger(__name__)

# Fixed in Fix 14 — uses app.core.content_encryption


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
        
        # Encrypt content — Fix 14: use per-tenant AES-256-GCM
        encrypted_content = encrypt_content(content, str(user.id))
        
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
        
        # Decrypt memory contents — Fix 14: per-tenant decryption
        for mem in memories:
            mem.content = decrypt_content(mem.content, str(user_id))
        
        return list(memories), total

    @staticmethod
    async def search_memories(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        min_attention_score: float = 0.3,
        dry_run: bool = False,
        redis: Optional[Redis] = None
    ) -> List[dict]:
        query_embedding = await get_embedding(query)
        
        # 1. Get attention weights (with Redis cache)
        weights = None
        cache_key = f"nsn:project:{project_id}:settings"
        
        if redis:
            cached = await redis.get(cache_key)
            if cached:
                try:
                    weights = json.loads(cached).get("attention_weights")
                except:
                    pass

        if not weights:
            proj = await session.scalar(select(Project).where(Project.id == project_id))
            if proj and proj.settings:
                weights = proj.settings.get("attention_weights")
                if redis:
                    # Cache for 5 minutes
                    await redis.setex(cache_key, 300, json.dumps(proj.settings))
            
        if not weights:
            weights = {"w_sim": 0.45, "w_rec": 0.15, "w_con": 0.25, "w_fb": 0.15}

        # 2. Fetch candidates using vector search
        stmt = select(
            Memory,
            (1 - Memory.embedding.cosine_distance(query_embedding)).label("similarity")
        ).where(
            Memory.user_id == user_id,
            Memory.project_id == project_id,
            Memory.status == "active"
        )
            
        stmt = stmt.order_by(desc("similarity")).limit(top_k * 2) 
        
        result = await session.execute(stmt)
        candidates = result.all()
        
        scored_results = []
        for mem, similarity in candidates:
            recency_weight = normalize_recency(mem.last_accessed_at)
            
            attention_score = score_memory(
                similarity=float(similarity),
                recency=float(recency_weight),
                consolidation=float(mem.consolidation_score),
                feedback=float(mem.feedback_score),
                importance=float(getattr(mem, 'importance', 1.0)),
                weights=weights
            )
            
            if attention_score >= min_attention_score:
                now_utc = datetime.now(timezone.utc)
                if not dry_run:
                    mem.access_count += 1
                    mem.last_accessed_at = now_utc
                
                # Decrypt content in-memory — Fix 14: per-tenant decryption
                decrypted_content = decrypt_content(mem.content, str(user_id))
                
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
                    "why_retrieved": generate_explanation(
                        similarity=float(similarity),
                        recency=float(recency_weight),
                        consolidation=float(mem.consolidation_score),
                        feedback=float(mem.feedback_score)
                    )
                }
                scored_results.append(res)
            else:
                # Fix 15: Log the miss so it appears in the Dashboard's Miss Inspector
                if not dry_run:
                    try:
                        # Decrypt content for the log so the user can actually inspect it
                        decrypted_for_log = decrypt_content(mem.content, str(user_id))
                        audit = AuditLog(
                            user_id=user_id,
                            action="memory.missed",
                            metadata_={
                                "query": query[:200],
                                "memory_id": str(mem.id),
                                "memory_content": decrypted_for_log[:200],
                                "score": float(attention_score),
                                "threshold": float(min_attention_score),
                                "project_id": str(project_id),
                                "reason": "below_threshold"
                            }
                        )
                        session.add(audit)
                    except Exception as e:
                        logger.warning(f"Failed to log memory miss: {e}")

        if not dry_run:
            # Fix 4: Update token_savings estimate on the project
            # Savings = tokens in all candidates - tokens in returned top-k subset
            all_candidate_bytes = sum(len(getattr(m, 'content', '')) for m, _ in candidates)
            hit_bytes = sum(len(r["memory"]["content"]) for r in scored_results) # using decrypted length here
            savings_delta = max(0, (all_candidate_bytes - hit_bytes) // 4) # rough token approximation
            
            if savings_delta > 0:
                await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(token_savings=Project.token_savings + savings_delta)
                )
            
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
