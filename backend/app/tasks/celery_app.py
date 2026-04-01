from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "patent_pulse",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.ingest_grants",
        "app.tasks.ingest_applications",
        "app.tasks.ingest_epo",
        "app.tasks.ingest_wipo",
        "app.tasks.summarize",
        "app.tasks.embeddings",
        "app.tasks.theme_matcher",
        "app.tasks.expiry_watch",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/New_York",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.ingest_grants.*": {"queue": "ingestion"},
        "app.tasks.ingest_applications.*": {"queue": "ingestion"},
        "app.tasks.summarize.*": {"queue": "summarization"},
        "app.tasks.expiry_watch.*": {"queue": "maintenance"},
    },
    task_default_retry_delay=60,
    task_max_retries=3,
)

celery_app.conf.beat_schedule = {
    # USPTO - Tuesday grants, Thursday applications
    "ingest-weekly-grants": {
        "task": "app.tasks.ingest_grants.ingest_weekly_grants",
        "schedule": crontab(hour=10, minute=0, day_of_week=2),
        "options": {"queue": "ingestion"},
    },
    "ingest-weekly-applications": {
        "task": "app.tasks.ingest_applications.ingest_weekly_applications",
        "schedule": crontab(hour=10, minute=0, day_of_week=4),
        "options": {"queue": "ingestion"},
    },
    # EPO - Wednesday publications
    "ingest-weekly-epo": {
        "task": "app.tasks.ingest_epo.ingest_weekly_epo",
        "schedule": crontab(hour=12, minute=0, day_of_week=3),
        "options": {"queue": "ingestion"},
    },
    # WIPO PCT - Thursday publications (limited scope per ToS)
    "ingest-weekly-pct": {
        "task": "app.tasks.ingest_wipo.ingest_weekly_pct",
        "schedule": crontab(hour=14, minute=0, day_of_week=4),
        "options": {"queue": "ingestion"},
    },
    # Family resolution - Friday (after weekly ingestion)
    "resolve-families-weekly": {
        "task": "app.tasks.ingest_epo.resolve_epo_families",
        "schedule": crontab(hour=6, minute=0, day_of_week=5),
        "options": {"queue": "maintenance"},
    },
    # Summarization - Sunday batch
    "batch-summarize": {
        "task": "app.tasks.summarize.batch_summarize_pending",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
        "options": {"queue": "summarization"},
    },
    # Embeddings - Sunday batch (after summarization)
    "batch-embeddings": {
        "task": "app.tasks.embeddings.batch_generate_embeddings",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
        "options": {"queue": "summarization"},
    },
    # Theme matching - Saturday (after weekly ingestion)
    "match-themes-weekly": {
        "task": "app.tasks.theme_matcher.match_all_themes",
        "schedule": crontab(hour=8, minute=0, day_of_week=6),
        "options": {"queue": "maintenance"},
    },
    # Expiry watch - Daily
    "expiry-watch-daily": {
        "task": "app.tasks.expiry_watch.update_expiry_flags",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "maintenance"},
    },
}
