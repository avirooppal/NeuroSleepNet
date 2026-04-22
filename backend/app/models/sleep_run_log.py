import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SleepRunLog(Base):
    """
    Audit record written at the end of every sleep phase run (nightly + manual).
    Surfaced in dashboard and at GET /v1/sleep/report/{run_id}.
    """
    __tablename__ = "sleep_run_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # Run metrics
    memories_scanned: Mapped[int] = mapped_column(Integer, default=0)
    memories_consolidated: Mapped[int] = mapped_column(Integer, default=0)
    avg_score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    memories_archived: Mapped[int] = mapped_column(Integer, default=0)
    memories_deleted_ttl: Mapped[int] = mapped_column(Integer, default=0)
    run_duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Top 3 archived memories with content preview (for dashboard widget)
    top_archived: Mapped[list] = mapped_column(JSONB, default=list)

    # Guardrails: True if min_memories floor was hit during this run
    guardrails_triggered: Mapped[bool] = mapped_column(default=False)

    run_type: Mapped[str] = mapped_column(String(32), default="nightly")   # nightly | manual | mini

    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
