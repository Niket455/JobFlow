from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "careerpilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    timezone="UTC",
    beat_schedule={
        "recheck-jobs": {
            "task": "app.workers.tasks.recheck_jobs",
            "schedule": settings.job_recheck_interval_minutes * 60,
        },
    },
)
