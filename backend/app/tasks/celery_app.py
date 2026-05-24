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
        "app.tasks.enrich_abstracts",
        "app.tasks.theme_matcher",
        "app.tasks.expiry_watch",
        "app.tasks.tag",
        "app.tasks.opportunity",
        "app.tasks.why_now",
        "app.tasks.opportunity_narrative",
        "app.tasks.trend_snapshot",
        "app.tasks.assignee_intelligence",
        "app.tasks.compute_trends",
        "app.tasks.compute_cliffs",
        "app.tasks.compute_convergence",
        "app.tasks.backfill_usage_signals",
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
        "app.tasks.enrich_abstracts.*": {"queue": "ingestion"},
        "app.tasks.expiry_watch.*": {"queue": "maintenance"},
        # Phase 1 AI tasks share the summarization queue (LLM-bound or fast rules)
        "app.tasks.tag.*": {"queue": "summarization"},
        "app.tasks.opportunity.*": {"queue": "summarization"},
        # Phase 2 Narrative tasks share the summarization queue
        "app.tasks.why_now.*": {"queue": "summarization"},
        "app.tasks.opportunity_narrative.*": {"queue": "summarization"},
        "app.tasks.trend_snapshot.*": {"queue": "summarization"},
        "app.tasks.assignee_intelligence.*": {"queue": "summarization"},
        "app.tasks.compute_trends.*": {"queue": "maintenance"},
        "app.tasks.compute_cliffs.*": {"queue": "maintenance"},
        "app.tasks.compute_convergence.*": {"queue": "maintenance"},
        "app.tasks.backfill_usage_signals.*": {"queue": "maintenance"},
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
    # Abstract enrichment - Saturday (after weekly ingestion, before summarization)
    "enrich-abstracts-weekly": {
        "task": "app.tasks.enrich_abstracts.enrich_batch",
        "schedule": crontab(hour=20, minute=0, day_of_week=6),
        "kwargs": {"batch_size": 200},
        "options": {"queue": "ingestion"},
    },
    # Summarization - Sunday batch
    "batch-summarize": {
        "task": "app.tasks.summarize.batch_summarize_pending",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
        "options": {"queue": "summarization"},
    },
    # Re-summarize enriched patents - Sunday (after new summaries)
    "resummarize-enriched": {
        "task": "app.tasks.summarize.batch_resummarize_enriched",
        "schedule": crontab(hour=5, minute=0, day_of_week=0),
        "kwargs": {"limit": 50},
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
    # Trend snapshots - Sunday (after embeddings, before next week)
    "compute-weekly-trends": {
        "task": "app.tasks.compute_trends.compute_weekly_trends",
        "schedule": crontab(hour=7, minute=0, day_of_week=0),
        "options": {"queue": "maintenance"},
    },
    # Cliff clusters - Sunday (after trends)
    "compute-cliff-clusters": {
        "task": "app.tasks.compute_cliffs.compute_cliff_clusters",
        "schedule": crontab(hour=7, minute=30, day_of_week=0),
        "options": {"queue": "maintenance"},
    },
    # Convergence signals - Sunday (after cliffs)
    "compute-convergence-signals": {
        "task": "app.tasks.compute_convergence.compute_convergence_signals",
        "schedule": crontab(hour=8, minute=0, day_of_week=0),
        "options": {"queue": "maintenance"},
    },
    # Sprint 5 — embedding backfill (every 15 min, 200/batch).
    "embeddings-backfill": {
        "task": "app.tasks.embeddings.batch_generate_embeddings",
        "schedule": crontab(minute="*/2"),
        "args": (1000,),
        "options": {"queue": "maintenance"},
    },
    # Sprint 5 follow-up (O2) — embed the expiring-patent cohort so usage
    # signals become visible on the Expiry Radar. Newest-first ordering on
    # the main backfill leaves these patents perpetually unembedded.
    # Runs every 10 min on the :05 mark with limit=200, prioritized by
    # soonest expiry.
    "embeddings-backfill-expiring": {
        "task": "app.tasks.embeddings.batch_generate_embeddings",
        "schedule": crontab(minute="5,15,25,35,45,55"),
        "kwargs": {"limit": 200, "prioritize_expiring": True},
        "options": {"queue": "maintenance"},
    },
    # Sprint 5 — usage signals backfill (hourly, 200/batch).
    # Idempotent: skips signal rows refreshed within STALENESS_DAYS (7).
    # The signal collectors depend on embeddings, so this runs after the
    # embedding backfill has had time to populate.
    "usage-signals-backfill": {
        "task": "app.tasks.backfill_usage_signals.batch_backfill_usage_signals",
        "schedule": crontab(minute=15),
        "kwargs": {"limit": 200, "offset": 0},
        "options": {"queue": "maintenance"},
    },
    # Post-Sprint-5 audit (A5) — Phase 1/2/4 batch tasks that were written
    # but never scheduled. Currently >99% of the 54K-patent corpus has
    # tags=[], opportunity_score=NULL, why_now_text=NULL despite the task
    # code existing. Adding modest hourly schedules so the gap closes
    # gradually without flooding the LLM budget.
    "batch-tag-patents": {
        "task": "app.tasks.tag.batch_tag_patents",
        "schedule": crontab(minute=20),  # hourly, offset from usage-signals
        "kwargs": {"limit": 100},
        "options": {"queue": "summarization"},
    },
    "batch-score-opportunity": {
        "task": "app.tasks.opportunity.batch_score_opportunity",
        # Deterministic compute (no LLM cost) — run every 15 min, larger batch.
        "schedule": crontab(minute="*/15"),
        "kwargs": {"limit": 500},
        "options": {"queue": "summarization"},
    },
    "batch-why-now": {
        "task": "app.tasks.why_now.batch_why_now",
        # Sonnet-tier LLM (per A3) — modest cadence.
        "schedule": crontab(minute=25),
        "kwargs": {"limit": 50},
        "options": {"queue": "summarization"},
    },
    "batch-opportunity-narrative": {
        "task": "app.tasks.opportunity_narrative.batch_opportunity_narrative",
        # Sonnet-tier LLM (per A3) — modest cadence.
        "schedule": crontab(minute=35),
        "kwargs": {"limit": 50},
        "options": {"queue": "summarization"},
    },
}
