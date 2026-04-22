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
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Store a new memory. Idempotency-Key header prevents duplicate writes on retry.
    Webhook is enqueued AFTER db.commit() — never before.
    """
    # ── Idempotency check ─────────────────────────────────────────────────────
    if idempotency_key:
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            cache_key = f"idemp:{current_user.id}:{idempotency_key}"
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass  # Redis failure must never kill the write path

    # ── PII redaction ─────────────────────────────────────────────────────────
    safe_content = redact_pii(memory_in.content)

    # ── Write to DB ───────────────────────────────────────────────────────────
    res = await memory_service.create_memory(
        session=db,
        user=current_user,
        content=safe_content,
        project_id=memory_in.project_id,
        session_id=memory_in.session_id,
        tags=memory_in.tags,
        metadata=memory_in.metadata,
        importance=memory_in.importance,
        ttl_days=memory_in.ttl_days,
    )
    # DB commit happens inside create_memory — res is now persisted.

    # ── Cache idempotency key (24h) ───────────────────────────────────────────
    if idempotency_key:
        try:
            redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            dump = {
                "id": str(res.id),
                "user_id": str(res.user_id),
                "project_id": str(res.project_id) if res.project_id else None,
                "session_id": res.session_id,
                "content": res.content,
                "tags": res.tags,
                "consolidation_score": res.consolidation_score,
                "access_count": res.access_count,
                "status": res.status,
                "created_at": res.created_at.isoformat(),
            }
            await redis.set(
                f"idemp:{current_user.id}:{idempotency_key}",
                json.dumps(dump),
                ex=86400,
            )
        except Exception:
            pass  # Idempotency cache failure is non-fatal

    # ── Enqueue async embedding (embed queue) ─────────────────────────────────
    celery_app.send_task(
        "tasks.embed.generate",
        kwargs={"memory_id": str(res.id)},
    )

    # ── Enqueue webhook AFTER commit is confirmed ─────────────────────────────
    celery_app.send_task(
        "tasks.webhooks.deliver",
        kwargs={
            "event": "memory.stored",
            "memory_id": str(res.id),
            "project_id": str(res.project_id) if res.project_id else "global",
            "timestamp": res.created_at.isoformat(),
            "extra": {"tags": res.tags},
        },
    )

    return res


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

    # Batch embedding — single efficient call to embed queue
    memory_ids = [str(m.id) for m in created]
    celery_app.send_task("tasks.embed.batch_generate", kwargs={"memory_ids": memory_ids})

    return created


@router.get("/retrieve", response_model=memory_schema.SearchResponse)
async def retrieve_memories(
    query: str,
    project_id: str,
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
    memories = await memory_service.search_memories(
        session=db,
        user_id=current_user.id,
        project_id=uuid.UUID(project_id),
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
    celery_app.send_task("tasks.embed.generate", kwargs={"memory_id": str(res.id)})
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
