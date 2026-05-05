import logging
import os

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

celery_app = Celery(
    "neurosleepnet",
    broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    include=[
        "app.workers.tasks.sleep",
        "app.workers.tasks.webhooks",
        "app.workers.tasks.embed",
    ],
)

# ── Three queues — never merged ───────────────────────────────────────────────
celery_app.conf.task_routes = {
    "tasks.sleep.*":    {"queue": "sleep"},      # Long-running, CPU-bound, nightly
    "tasks.webhooks.*": {"queue": "webhooks"},   # Short, IO-bound, time-sensitive
    "tasks.embed.*":    {"queue": "embed"},      # Fast, high-frequency, hot path
}

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

# ── Celery Beat Schedule ──────────────────────────────────────────────────────
# NSN_SLEEP_SCHEDULE env var format: "minute hour * * *"
_sleep_schedule = os.environ.get("NSN_SLEEP_SCHEDULE", "0 3 * * *").split()
_minute, _hour = _sleep_schedule[0], _sleep_schedule[1]

celery_app.conf.beat_schedule = {
    "nightly-sleep-consolidation": {
        "task": "tasks.sleep.run_consolidation",
        "schedule": crontab(minute=_minute, hour=_hour),
        "options": {"queue": "sleep"},
    },
    "daily-ttl-expiry": {
        "task": "tasks.sleep.run_ttl_expiry",
        "schedule": crontab(minute="30", hour=_hour),   # 30 min after consolidation
        "options": {"queue": "sleep"},
    },
    "webhook-failed-sweep": {
        "task": "tasks.webhooks.retry_failed",
        "schedule": crontab(minute="0", hour="*/6"),     # Every 6 hours
        "options": {"queue": "webhooks"},
    },
}

# ── Webhook Retry Policy (kept here for reference by task modules) ─────────────
WEBHOOK_RETRY_POLICY = {
    "max_retries": int(os.environ.get("NSN_WEBHOOK_MAX_RETRIES", 3)),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "timeout": int(os.environ.get("NSN_WEBHOOK_TIMEOUT_SECONDS", 10)),
    "throw": False,
}
