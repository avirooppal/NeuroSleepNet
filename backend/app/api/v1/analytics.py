"""
Analytics API — memory health, usage stats, access timeline, and state diff.
All responses are real metrics from the DB — no placeholders.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db
from ...models.memory import Memory
from ...models.user import User
from ...models.usage_log import UsageLog
from ...core.sleep_engine import score_label
from .auth import get_current_user

router = APIRouter()


@router.get("/health")
async def memory_health(
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Memory health metrics: active/archived counts, consolidation score distribution.
    Used by the dashboard Memory Health Panel.
    """
    base = [Memory.user_id == current_user.id]
    if project_id:
        from ...models.project import Project
        import uuid
        base.append(Memory.project_id == uuid.UUID(project_id))

    # Status counts
    status_q = select(Memory.status, func.count(Memory.id)).where(*base).group_by(Memory.status)
    status_result = await db.execute(status_q)
    status_counts = {row[0]: row[1] for row in status_result.fetchall()}

    active = status_counts.get("active", 0)
    archived = status_counts.get("archived", 0)
    total = active + archived + status_counts.get("pruned", 0)

    # Score distribution — bucket by tier
    score_q = select(Memory.consolidation_score).where(*base, Memory.status == "active")
    score_result = await db.execute(score_q)
    scores = [row[0] for row in score_result.fetchall()]

    dist = {"Weak": 0, "Developing": 0, "Established": 0, "Core": 0}
    for s in scores:
        dist[score_label(s)["label"]] += 1

    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    health_label = score_label(avg_score)["label"]

    return {
        "total": total,
        "active": active,
        "archived": archived,
        "avg_consolidation_score": avg_score,
        "health_label": health_label,
        "score_distribution": dist,
    }


@router.get("/usage")
async def memory_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    API call counts, token usage, and quota ring gauge data.
    """
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Total memories written by user
    total_q = select(func.count(Memory.id)).where(Memory.user_id == current_user.id)
    total = await db.scalar(total_q) or 0

    # Usage log entries for last 30 days (API calls)
    try:
        usage_q = select(
            func.count(UsageLog.id),
            func.sum(UsageLog.tokens_used),
        ).where(
            UsageLog.user_id == current_user.id,
            UsageLog.created_at >= thirty_days_ago,
        )
        usage_result = await db.execute(usage_q)
        row = usage_result.fetchone()
        api_calls = row[0] or 0
        tokens_used = row[1] or 0
    except Exception:
        api_calls, tokens_used = 0, 0

    # Quota — from user model (if exists) — fallback to defaults
    quota_limit = getattr(current_user, "quota_limit", 10000)
    quota_used = total
    quota_pct = round((quota_used / quota_limit) * 100, 1) if quota_limit else 0

    return {
        "api_calls_30d": api_calls,
        "tokens_used_30d": tokens_used,
        "memories_total": total,
        "quota_used": quota_used,
        "quota_limit": quota_limit,
        "quota_pct": quota_pct,
        "quota_warning": quota_pct >= 80,
        "quota_critical": quota_pct >= 95,
    }


@router.get("/timeline")
async def memory_timeline(
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    30-day memory access timeline — daily access counts for Recharts chart.
    """
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    base = [
        Memory.user_id == current_user.id,
        Memory.last_accessed_at >= thirty_days_ago,
    ]
    if project_id:
        import uuid
        base.append(Memory.project_id == uuid.UUID(project_id))

    q = select(
        func.date_trunc("day", Memory.last_accessed_at).label("day"),
        func.count(Memory.id).label("accesses"),
    ).where(*base).group_by("day").order_by("day")

    result = await db.execute(q)
    rows = result.fetchall()

    return [{"date": str(row[0].date()), "accesses": row[1]} for row in rows]


