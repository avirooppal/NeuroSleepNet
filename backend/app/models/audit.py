import uuid
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type: Mapped[str] = mapped_column(String, index=True) # e.g. "SLEEP_CONSOLIDATION"
    scanned_count: Mapped[int] = mapped_column(Integer, default=0)
    consolidated_count: Mapped[int] = mapped_column(Integer, default=0)
    archived_count: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[dict] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
