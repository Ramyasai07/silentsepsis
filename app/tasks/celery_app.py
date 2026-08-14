from datetime import timedelta

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "silentsepsis",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "evaluate-all-active-patients": {
            "task": "app.tasks.risk_evaluation.evaluate_all_active_patients",
            "schedule": timedelta(minutes=settings.risk_evaluation_interval_minutes),
        }
    },
)

# Import tasks to ensure they are registered with Celery.
from app.tasks import risk_evaluation  # noqa: F401
