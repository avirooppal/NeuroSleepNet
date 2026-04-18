import uuid
from typing import Annotated, List, Optional
import json

from fastapi import APIRouter, Depends, Query, Header, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from ...config import settings
from ...workers.celery_app import celery_app

from ...deps import get_db
from ...models.user import User
from ...schemas import memory as memory_schema
from ...services.memory_service import memory_service
from ...core.pii import redact_pii
from .auth import get_current_user

router = APIRouter()


@router.post("/", response_model=memory_schema.Memory, status_code=status.HTTP_201_CREATED)
async def create_memory(
    memory_in: memory_schema.MemoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None)
):
    """
    Store a new memory. Sends payload to sidecar or triggers background task.
    """
    if idempotency_key:
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            cache_key = f"idemp:{current_user.id}:{idempotency_key}"
            cached = await redis.get(cache_key)
            if cached:
                cached_data = json.loads(cached)
                # Ensure it's returned as a consistent schema dict
                return cached_data
        except Exception:
            pass # Redis failure shouldn't kill the request
            
    safe_content = redact_pii(memory_in.content)
    # the original implementation used memory_service.create_memory. We will keep that structure
    # but adapt to project_id.
    return await memory_service.create_memory(
        session=db,
        user=current_user,
        content=safe_content,
        project_id=memory_in.project_id,
        session_id=memory_in.session_id,
        tags=memory_in.tags,
        metadata=memory_in.metadata,
        importance=memory_in.importance,
        ttl_days=memory_in.ttl_days
    )
    
    if idempotency_key:
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Serialize for cache
            dump = {
                "id": str(res.id),
                "user_id": str(res.user_id),
                "project_id": str(res.project_id) if res.project_id else None,
                "session_id": res.session_id,
                "content": res.content,
                "tags": res.tags,
                "metadata": res.metadata_,
                "consolidation_score": res.consolidation_score,
                "access_count": res.access_count,
                "status": res.status,
                "created_at": res.created_at.isoformat(),
                "last_accessed_at": res.last_accessed_at.isoformat(),
                "last_consolidated_at": res.last_consolidated_at.isoformat() if res.last_consolidated_at else None,
                "expires_at": res.expires_at.isoformat() if hasattr(res, 'expires_at') and res.expires_at else None
            }
            await redis.set(f"idemp:{current_user.id}:{idempotency_key}", json.dumps(dump), ex=86400)
        except Exception:
            pass
            
    # Enqueue webhook explicitly AFTER commit has resolved
    celery_app.send_task(
        "tasks.webhooks.deliver",
        kwargs={
            "event": "memory.stored",
            "memory_id": str(res.id),
            "project_id": str(res.project_id) if res.project_id else "global",
            "content": {"tags": res.tags}
        }
    )
            
    return res

@router.post("/batch", response_model=List[memory_schema.Memory], status_code=status.HTTP_201_CREATED)
async def create_memory_batch(
    memories_in: List[memory_schema.MemoryCreate],
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Store up to 100 memories densely"""
    if len(memories_in) > 100:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 100")
        
    created = []
    # For a real system we would use insert().values() but for now loop
    for mem in memories_in:
        safe_content = redact_pii(mem.content)
        res = await memory_service.create_memory(
            session=db,
            user=current_user,
            content=safe_content,
            project_id=mem.project_id,
            session_id=mem.session_id,
            tags=mem.tags,
            metadata=mem.metadata,
            importance=mem.importance,
            ttl_days=mem.ttl_days
        )
        created.append(res)
    return created


@router.get("/retrieve", response_model=memory_schema.SearchResponse)
async def retrieve_memories(
    query: str,
    project_id: str,
    top_k: int = Query(5, ge=1, le=100),
    dry_run: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Semantic search and attention reranking.
    """
    memories = await memory_service.search_memories(
        session=db,
        user_id=current_user.id,
        project_id=uuid.UUID(project_id),
        query=query,
        top_k=top_k,
        dry_run=dry_run
    )
    return {"memories": memories}


@router.post("/forget-query")
async def forget_by_query(
    query: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Forget semantically matching query
    """
    deleted_count = await memory_service.forget_by_query(
        session=db,
        user_id=current_user.id,
        query=query
    )
    return {"status": "success", "deleted": deleted_count}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await memory_service.delete_memory(db, current_user.id, memory_id)


@router.get("/explain_last")
async def explain_last(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"status": "not_implemented_fully", "explanation": "Why retrieved logic placeholder"}
