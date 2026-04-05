import os
from celery import Celery
from celery.schedules import crontab

from ..config import settings

celery_app = Celery(
    "neurosleepnet_workers",
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Celery Beat Schedule
    beat_schedule={
        "nightly-sleep-consolidation": {
            "task": "app.workers.tasks.run_nightly_sleep",
            "schedule": crontab(hour=2, minute=0),  # 2:00 AM UTC
        }
    }
)

if __name__ == "__main__":
    celery_app.start()
