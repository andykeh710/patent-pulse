"""Validation: every beat-scheduled task must be a registered Celery task.

Guards against the class of bug where a beat entry references a task name that
doesn't match the task's declared `name=` (e.g. patentsview/bigquery backfills
were namespaced under app.tasks.enrich_abstracts.*). Such entries silently fail
at runtime with "Received unregistered task of type ...".
"""

from app.tasks.celery_app import celery_app


def test_all_beat_tasks_are_registered():
    # The include= modules register lazily; force-import them like the worker.
    celery_app.loader.import_default_modules()
    registered = set(celery_app.tasks.keys())

    missing = {
        name: entry["task"]
        for name, entry in celery_app.conf.beat_schedule.items()
        if entry["task"] not in registered
    }

    assert not missing, "Beat schedule references unregistered tasks: " + ", ".join(
        f"{k} -> {v}" for k, v in sorted(missing.items())
    )
