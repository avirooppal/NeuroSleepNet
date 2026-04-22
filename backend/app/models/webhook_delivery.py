import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class WebhookDelivery(Base):
    """
    Audit log of every webhook delivery attempt.
    Surfaced in dashboard at GET /v1/webhooks/deliveries.
    """
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_summary: Mapped[str] = mapped_column(String(512), nullable=True)
    http_status: Mapped[int] = mapped_column(Integer, nullable=True)   # None = never reached server
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_error: Mapped[str] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    succeeded: Mapped[bool] = mapped_column(default=False, nullable=False)
