import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db
from ...models.user import User
from ...schemas import memory as memory_schema
from ...services.memory_service import memory_service
from .auth import get_current_user

router = APIRouter()


@router.post("/", response_model=memory_schema.Memory, status_code=status.HTTP_201_CREATED)
async def create_memory(
    memory_in: memory_schema.MemoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Store a new memory. Triggers embedding generation and usage tracking.
    """
    return await memory_service.create_memory(
        session=db,
        user=current_user,
        content=memory_in.content,
        task_id=memory_in.task_id,
        metadata=memory_in.metadata
    )


@router.get("/", response_model=List[memory_schema.Memory])
async def list_memories(
    current_user: Annotated[User, Depends(get_current_user)],
    task_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List memories with optional task filtering and pagination.
    """
    memories, _ = await memory_service.list_memories(
        session=db,
        user_id=current_user.id,
        task_id=task_id,
        page=page,
        size=size
    )
    return memories
