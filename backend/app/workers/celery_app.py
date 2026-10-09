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
        "run-alerts": {
            "task": "app.workers.tasks.run_alerts",
            "schedule": settings.alert_run_interval_minutes * 60,
        },
        "discover-leads": {
            "task": "app.workers.tasks.discover_leads",
            "schedule": settings.lead_discovery_interval_minutes * 60,
        },
        "refresh-notifications": {
            "task": "app.workers.tasks.refresh_notifications",
            "schedule": settings.notification_refresh_interval_minutes * 60,
        },
        "deliver-notification-emails": {
            "task": "app.workers.tasks.deliver_notification_emails",
            "schedule": settings.notification_email_interval_minutes * 60,
        },
    },
)
