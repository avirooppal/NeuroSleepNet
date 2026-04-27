import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

class MemoryBase(BaseModel):
    content: str
    project_id: Optional[Union[uuid.UUID, str]] = None
    session_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance: float = 1.0
    ttl_days: Optional[int] = Field(default=None, description="Hard deletion after N days")


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
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MemorySearch(BaseModel):
    query: str
    project_id: Optional[Union[uuid.UUID, str]] = None
    top_k: int = 5
    min_attention_score: float = 0.3


class MemorySearchResult(Memory):
    attention_score: float
    why_retrieved: str
    consolidation_label: str = "Weak"

    def __init__(self, **data):
        super().__init__(**data)
        if self.consolidation_score >= 0.8:
            self.consolidation_label = "Core"
        elif self.consolidation_score >= 0.4:
            self.consolidation_label = "Established"
        elif self.consolidation_score >= 0.1:
            self.consolidation_label = "Developing"
        else:
            self.consolidation_label = "Weak"


class SearchResponse(BaseModel):
    memories: List[MemorySearchResult]
    sleep_last_run: Optional[datetime] = None
    residual_context_applied: bool = False
