import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Webhook(Base):
    """
    Registered webhook endpoint for a project.
    Events are delivered exclusively via the Celery webhooks queue — never synchronously.
    """
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # JSONB list of subscribed event types:
    # ["memory.stored", "sleep.completed", "quota.warning", ...]
    event_types: Mapped[list] = mapped_column(JSONB, default=list)

    # Optional HMAC-SHA256 signing secret — sent as X-NSN-Signature header
    secret: Mapped[str] = mapped_column(String(256), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
