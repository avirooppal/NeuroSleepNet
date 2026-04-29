import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User
    from .project import Project


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Optional[Vector]] = mapped_column(Vector(384), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default={})
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    consolidation_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 -> pruned, 1.0 -> permanent
    feedback_score: Mapped[float] = mapped_column(Float, default=0.0)       # -1.0 -> negative, 1.0 -> positive
    importance: Mapped[float] = mapped_column("importance_weight", Float, default=1.0) # 0.0 -> trivial, 2.0 -> critical
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="active")  # 'active' | 'archived' | 'pruned'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_consolidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=2)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memories")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="memories")
