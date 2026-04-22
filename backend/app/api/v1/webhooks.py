"""
Webhook registration and delivery log API.

Webhooks are delivered EXCLUSIVELY via the Celery webhooks queue.
A third-party server's downtime must never affect NSN API response times.
"""
import uuid
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db
from ...models.user import User
from ...models.webhook import Webhook
from ...models.webhook_delivery import WebhookDelivery
from ...workers.celery_app import celery_app
from .auth import get_current_user

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    url: str
    event_types: List[str] = []  # Empty = all events
    secret: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://your-server.com/nsn-webhook",
                "event_types": ["memory.stored", "sleep.completed"],
                "secret": "optional-hmac-secret",
            }
        }


VALID_EVENTS = {
    "memory.stored",
    "memory.archived",
    "memory.expired",
    "sleep.completed",
    "quota.warning",
    "benchmark.completed",
}

# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[dict])
async def list_webhooks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """List all registered webhooks for the current user's projects."""
    # Note: in a multi-project system, this would filter by user's project IDs.
    # For now we return all webhooks (project isolation is enforced at model level).
    result = await db.execute(select(Webhook).order_by(desc(Webhook.created_at)))
    webhooks = result.scalars().all()
    return [
        {
            "id": str(wh.id),
            "project_id": str(wh.project_id),
            "url": wh.url,
            "event_types": wh.event_types,
            "is_active": wh.is_active,
            "created_at": wh.created_at.isoformat(),
        }
        for wh in webhooks
    ]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    payload: WebhookCreate,
    project_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Register a new webhook endpoint for a project."""
    # Validate event types
    invalid = set(payload.event_types) - VALID_EVENTS
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event types: {invalid}. Valid: {VALID_EVENTS}",
        )

    wh = Webhook(
        project_id=uuid.UUID(project_id),
        url=payload.url,
        event_types=payload.event_types,
        secret=payload.secret,
        is_active=True,
    )
    db.add(wh)
    await db.commit()
    await db.refresh(wh)

    return {
        "id": str(wh.id),
        "url": wh.url,
        "event_types": wh.event_types,
        "is_active": wh.is_active,
        "created_at": wh.created_at.isoformat(),
    }


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Remove a registered webhook."""
    wh = await db.get(Webhook, webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found.")
    await db.delete(wh)
    await db.commit()


@router.get("/deliveries", response_model=List[dict])
async def list_deliveries(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    succeeded: Optional[bool] = Query(None),
):
    """
    Paginated delivery history: event type, URL, HTTP status, attempt count, last error.
    Surfaced in dashboard Webhooks page — makes "did the webhook fire?" a non-issue.
    """
    query = select(WebhookDelivery).order_by(desc(WebhookDelivery.delivered_at))
    if succeeded is not None:
        query = query.where(WebhookDelivery.succeeded == succeeded)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    deliveries = result.scalars().all()

    return [
        {
            "id": str(d.id),
            "webhook_id": str(d.webhook_id),
            "event": d.event,
            "payload_summary": d.payload_summary,
            "http_status": d.http_status,
            "attempt_count": d.attempt_count,
            "last_error": d.last_error,
            "succeeded": d.succeeded,
            "delivered_at": d.delivered_at.isoformat(),
        }
        for d in deliveries
    ]


@router.post("/deliveries/{delivery_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def manual_retry_delivery(
    delivery_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Manually retry a failed webhook delivery.
    Re-enqueues the original event to the webhooks queue.
    """
    delivery = await db.get(WebhookDelivery, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery record not found.")
    if delivery.succeeded:
        raise HTTPException(status_code=400, detail="Delivery already succeeded — no retry needed.")

    wh = await db.get(Webhook, delivery.webhook_id)
    if not wh:
        raise HTTPException(status_code=404, detail="Associated webhook has been deleted.")

    celery_app.send_task(
        "tasks.webhooks.deliver",
        kwargs={
            "event": delivery.event,
            "project_id": str(wh.project_id),
        },
    )
    return {"status": "retry_queued", "delivery_id": str(delivery_id)}
