import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from .memory import Memory


class DashboardStats(BaseModel):
    total_memories: int
    monthly_ops: int
    monthly_ops_limit: Optional[int]
    memory_health_score: float  # 0-100
    last_sleep_run: Optional[datetime]
    last_sleep_status: str


class AttentionMemory(BaseModel):
    id: uuid.UUID
    content: str
    attention_score: float
    consolidation_score: float
    task_name: Optional[str]


class AttentionHeatmap(BaseModel):
    memories: List[AttentionMemory]


class MemoryDrift(BaseModel):
    stale_count: int
    at_risk_count: int
    drift_score: float  # 0-1.0


class SleepRunLog(BaseModel):
    id: uuid.UUID
    date: datetime
    duration_seconds: int
    memories_consolidated: int
    memories_archived: int
    memories_pruned: int
    status: str
