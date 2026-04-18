import logging
import httpx
from celery import Celery
from ..config import settings

logger = logging.getLogger(__name__)

celery_app = Celery("neurosleepnet", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_routes={
        "tasks.sleep.*": {"queue": "sleep"},
        "tasks.webhooks.*": {"queue": "webhooks"},
        "tasks.embed.*": {"queue": "embed"},
    },
    task_default_queue="default",
)

WEBHOOK_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 30,
    "interval_step": 60,
    "interval_max": 300,
}

@celery_app.task(name="tasks.webhooks.deliver", bind=True, max_retries=3)
def deliver_webhook(self, event: str, memory_id: str, project_id: str, content: dict = None):
    # In a real app we'd fetch the subscribed URLs for this project_id from DB
    # We will simulate a delivery for the sake of the task
    
    # Mock URLs the user might have registered
    # Normally this would be a select from WebhookSubscriptions table
    mock_urls = [] 
    
    payload = {
        "event": event,
        "memory_id": memory_id,
        "project_id": project_id,
        "data": content or {}
    }
    
    with httpx.Client(timeout=10.0) as client:
        for url in mock_urls:
            try:
                # fire and forget
                res = client.post(url, json=payload)
                res.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to deliver webhook to {url}: {e}")
                # Exponential backoff retry logic
                raise self.retry(exc=e, countdown=WEBHOOK_RETRY_POLICY["interval_start"] * (2 ** self.request.retries))
    
    return {"status": "dispatched"}
