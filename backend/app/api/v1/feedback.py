import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...deps import get_db
from ...services.feedback_service import FeedbackService
from .auth import get_current_user
from ...models.user import User

router = APIRouter()

class ImplicitFeedbackRequest(BaseModel):
    text: str
    memory_ids: List[uuid.UUID]

@router.post("/implicit", status_code=status.HTTP_202_ACCEPTED)
async def process_implicit_feedback(
    request: ImplicitFeedbackRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process implicit feedback from the SDK.
    Fire-and-forget: returns 202 immediately and processes in background.
    """
    signal = FeedbackService.analyze_feedback_signal(request.text)
    
    if signal is not None:
        # Process in background to avoid blocking the agent
        background_tasks.add_task(
            FeedbackService.update_memory_feedback,
            db,
            request.memory_ids,
            signal
        )
    
    return {"status": "accepted", "signal_detected": signal is not None}

@router.post("/explicit", status_code=status.HTTP_200_OK)
async def process_explicit_feedback(
    memory_id: uuid.UUID,
    helpful: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Explicit feedback from user or dashboard.
    """
    signal = 1.0 if helpful else 0.0
    await FeedbackService.update_memory_feedback(db, [memory_id], signal)
    return {"status": "success"}
