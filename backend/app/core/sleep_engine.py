"""
Sleep Engine — nightly memory consolidation and pruning.

Run order is STRICT per the architecture spec:
  1. TTL expiry (hard delete) — always first, overrides everything
  2. Boost consolidation scores for frequently accessed memories
  3. Identify and archive low-score candidates
  4. Enforce min_memories floor — never archive below this count
  5. Write SleepRunLog audit record

A lightweight mini_consolidation() is available for the 48h fallback path
(no Celery dependency — runs synchronously on next API call).
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.memory import Memory
from ..models.sleep_run_log import SleepRunLog

logger = logging.getLogger(__name__)

# ── Consolidation score human labels ─────────────────────────────────────────

SCORE_LABELS = {
    (0.00, 0.25): ("Weak",        "red"),
    (0.25, 0.50): ("Developing",  "amber"),
    (0.50, 0.75): ("Established", "blue"),
    (0.75, 1.00): ("Core",        "green"),
}


def score_label(score: float) -> dict:
    for (lo, hi), (label, color) in SCORE_LABELS.items():
        if lo <= score < hi:
            return {"label": label, "color": color, "score": round(score, 4)}
    # Edge: score == 1.0
    return {"label": "Core", "color": "green", "score": round(score, 4)}


# ── TTL Expiry ────────────────────────────────────────────────────────────────

async def run_ttl_expiry(
    session: AsyncSession,
    user_id: str,
    project_id: Optional[str] = None,
) -> int:
    """
    Hard-delete all memories past their expires_at timestamp.
    This is ALWAYS step 1 of any sleep run — TTL overrides consolidation score.
    """
    now = datetime.now(timezone.utc)
    query = delete(Memory).where(
        Memory.user_id == user_id,
        Memory.expires_at.isnot(None),
        Memory.expires_at <= now,
    )
    if project_id:
        query = query.where(Memory.project_id == project_id)

    result = await session.execute(query)
    deleted = result.rowcount or 0
    if deleted:
        logger.info(f"[Sleep] TTL expiry: hard-deleted {deleted} memories for user {user_id}")
    return deleted


# ── Consolidation Boost ───────────────────────────────────────────────────────

async def boost_consolidation_scores(
    session: AsyncSession,
    user_id: str,
    project_id: Optional[str] = None,
) -> dict:
    """
    Boost scores for frequently accessed memories.
    Returns stats: how many were boosted and average delta.
    """
    query = select(Memory).where(
        Memory.user_id == user_id,
        Memory.status == "active",
        Memory.access_count > 0,
    )
    if project_id:
        query = query.where(Memory.project_id == project_id)

    result = await session.execute(query)
    memories = result.scalars().all()

    boosted, total_delta = 0, 0.0
    for mem in memories:
        old_score = mem.consolidation_score
        # Logarithmic boost: more accesses = more boost, but diminishing returns
        boost = min(0.1 * (1 + (mem.access_count ** 0.5) * 0.05), 0.2)
        mem.consolidation_score = min(1.0, old_score + boost)
        total_delta += mem.consolidation_score - old_score
        mem.last_consolidated_at = datetime.now(timezone.utc)
        boosted += 1

    return {
        "boosted": boosted,
        "avg_delta": round(total_delta / boosted, 4) if boosted else 0.0,
    }


# ── Archive Candidates ────────────────────────────────────────────────────────

async def archive_low_score_memories(
    session: AsyncSession,
    user_id: str,
    min_memories: int = 3,
    min_age_hours: int = 72,
    project_id: Optional[str] = None,
) -> dict:
    """
    Archive memories with low consolidation score that have never been retrieved.
    Respects the min_memories floor — never archives the last N memories.
    Returns the count archived and previews of top archived (for SleepRunLog).
    """
    now = datetime.now(timezone.utc)
    age_cutoff = now - timedelta(hours=min_age_hours)

    # Count total active memories (for floor guard)
    count_q = select(func.count(Memory.id)).where(
        Memory.user_id == user_id,
        Memory.status == "active",
    )
    if project_id:
        count_q = count_q.where(Memory.project_id == project_id)
    total_active = await session.scalar(count_q) or 0

    if total_active <= min_memories:
        logger.info(f"[Sleep] min_memories floor hit ({total_active} <= {min_memories}) — skipping archive.")
        return {"archived": 0, "guardrails_triggered": True, "top_archived": []}

    # Max we can archive without breaching the floor
    max_archive = total_active - min_memories

    # Archive candidates: low score + never retrieved + old enough
    cands_q = select(Memory).where(
        Memory.user_id == user_id,
        Memory.status == "active",
        Memory.consolidation_score < 0.25,
        Memory.access_count == 0,
        Memory.created_at < age_cutoff,
    ).order_by(Memory.consolidation_score.asc()).limit(max_archive)
    if project_id:
        cands_q = cands_q.where(Memory.project_id == project_id)

    result = await session.execute(cands_q)
    candidates = result.scalars().all()

    top_archived = []
    archived = 0
    guardrails_triggered = False

    for mem in candidates:
        if archived >= max_archive:
            guardrails_triggered = True
            break
        mem.status = "archived"
        archived += 1
        if len(top_archived) < 3:
            top_archived.append({
                "id": str(mem.id),
                "content_preview": mem.content[:120] + "…" if len(mem.content) > 120 else mem.content,
                "consolidation_score": mem.consolidation_score,
            })

    return {
        "archived": archived,
        "guardrails_triggered": guardrails_triggered,
        "top_archived": top_archived,
    }


# ── Full Nightly Sleep Run ────────────────────────────────────────────────────

async def run_sleep_phase(
    session: AsyncSession,
    user_id: str,
    min_memories: int = 3,
    min_age_hours: int = 72,
    project_id: Optional[str] = None,
    run_type: str = "nightly",
) -> dict:
    """
    Full nightly sleep run. Strict step order per architecture spec.
    """
    t_start = time.monotonic()

    # Step 1 — TTL expiry (hard delete, runs FIRST, overrides everything)
    deleted_ttl = await run_ttl_expiry(session, user_id, project_id)

    # Step 2 — Boost consolidation scores for accessed memories
    boost_stats = await boost_consolidation_scores(session, user_id, project_id)

    # Step 3 — Count total scanned (after TTL expiry)
    count_q = select(func.count(Memory.id)).where(
        Memory.user_id == user_id,
        Memory.status == "active",
    )
    if project_id:
        count_q = count_q.where(Memory.project_id == project_id)
    scanned = await session.scalar(count_q) or 0

    # Step 4 — Archive low-score candidates (respects min_memories floor)
    archive_stats = await archive_low_score_memories(
        session, user_id, min_memories, min_age_hours, project_id
    )

    await session.commit()

    duration_ms = int((time.monotonic() - t_start) * 1000)

    # Step 5 — Write SleepRunLog audit record
    log = SleepRunLog(
        user_id=user_id,
        project_id=project_id,
        memories_scanned=scanned,
        memories_consolidated=boost_stats["boosted"],
        avg_score_delta=boost_stats["avg_delta"],
        memories_archived=archive_stats["archived"],
        memories_deleted_ttl=deleted_ttl,
        top_archived=archive_stats["top_archived"],
        guardrails_triggered=archive_stats["guardrails_triggered"],
        run_duration_ms=duration_ms,
        run_type=run_type,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)

    return {
        "run_id": str(log.id),
        "status": "success",
        "scanned": scanned,
        "consolidated": boost_stats["boosted"],
        "avg_score_delta": boost_stats["avg_delta"],
        "archived": archive_stats["archived"],
        "deleted_ttl": deleted_ttl,
        "guardrails_triggered": archive_stats["guardrails_triggered"],
        "run_duration_ms": duration_ms,
        "run_type": run_type,
    }


# ── Mini Consolidation (48h fallback — no Celery) ─────────────────────────────

async def mini_consolidation(
    session: AsyncSession,
    user_id: str,
    project_id: Optional[str] = None,
) -> dict:
    """
    Lightweight sync fallback triggered when last sleep run was > 48h ago.
    Runs only TTL expiry + basic score decay. No Celery dependency.
    """
    deleted_ttl = await run_ttl_expiry(session, user_id, project_id)

    # Mild score decay for memories that haven't been accessed in 30+ days
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    q = select(Memory).where(
        Memory.user_id == user_id,
        Memory.status == "active",
        Memory.last_accessed_at < cutoff,
        Memory.consolidation_score > 0.1,
    )
    if project_id:
        q = q.where(Memory.project_id == project_id)

    result = await session.execute(q)
    stale = result.scalars().all()
    decayed = 0
    for mem in stale:
        mem.consolidation_score = max(0.1, mem.consolidation_score * 0.95)
        decayed += 1

    await session.commit()

    log = SleepRunLog(
        user_id=user_id,
        project_id=project_id,
        memories_scanned=decayed,
        memories_deleted_ttl=deleted_ttl,
        run_type="mini",
        notes="Mini-consolidation — triggered by 48h fallback (last full run overdue).",
    )
    session.add(log)
    await session.commit()

    return {"status": "mini_consolidation_complete", "decayed": decayed, "deleted_ttl": deleted_ttl}
