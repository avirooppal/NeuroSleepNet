"""
Celery task definitions for the `webhooks` queue.

Queue: webhooks
Workers: 3 concurrent (IO-bound, time-sensitive)
Retry policy: exponential backoff 30s → 90s → 270s, cap 300s, timeout 10s

CRITICAL: Webhooks are NEVER fired synchronously inside FastAPI handlers.
FastAPI handler commits to DB, then enqueues here. This task's latency
must never affect API response times.
"""
import hashlib
import hmac
import json
import logging
import os

import httpx

from ..celery_app import celery_app

logger = logging.getLogger(__name__)

# ── Retry Policy (locked) ──────────────────────────────────────────────────────

_MAX_RETRIES = int(os.environ.get("NSN_WEBHOOK_MAX_RETRIES", 3))
_TIMEOUT = int(os.environ.get("NSN_WEBHOOK_TIMEOUT_SECONDS", 10))


def _sign_payload(secret: str, payload: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


@celery_app.task(
    name="tasks.webhooks.deliver",
    bind=True,
    max_retries=_MAX_RETRIES,
    default_retry_delay=30,
    acks_late=True,
)
def deliver_webhook(
    self,
    event: str,
    project_id: str,
    memory_id: str = None,
    timestamp: str = None,
    extra: dict = None,
):
    """
    Deliver a single webhook event to all registered endpoints for this project.

    Called AFTER db.commit() in the FastAPI handler — never before.
    On failure: exponential backoff retries. After max_retries: write to
    webhook_deliveries table as failed (surfaced in dashboard).
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    import re

    # Use sync engine for Celery context
    db_url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
    engine = create_engine(db_url)

    payload = {
        "event": event,
        "project_id": project_id,
        "memory_id": memory_id,
        "timestamp": timestamp,
        **(extra or {}),
    }
    payload_json = json.dumps(payload, default=str)

    with Session(engine) as session:
        # Fetch registered active webhooks for this project that subscribe to this event
        from ...models.webhook import Webhook
        from ...models.webhook_delivery import WebhookDelivery

        webhooks = session.execute(
            select(Webhook).where(
                Webhook.project_id == project_id,
                Webhook.is_active == True,
            )
        ).scalars().all()

        # Filter to webhooks subscribed to this event type
        subscribed = [
            wh for wh in webhooks
            if not wh.event_types or event in wh.event_types
        ]

        if not subscribed:
            return {"delivered": 0, "event": event}

        delivered_count = 0
        for webhook in subscribed:
            headers = {
                "Content-Type": "application/json",
                "X-NSN-Event": event,
                "X-NSN-Project": project_id,
            }
            if webhook.secret:
                headers["X-NSN-Signature"] = f"sha256={_sign_payload(webhook.secret, payload_json)}"

            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event=event,
                payload_summary=payload_json[:512],
            )

            try:
                with httpx.Client(timeout=_TIMEOUT) as client:
                    resp = client.post(webhook.url, content=payload_json, headers=headers)
                    delivery.http_status = resp.status_code
                    delivery.succeeded = 200 <= resp.status_code < 300
                    if not delivery.succeeded:
                        delivery.last_error = f"HTTP {resp.status_code}: {resp.text[:256]}"
                    else:
                        delivered_count += 1
            except Exception as exc:
                delivery.http_status = None
                delivery.last_error = str(exc)[:512]
                delivery.succeeded = False

            delivery.attempt_count = self.request.retries + 1
            session.add(delivery)

        session.commit()

        if delivered_count < len(subscribed):
            # Some failed — retry the whole task with backoff
            failed_count = len(subscribed) - delivered_count
            logger.warning(f"[Webhooks] {failed_count}/{len(subscribed)} deliveries failed for event={event}")
            try:
                raise self.retry(
                    countdown=30 * (3 ** self.request.retries),  # 30s, 90s, 270s
                    exc=Exception(f"{failed_count} webhook deliveries failed"),
                )
            except self.MaxRetriesExceededError:
                logger.error(f"[Webhooks] Max retries exceeded for event={event}, project={project_id}")

        return {"delivered": delivered_count, "total": len(subscribed), "event": event}


@celery_app.task(name="tasks.webhooks.retry_failed", bind=True)
def retry_failed_webhooks(self):
    """
    Periodic sweep — finds permanently failed deliveries from the last 24h
    and surfaces them in the dashboard. Does not re-attempt (that's the caller's job
    via the manual retry button). Just ensures the failure log is complete.
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from datetime import datetime, timedelta, timezone

    db_url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
    engine = create_engine(db_url)

    with Session(engine) as session:
        from ...models.webhook_delivery import WebhookDelivery
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        failed = session.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.succeeded == False,
                WebhookDelivery.delivered_at >= cutoff,
            )
        ).scalars().all()

        logger.info(f"[Webhooks] retry_failed_webhooks: {len(failed)} undelivered in last 24h.")
        return {"undelivered_24h": len(failed)}
