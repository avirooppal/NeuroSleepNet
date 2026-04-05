import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db
from ...models.user import User
from ...models.task import Task
from .auth import get_current_user
from ...schemas import memory as memory_schema

router = APIRouter()


@router.post("/", response_model=memory_schema.Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: memory_schema.TaskCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task/context for memories.
    """
    task = Task(
        user_id=current_user.id,
        name=task_in.name
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/", response_model=List[memory_schema.Task])
async def list_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    List all tasks for current user.
    """
    from sqlalchemy import select
    result = await db.execute(
        select(Task).where(Task.user_id == current_user.id).order_by(Task.created_at.desc())
    )
    return result.scalars().all()
