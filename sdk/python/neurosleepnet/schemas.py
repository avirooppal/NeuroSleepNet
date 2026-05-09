"""
Shared Pydantic schemas for NeuroSleepNet (Phase 6.2).

Provides common data models used across SDK, backend, and clients.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    # Fallback when pydantic is not installed
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class Field:
        def __init__(self, default=None, description=None, **kwargs):
            self.default = default
            self.description = description
    
    def validator(field_name, **kwargs):
        def decorator(func):
            return func
        return decorator


class MemoryType(str, Enum):
    """Memory type enumeration."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    DECLARATIVE = "declarative"


class MemoryStatus(str, Enum):
    """Memory status enumeration."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class Memory(BaseModel):
    """Core memory data model."""
    id: str = Field(..., description="Unique memory identifier")
    content: str = Field(..., description="Memory content text")
    user_id: Optional[str] = Field(None, description="User who owns this memory")
    project: str = Field(..., description="Project this memory belongs to")
    memory_type: MemoryType = Field(MemoryType.SEMANTIC, description="Type of memory")
    status: MemoryStatus = Field(MemoryStatus.ACTIVE, description="Current status")
    importance: float = Field(1.0, description="Importance score (0.0-1.0)")
    feedback_score: Optional[float] = Field(None, description="User feedback score")
    consolidation_score: Optional[float] = Field(None, description="Sleep consolidation score")
    access_count: int = Field(0, description="Number of times accessed")
    pinned: bool = Field(False, description="Whether memory is pinned")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_accessed_at: Optional[datetime] = Field(None, description="Last access timestamp")
    last_consolidated_at: Optional[datetime] = Field(None, description="Last consolidation timestamp")
    ttl_days: Optional[int] = Field(None, description="Time-to-live in days")
    deprecated_by: Optional[str] = Field(None, description="ID of memory that deprecated this one")
    label: Optional[str] = Field(None, description="Human-readable label")

    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Content cannot be empty')
        return v.strip()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class SearchResult(Memory):
    """Memory with search relevance information."""
    attention_score: float = Field(..., description="Attention/relevance score")
    why_retrieved: str = Field(..., description="Reason for retrieval")
    similarity: Optional[float] = Field(None, description="Embedding similarity score")


class SearchRequest(BaseModel):
    """Search request parameters."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    user_id: Optional[str] = Field(None, description="Filter by user")
    memory_type: Optional[MemoryType] = Field(None, description="Filter by memory type")
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum importance")
    pinned_only: bool = Field(False, description="Only return pinned memories")


class SearchResponse(BaseModel):
    """Search response containing results and metadata."""
    memories: List[SearchResult] = Field(..., description="Search results")
    total_found: int = Field(..., description="Total memories found")
    query_time_ms: float = Field(..., description="Query execution time in milliseconds")
    residual_context_applied: bool = Field(False, description="Whether residual context was applied")
    sleep_last_run: Optional[datetime] = Field(None, description="Last sleep cycle timestamp")


class StoreRequest(BaseModel):
    """Store memory request."""
    content: str = Field(..., description="Memory content")
    user_id: Optional[str] = Field(None, description="User who owns this memory")
    memory_type: MemoryType = Field(MemoryType.SEMANTIC, description="Type of memory")
    importance: float = Field(1.0, ge=0.0, le=1.0, description="Importance score")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    ttl_days: Optional[int] = Field(None, ge=1, description="Time-to-live in days")
    pinned: bool = Field(False, description="Whether to pin this memory")
    label: Optional[str] = Field(None, description="Human-readable label")


class StoreResponse(BaseModel):
    """Store memory response."""
    id: str = Field(..., description="ID of stored memory")
    status: str = Field("stored", description="Storage status")


class FeedbackRequest(BaseModel):
    """Feedback submission request."""
    memory_id: str = Field(..., description="Memory to provide feedback for")
    user_id: Optional[str] = Field(None, description="User providing feedback")
    feedback_type: str = Field(..., description="Type of feedback")
    score: float = Field(..., ge=-1.0, le=1.0, description="Feedback score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional feedback metadata")


class User(BaseModel):
    """User data model."""
    id: str = Field(..., description="User ID")
    email: Optional[str] = Field(None, description="User email")
    plan: str = Field("free", description="User plan (free, pro, enterprise)")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional user metadata")


class ApiKey(BaseModel):
    """API key data model."""
    id: str = Field(..., description="Key ID")
    key_hash: str = Field(..., description="Hashed key value")
    name: str = Field(..., description="Key name/description")
    is_active: bool = Field(True, description="Whether key is active")
    created_at: datetime = Field(..., description="Key creation timestamp")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Key expiration timestamp")
    user_id: str = Field(..., description="User who owns this key")


class Project(BaseModel):
    """Project data model."""
    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    user_id: str = Field(..., description="User who owns this project")
    created_at: datetime = Field(..., description="Project creation timestamp")
    memory_count: int = Field(0, description="Number of memories in project")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Project settings")


class SleepCycle(BaseModel):
    """Sleep cycle data model."""
    id: str = Field(..., description="Cycle ID")
    project_id: str = Field(..., description="Project this cycle belongs to")
    started_at: datetime = Field(..., description="Cycle start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Cycle completion timestamp")
    status: str = Field(..., description="Cycle status (running, completed, failed)")
    memories_processed: int = Field(0, description="Number of memories processed")
    memories_consolidated: int = Field(0, description="Number of memories consolidated")
    config: Dict[str, Any] = Field(default_factory=dict, description="Cycle configuration")


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Check timestamp")
    checks: Dict[str, str] = Field(default_factory=dict, description="Individual component checks")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")


class ErrorDetail(BaseModel):
    """Error detail model for API responses."""
    error: str = Field(..., description="Error type/code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")


# Export schemas for convenience
__all__ = [
    "MemoryType",
    "MemoryStatus", 
    "Memory",
    "SearchResult",
    "SearchRequest",
    "SearchResponse",
    "StoreRequest",
    "StoreResponse",
    "FeedbackRequest",
    "User",
    "ApiKey",
    "Project",
    "SleepCycle",
    "HealthCheck",
    "ErrorDetail",
]
