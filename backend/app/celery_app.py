from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from .settings import settings

celery_app = Celery(
    "jarvis",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.jobs", "app.tasks.facebook_auto"],  # ✅ added
)

celery_app.conf.update(
    task_default_queue="default",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "nightly_inbox_triage": {
        "task": "app.tasks.jobs.nightly_inbox_triage",
        "schedule": crontab(hour=settings.NIGHTLY_HOUR, minute=settings.NIGHTLY_MINUTE),
    },
    "facebook_autoreply_tick": {
    "task": "app.tasks.jobs.facebook_autoreply_tick",
    "schedule": settings.FACEBOOK_AUTOREPLY_POLL_SECONDS,
},

    "nightly_product_research": {
        "task": "app.tasks.jobs.nightly_product_research",
        "schedule": crontab(hour=settings.NIGHTLY_HOUR, minute=(settings.NIGHTLY_MINUTE + 5) % 60),
    },
    "nightly_content_generation": {
        "task": "app.tasks.jobs.nightly_content_generation",
        "schedule": crontab(hour=settings.NIGHTLY_HOUR, minute=(settings.NIGHTLY_MINUTE + 10) % 60),
    },
    "daily_report": {
        "task": "app.tasks.jobs.daily_report",
        "schedule": crontab(hour=settings.REPORT_HOUR, minute=settings.REPORT_MINUTE),
    },

    # ✅ NEW: auto reply every minute
    "facebook_auto_reply_every_minute": {
        "task": "app.tasks.facebook_auto.facebook_auto_reply",
        "schedule": crontab(minute="*/1"),
    },

    # ✅ NEW: auto post daily at 10:00 UTC
    "facebook_auto_post_daily": {
        "task": "app.tasks.facebook_auto.facebook_auto_post",
        "schedule": crontab(hour=10, minute=0),
    },
}
