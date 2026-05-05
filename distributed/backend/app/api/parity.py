"""
Dashboard Parity Router — maps standard /api/* endpoints to internal v1 routes.
Ensures the same React frontend works in both Local SDK mode and Docker Self-Host mode.
"""
from fastapi import APIRouter, Depends, Query
from typing import Annotated, Optional
import uuid

from .v1 import dashboard, memories, sleep, analytics
from .v1.auth import get_current_user
from ..models.user import User

parity_router = APIRouter()

# 1. Stats
@parity_router.get("/stats")
async def sdk_stats(
    project: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db = Depends(dashboard.get_db)
):
    # Map to the dashboard stats or analytics stats
    return await dashboard.get_dashboard_stats(current_user, db)

# 2. Misses
@parity_router.get("/misses")
async def sdk_misses(
    project: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db = Depends(dashboard.get_db)
):
    # This matches the local SDK's /api/misses
    # We'll just return a list from the AuditLog for now, or the miss log if we have it
    from ..models.audit_log import AuditLog
    from sqlalchemy import select, desc
    stmt = select(AuditLog).where(
        AuditLog.user_id == current_user.id,
        AuditLog.action == "memory.missed"
    ).order_by(desc(AuditLog.created_at)).limit(50)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return {"misses": [l.metadata for l in logs]}

# 3. Pins
@parity_router.get("/pins")
async def sdk_pins(
    project: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db = Depends(dashboard.get_db)
):
    # List all pins for user
    from ..models.memory import Memory
    from sqlalchemy import select
    stmt = select(Memory).where(
        Memory.user_id == current_user.id,
        Memory.tags.contains(["pinned"])
    )
    res = await db.execute(stmt)
    pins = res.scalars().all()
    return {"pins": pins}

# 4. Sleep
@parity_router.get("/sleep")
async def sdk_sleep_status(
    project: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db = Depends(dashboard.get_db)
):
    return await sleep.sleep_status(project, current_user, db)

@parity_router.post("/sleep")
async def sdk_trigger_sleep(
    current_user: User = Depends(get_current_user),
):
    return await sleep.trigger_sleep(None, current_user)

# 5. Events (SSE)
@parity_router.get("/events")
async def sdk_events(
    project: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    # In self-host, we might not have a live SSE stream easily accessible without a queue.
    # For now, we'll return a placeholder or implement a simple Redis-backed stream.
    from fastapi.responses import StreamingResponse
    import asyncio
    
    async def event_generator():
        yield "data: {\"type\": \"info\", \"message\": \"SSE connected to self-host\"}\n\n"
        while True:
            await asyncio.sleep(30)
            yield "data: {\"type\": \"ping\"}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
