"""
Daily database backup task.

Runs at 03:00 UTC via Celery beat. Dumps the database, gzips,
and optionally uploads to S3-compatible storage.

Configuration via env vars:
  BACKUP_S3_ENDPOINT — S3-compatible endpoint (e.g. Hetzner Object Storage)
  BACKUP_S3_BUCKET — bucket name
  BACKUP_S3_ACCESS_KEY — access key
  BACKUP_S3_SECRET_KEY — secret key
  BACKUP_RETENTION_DAYS — keep last N dailies (default 30)
"""

from __future__ import annotations

import gzip
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
BACKUP_S3_ENDPOINT = os.getenv("BACKUP_S3_ENDPOINT", "")
BACKUP_S3_BUCKET = os.getenv("BACKUP_S3_BUCKET", "")
BACKUP_S3_ACCESS_KEY = os.getenv("BACKUP_S3_ACCESS_KEY", "")
BACKUP_S3_SECRET_KEY = os.getenv("BACKUP_S3_SECRET_KEY", "")


@celery_app.task(name="backup_database_daily")
def backup_database_daily() -> dict:
    """Dump database, gzip, optionally upload to S3."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
    filename = f"patent_pulse_{timestamp}.sql.gz"

    logger.info("Starting database backup to %s", filename)

    # Dump and gzip in one pass
    pg_password = os.getenv("POSTGRES_PASSWORD", "secret")
    db_host = os.getenv("DB_HOST", "db")

    with tempfile.NamedTemporaryFile(suffix=".sql.gz", delete=False) as tmp:
        dump = subprocess.run(
            [
                "pg_dump",
                "-h",
                db_host,
                "-U",
                "patent",
                "-d",
                "patent_pulse",
                "--no-owner",
                "--no-acl",
            ],
            capture_output=True,
            env={**os.environ, "PGPASSWORD": pg_password},
        )
        if dump.returncode != 0:
            logger.error("pg_dump failed: %s", dump.stderr.decode()[:500])
            return {"status": "failed", "error": dump.stderr.decode()[:500]}

        compressed = gzip.compress(dump.stdout)
        tmp.write(compressed)
        tmp.flush()

        size_mb = len(compressed) / (1024 * 1024)
        logger.info("Backup created: %s (%.1f MB)", filename, size_mb)

    # Upload to S3 if configured
    s3_url = None
    if BACKUP_S3_ENDPOINT and BACKUP_S3_BUCKET:
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                endpoint_url=BACKUP_S3_ENDPOINT,
                aws_access_key_id=BACKUP_S3_ACCESS_KEY,
                aws_secret_access_key=BACKUP_S3_SECRET_KEY,
            )
            s3.upload_file(tmp.name, BACKUP_S3_BUCKET, f"daily/{filename}")
            s3_url = f"{BACKUP_S3_ENDPOINT}/{BACKUP_S3_BUCKET}/daily/{filename}"
            logger.info("Uploaded to S3: %s", s3_url)
        except Exception as e:
            logger.error("S3 upload failed: %s", e)
            return {"status": "partial", "error": str(e), "local_file": tmp.name}

    # Cleanup old local backups
    _cleanup_old_backups()

    return {
        "status": "ok",
        "file": filename,
        "size_mb": round(size_mb, 1),
        "s3_url": s3_url,
    }


def _cleanup_old_backups() -> None:
    """Remove local backups older than BACKUP_RETENTION_DAYS."""
    backup_dir = "/tmp/backups"
    if not os.path.isdir(backup_dir):
        return
    cutoff = datetime.utcnow() - timedelta(days=BACKUP_RETENTION_DAYS)
    for fname in os.listdir(backup_dir):
        if not fname.startswith("patent_pulse_") or not fname.endswith(".sql.gz"):
            continue
        fpath = os.path.join(backup_dir, fname)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
                logger.info("Removed old backup: %s", fname)
        except OSError:
            pass
