from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "copilote",
    broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,
)

# Re-analyse hebdomadaire de la watchlist — tous les dimanches à 07h00 UTC
# Vérification quotidienne des alertes prix — tous les jours à 08h00 UTC
# Rapport PDF hebdomadaire par email — tous les dimanches à 09h00 UTC (après 07h00 + 08h00)
# Vérification quotidienne alertes composite_score — tous les jours à 10h00 UTC
# Screener hebdomadaire watchlist — tous les dimanches à 11h00 UTC (après les autres tâches)
celery_app.conf.beat_schedule = {
    "run-watchlist-analysis-weekly": {
        "task": "run_watchlist_analysis",
        "schedule": crontab(hour=7, minute=0, day_of_week=0),
    },
    "run-price-alert-check-daily": {
        "task": "run_price_alert_check",
        "schedule": crontab(hour=8, minute=0),
    },
    "run-weekly-watchlist-report": {
        "task": "run_weekly_watchlist_report",
        "schedule": crontab(hour=9, minute=0, day_of_week=0),
    },
    "run-composite-alert-check-daily": {
        "task": "run_composite_alert_check",
        "schedule": crontab(hour=10, minute=0),
    },
    "run-scheduled-screener": {
        "task": "run_scheduled_screener",
        "schedule": crontab(day_of_week="sunday", hour=11, minute=0),
    },
    # Rapport PDF mensuel consolidé — 1er du mois à 08h00 UTC
    "run-monthly-report": {
        "task": "app.workers.tasks.run_monthly_report",
        "schedule": crontab(hour=8, minute=0, day_of_month=1),
    },
}
