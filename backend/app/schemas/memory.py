import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Task Schemas
class TaskBase(BaseModel):
    name: str


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: uuid.UUID
    user_id: uuid.UUID
    residual_context: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Memory Schemas
class MemoryBase(BaseModel):
    content: str
    task_id: Optional[uuid.UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryCreate(MemoryBase):
    pass


class Memory(MemoryBase):
    id: uuid.UUID
    user_id: uuid.UUID
    consolidation_score: float
    access_count: int
    status: str
    created_at: datetime
    last_accessed_at: datetime
    last_consolidated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemorySearch(BaseModel):
    query: str
    task_id: Optional[uuid.UUID] = None
    top_k: int = 5
    min_attention_score: float = 0.3


class MemorySearchResult(Memory):
    attention_score: float
    why_retrieved: str


class SearchResponse(BaseModel):
    memories: List[MemorySearchResult]
    sleep_last_run: Optional[datetime] = None
    residual_context_applied: bool = False
