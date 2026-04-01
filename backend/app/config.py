from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://patent:secret@db:5432/patent_pulse"
    database_url_sync: str = "postgresql+psycopg2://patent:secret@db:5432/patent_pulse"
    redis_url: str = "redis://redis:6379/0"

    anthropic_api_key: str = ""
    uspto_api_key: str = ""
    google_cloud_project: str | None = None

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    claude_model: str = "claude-sonnet-4-6"
    summarization_batch_size: int = 10
    max_summary_retries: int = 3
    ingest_lookback_days: int = 7
    bigquery_backfill_years: int = 5

    epo_ops_client_id: str | None = None
    epo_ops_client_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
