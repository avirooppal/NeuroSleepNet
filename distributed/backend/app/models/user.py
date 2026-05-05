import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .api_key import ApiKey
    from .project import Project
    from .benchmark import BenchmarkRun
    from .memory import Memory
    from .usage_log import UsageLog
    from .audit_log import AuditLog


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # None for OAuth-only users
    github_id: Mapped[Optional[int]] = mapped_column(nullable=True, unique=True, index=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    plan: Mapped[str] = mapped_column(String, default="free")  # 'free' | 'paid'
    razorpay_subscription_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    benchmark_runs: Mapped[List["BenchmarkRun"]] = relationship("BenchmarkRun", cascade="all, delete-orphan")
    memories: Mapped[List["Memory"]] = relationship("Memory", back_populates="user", cascade="all, delete-orphan")
    usage_logs: Mapped[List["UsageLog"]] = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
