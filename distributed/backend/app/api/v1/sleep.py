"""
Sleep Engine API routes.

POST /sleep/trigger     → enqueue Celery task (async, non-blocking)
GET  /sleep/status      → last run stats + next scheduled run countdown
GET  /sleep/report/{id} → full audit report from sleep_run_logs
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db
from ...models.user import User
from ...models.sleep_run_log import SleepRunLog
from ...workers.celery_app import celery_app
from ...core.sleep_engine import score_label
from .auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sleep(
    project_id: Optional[str] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    """
    Manually trigger a sleep consolidation run for this user/project.
    Enqueued to the sleep Celery queue — non-blocking, returns immediately.
    """
    task = celery_app.send_task(
        "tasks.sleep.run_consolidation",
        kwargs={
            "user_id": str(current_user.id),
            "project_id": project_id,
        },
        queue="sleep",
    )
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Sleep consolidation run queued. Check /sleep/status for results.",
    }


@router.get("/status")
async def sleep_status(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Last run summary and next scheduled run countdown.
    Dashboard widget: "Last night: 847 scanned · 23 consolidated · 12 archived · Next run in 14h"
    """
    query = select(SleepRunLog).where(
        SleepRunLog.user_id == current_user.id,
    ).order_by(desc(SleepRunLog.created_at)).limit(1)

    if project_id:
        query = query.where(SleepRunLog.project_id == uuid.UUID(project_id))

    result = await db.execute(query)
    last_run = result.scalar_one_or_none()

    # Calculate next run time (3am UTC)
    now = datetime.now(timezone.utc)
    today_3am = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if now.hour >= 3:
        from datetime import timedelta
        next_run = today_3am + timedelta(days=1)
    else:
        next_run = today_3am

    hours_until = round((next_run - now).total_seconds() / 3600, 1)

    last_run_data = None
    if last_run:
        last_run_data = {
            "run_id": str(last_run.id),
            "run_type": last_run.run_type,
            "scanned": last_run.memories_scanned,
            "consolidated": last_run.memories_consolidated,
            "archived": last_run.memories_archived,
            "deleted_ttl": last_run.memories_deleted_ttl,
            "guardrails_triggered": last_run.guardrails_triggered,
            "run_duration_ms": last_run.run_duration_ms,
            "ran_at": last_run.created_at.isoformat(),
            "summary": (
                f"{last_run.memories_scanned} scanned · "
                f"{last_run.memories_consolidated} consolidated · "
                f"{last_run.memories_archived} archived · "
                f"{last_run.memories_deleted_ttl} deleted"
            ),
        }

    return {
        "last_run": last_run_data,
        "next_run_at": next_run.isoformat(),
        "hours_until_next_run": hours_until,
        "schedule": "0 3 * * * (3am UTC daily)",
    }


@router.get("/report/{run_id}")
async def sleep_report(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full audit report for a specific sleep run.
    Includes top 3 archived memories, guardrails triggered, full metrics.
    """
    run = await db.get(SleepRunLog, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Sleep run report not found.")
    if run.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    return {
        "run_id": str(run.id),
        "run_type": run.run_type,
        "project_id": str(run.project_id) if run.project_id else None,
        "memories_scanned": run.memories_scanned,
        "memories_consolidated": run.memories_consolidated,
        "avg_score_delta": run.avg_score_delta,
        "memories_archived": run.memories_archived,
        "memories_deleted_ttl": run.memories_deleted_ttl,
        "top_archived": run.top_archived,
        "guardrails_triggered": run.guardrails_triggered,
        "run_duration_ms": run.run_duration_ms,
        "notes": run.notes,
        "ran_at": run.created_at.isoformat(),
    }


@router.get("/history")
async def sleep_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recent sleep run history — last N runs for the current user."""
    query = select(SleepRunLog).where(
        SleepRunLog.user_id == current_user.id,
    ).order_by(desc(SleepRunLog.created_at)).limit(limit)

    result = await db.execute(query)
    runs = result.scalars().all()

    return [
        {
            "run_id": str(r.id),
            "run_type": r.run_type,
            "scanned": r.memories_scanned,
            "consolidated": r.memories_consolidated,
            "archived": r.memories_archived,
            "deleted_ttl": r.memories_deleted_ttl,
            "run_duration_ms": r.run_duration_ms,
            "ran_at": r.created_at.isoformat(),
        }
        for r in runs
    ]
