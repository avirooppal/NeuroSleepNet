import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel

class BenchmarkRunBase(BaseModel):
    model: str
    overall_score: float
    results: list[Dict[str, Any]] = []

class BenchmarkRunCreate(BenchmarkRunBase):
    pass

class BenchmarkRun(BenchmarkRunBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
