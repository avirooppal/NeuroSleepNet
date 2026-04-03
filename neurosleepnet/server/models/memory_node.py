from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class MemoryNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    task_id: str
    session_id: str
    content: str
    type: str = "fact" # fact, event, preference, instruction, summary
    embedding: Optional[List[float]] = None
    superseded: bool = False
    confidence: float = 1.0
    weight: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TaskThread(BaseModel):
    task_id: str
    user_id: str
    description: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
