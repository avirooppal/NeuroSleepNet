import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

class ProjectBase(BaseModel):
    name: str
    attention_weights: Dict[str, float] = Field(default_factory=lambda: {"w1": 0.5, "w2": 0.2, "w3": 0.2, "w4": 0.1})

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
