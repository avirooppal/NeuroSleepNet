import uuid
import logging
from typing import Annotated, Any, Dict, List, Optional, Union
import json

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Query, Header, status, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from ...config import settings
from ...workers.celery_app import celery_app
from ...deps import get_db
from ...models.user import User
from ...schemas import memory as memory_schema
from ...services.memory_service import memory_service
from ...core.pii import redact_pii
from .auth import get_current_user
from ...models.project import Project

router = APIRouter()

async def _resolve_project_id(project_id_raw: Union[uuid.UUID, str], user_id: uuid.UUID, db: AsyncSession) -> uuid.UUID:
    """Helper to convert a project name or UUID string into a UUID."""
    if isinstance(project_id_raw, uuid.UUID):
        return project_id_raw
    
    # Try to parse as UUID first
    try:
        return uuid.UUID(project_id_raw)
    except (ValueError, TypeError):
        pass
    
    # Otherwise treat as project name and find/create
    stmt = select(Project).where(Project.user_id == user_id, Project.name == project_id_raw)
    result = await db.execute(stmt)
    project = result.scalars().first()
    
    if not project:
        # Auto-create project for the user if it doesn't exist
        project = Project(user_id=user_id, name=project_id_raw)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
    return project.id


@router.post("/batch", response_model=List[memory_schema.Memory], status_code=status.HTTP_201_CREATED)
async def create_memory_batch(
    memories_in: List[memory_schema.MemoryCreate],
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Store up to 100 memories in a single request.
    Idempotency-Key required for safe retries.
    Embeddings generated in a single batch call to the embed sidecar.
    """
    if len(memories_in) > 100:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 100 memories.")

    created = []
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
            ttl_days=mem.ttl_days,
        )
        created.append(res)

    return created


@router.get("/retrieve")
async def retrieve_memories(
    query: str,
    project_id: Union[uuid.UUID, str],
    top_k: int = Query(5, ge=1, le=100),
    dry_run: bool = Query(False, description="If true, does not update access_count or consolidation scoring."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic search with attention reranking.
    dry_run=true retrieves without affecting consolidation scores — used by
    the dashboard "What would my agent remember?" search bar.
    """
    # ── Resolve Project ID ──────────────────────────────────────────────────
    actual_project_id = await _resolve_project_id(project_id, current_user.id, db)

    memories = await memory_service.search_memories(
        session=db,
        user_id=current_user.id,
        project_id=actual_project_id,
        query=query,
        top_k=top_k,
        dry_run=dry_run,
    )
    return {"memories": memories}


@router.post("/remember", status_code=status.HTTP_201_CREATED)
async def remember_important(
    content: str,
    importance: float = 0.9,
    tags: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    High-importance manual memory injection (maps to nsn.remember() in SDK).
    Importance is pre-boosted and these memories are resistant to sleep archival.
    """
    safe_content = redact_pii(content)
    res = await memory_service.create_memory(
        session=db,
        user=current_user,
        content=safe_content,
        project_id=uuid.UUID(project_id) if project_id else None,
        tags=tags or ["manual-injection"],
        importance=importance,
    )
    return res


@router.post("/forget-query")
async def forget_by_query(
    query: str,
    older_than_days: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic forget — hard-delete all memories matching query.
    Optionally filter to memories older than N days (nsn.forget(query, older_than_days)).
    """
    deleted_count = await memory_service.forget_by_query(
        session=db,
        user_id=current_user.id,
        query=query,
        older_than_days=older_than_days,
    )
    return {"status": "success", "deleted": deleted_count}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hard-delete a single memory by ID."""
    return await memory_service.delete_memory(db, current_user.id, memory_id)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def store_memory(
    memory_in: memory_schema.MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """Generic memory storage (maps to nsn.remember() in SDK)."""
    try:
        # Resolve project_id if string provided
        p_id = None
        if memory_in.project_id:
            p_id = await _resolve_project_id(memory_in.project_id, current_user.id, db)

        res = await memory_service.create_memory(
            session=db,
            user=current_user,
            content=memory_in.content,
            project_id=p_id,
            tags=memory_in.tags,
            importance=memory_in.importance,
            session_id=memory_in.session_id,
            ttl_days=memory_in.ttl_days
        )
        return {
            "id": str(res.id),
            "user_id": str(res.user_id),
            "content": res.content,
            "tags": res.tags or [],
            "metadata": dict(res.metadata_ or {}),
            "importance": res.importance,
            "status": res.status,
            "created_at": res.created_at.isoformat() if res.created_at else None,
            "last_accessed_at": res.last_accessed_at.isoformat() if res.last_accessed_at else None,
            "consolidation_score": res.consolidation_score,
            "access_count": res.access_count,
            "session_id": res.session_id,
            "project_id": str(res.project_id) if res.project_id else None
        }
    except Exception as e:
        logger.exception(f"FAIL in store_memory: {e}")
        raise


@router.post("/feedback")
async def apply_feedback(
    feedback: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reinforce or downweight a memory based on feedback."""
    memory_id = uuid.UUID(feedback["memory_id"]) if isinstance(feedback["memory_id"], str) else feedback["memory_id"]
    helpful = feedback["helpful"]
    ok = await memory_service.apply_feedback(db, current_user.id, memory_id, helpful)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "success"}


@router.post("/{memory_id}/pin")
async def pin_memory(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a memory as pinned (immutable, always recalled)."""
    ok = await memory_service.pin_memory(db, current_user.id, memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "success"}


@router.post("/{memory_id}/unpin")
async def unpin_memory(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the pinned status from a memory."""
    ok = await memory_service.unpin_memory(db, current_user.id, memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "success"}


@router.get("/explain_last")
async def explain_last(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Explain why specific memories were retrieved in the last agent call.
    Returns the retrieval context: query used, memories returned, attention scores.
    """
    from sqlalchemy import select, desc
    from ...models.audit_log import AuditLog
    query = select(AuditLog).where(
        AuditLog.user_id == current_user.id,
        AuditLog.action == "memory.retrieved",
    ).order_by(desc(AuditLog.created_at)).limit(1)
    result = await db.execute(query)
    last = result.scalar_one_or_none()

    if not last:
        return {"explanation": "No retrieval events found for this project.", "memories": []}

    meta = last.metadata or {}
    return {
        "query": meta.get("query", ""),
        "retrieved_at": last.created_at.isoformat(),
        "memories": meta.get("memories", []),
        "attention_scores": meta.get("attention_scores", []),
        "dry_run": meta.get("dry_run", False),
    }
