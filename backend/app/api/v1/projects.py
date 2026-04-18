import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...deps import get_db
from ...models.user import User
from ...models.project import Project
from ...schemas import project as project_schema
from .auth import get_current_user

router = APIRouter()

@router.post("/", response_model=project_schema.Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: project_schema.ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    project = Project(
        user_id=current_user.id,
        name=project_in.name,
        attention_weights=project_in.attention_weights
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

@router.get("/", response_model=List[project_schema.Project])
async def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(Project.user_id == current_user.id))
    return result.scalars().all()

@router.delete("/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.user_id == current_user.id))
    project = result.scalars().first()
    if project:
        await db.delete(project)
        await db.commit()
    return {"status": "deleted"}