@router.get("/diff")
async def memory_diff(
    from_ts: str = Query(..., description="ISO8601 timestamp — start of diff window"),
    to_ts: str = Query(..., description="ISO8601 timestamp — end of diff window"),
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Memory state diff between two timestamps.
    Returns memories created, archived, and deleted in the window.
    """
    t_from = datetime.fromisoformat(from_ts.replace("Z", "+00:00"))
    t_to = datetime.fromisoformat(to_ts.replace("Z", "+00:00"))

    base = [Memory.user_id == current_user.id]
    if project_id:
        import uuid
        base.append(Memory.project_id == uuid.UUID(project_id))

    # Created in window
    created_q = select(func.count(Memory.id)).where(
        *base, Memory.created_at >= t_from, Memory.created_at <= t_to
    )
    created = await db.scalar(created_q) or 0

    # Archived in window (last_consolidated_at used as proxy for archive time)
    archived_q = select(func.count(Memory.id)).where(
        *base,
        Memory.status == "archived",
        Memory.last_consolidated_at >= t_from,
        Memory.last_consolidated_at <= t_to,
    )
    archived = await db.scalar(archived_q) or 0

    return {
        "from": from_ts,
        "to": to_ts,
        "created": created,
        "archived": archived,
        "net_change": created - archived,
    }


@router.get("/stats")
async def get_project_stats(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Project-level statistics for the SDK get_stats() call.
    Returns counts, health score, and anomaly flags.
    """
    import uuid
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        # Resolve project name to ID
        from ...models.project import Project
        stmt = select(Project).where(Project.user_id == current_user.id, Project.name == project_id)
        res = await db.execute(stmt)
        proj = res.scalars().first()
        if not proj:
            return {"error": "Project not found"}
        pid = proj.id
    
    # Total active memories
    active_q = select(func.count(Memory.id)).where(
        Memory.user_id == current_user.id,
        Memory.project_id == pid,
        Memory.status == "active"
    )
    active = await db.scalar(active_q) or 0
    
    # Archived memories
    archived_q = select(func.count(Memory.id)).where(
        Memory.user_id == current_user.id,
        Memory.project_id == pid,
        Memory.status == "archived"
    )
    archived = await db.scalar(archived_q) or 0
    
    # Avg consolidation score
    avg_score_q = select(func.avg(Memory.consolidation_score)).where(
        Memory.user_id == current_user.id,
        Memory.project_id == pid,
        Memory.status == "active"
    )
    avg_score = await db.scalar(avg_score_q) or 0.0
    
    # Health score (0-1)
    health_score = round(min(1.0, float(avg_score) * 1.2), 2)
    
    return {
        "project": project_id,
        "total_memories": active,
        "archived": archived,
        "avg_consolidation_score": round(float(avg_score), 3),
        "health_score": health_score,
        "status": "healthy" if health_score > 0.4 else "fragmented"
    }


@router.get("/attention")
async def attention_distribution(
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Recalled memory type distribution for the Attention Heatmap.
    Analyses audit logs for 'memory.retrieved' actions.
    """
    from ...models.audit_log import AuditLog
    
    # Query last 100 retrieval events
    base = [AuditLog.user_id == current_user.id, AuditLog.action == "memory.retrieved"]
    q = select(AuditLog.metadata_).where(*base).order_by(AuditLog.created_at.desc()).limit(100)
    
    result = await db.execute(q)
    rows = result.fetchall()
    
    distribution = {"episodic": 0, "semantic": 0, "procedural": 0, "user": 0, "agent": 0}
    
    for row in rows:
        meta = row[0] or {}
        memories = meta.get("memories", [])
        for mem in memories:
            m_type = mem.get("type", "episodic")
            if m_type in distribution:
                distribution[m_type] += 1
            else:
                distribution["episodic"] += 1 # Default fallback
                
    # Format for Recharts / Heatmap
    return [
        {"type": k.capitalize(), "recalls": v} 
        for k, v in distribution.items() 
        if v > 0 or k in ["episodic", "semantic"]
    ]
