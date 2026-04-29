from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...deps import get_db
from ...models.user import User
from ...models.audit_log import AuditLog
from .auth import get_current_user
import uuid

router = APIRouter()

@router.post("/push", status_code=status.HTTP_201_CREATED)
async def push_telemetry(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Receives telemetry from local SDKs to populate the dashboard.
    Does not store actual memory vectors, only activity metadata.
    """
    project_id = data.get("project_id")
    event_type = data.get("event")
    
    # 1. Log the activity for the "Live SDK Logs" panel
    if event_type == "memory.retrieved":
        log = AuditLog(
            user_id=current_user.id,
            action="memory.retrieved",
            metadata={
                "query": data.get("query"),
                "memories": data.get("memories", []),
                "attention_scores": data.get("scores", []),
                "project_id": project_id
            }
        )
        db.add(log)
    
    # 2. Update stats by creating a 'Shadow' memory in the backend
    elif event_type == "memory.stored":
        from ...models.memory import Memory
        # We store a shadow stub so the dashboard counters work
        # We don't store the actual content for privacy
        shadow = Memory(
            user_id=current_user.id,
            content="[LOCAL_SYNC_STUB]",
            metadata_={"local_id": data.get("id"), "project_id": project_id},
            status="active"
        )
        db.add(shadow)
        
        log = AuditLog(
            user_id=current_user.id,
            action="memory.stored",
            metadata={"count": 1, "project_id": project_id}
        )
        db.add(log)

    await db.commit()
    return {"status": "synced"}
