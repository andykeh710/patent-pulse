from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://patent:secret@db:5432/patent_pulse"
    database_url_sync: str = "postgresql+psycopg2://patent:secret@db:5432/patent_pulse"
    redis_url: str = "redis://redis:6379/0"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    uspto_api_key: str = ""
    google_cloud_project: str | None = None

    # Sprint 6: magic-link auth
    auth_secret_key: str = ""
    magic_link_ttl_minutes: int = 15
    magic_link_base_url: str = "http://localhost:3000"

    # Sprint 6: email
    resend_api_key: str = ""
    email_from_address: str = ""
    email_dev_recipient: str = ""
    email_send_mode: str = "dev"  # "dev" | "production"

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    claude_model: str = "claude-sonnet-4-20250514"
    claude_haiku_model: str = "claude-haiku-4-5"
    summarization_batch_size: int = 10
    max_summary_retries: int = 3
    ingest_lookback_days: int = 7
    bigquery_backfill_years: int = 5

    epo_ops_client_id: str | None = None
    epo_ops_client_secret: str | None = None

    # Phase 0: single-user mode + AI cost controls
    single_user_mode: bool = True
    default_user_id: str = "local-user"
    default_user_display_name: str = "Local User"

    # LLM mode controls the llm_client wrapper behavior:
    #   live   -> always call the API (still writes to cache on success)
    #   record -> call API only on cache miss, write result to cache
    #   replay -> never call API; raise if cache miss
    llm_mode: Literal["live", "record", "replay"] = "record"

    # Soft auto-approval threshold: AIRun requests with est_cost_usd <=
    # this value can be confirmed with a single click in /admin/ai-runs.
    # Above this, the UI requires an explicit "Confirm run" action.
    llm_run_auto_approve_usd: float = 5.0

    # Hard upper bound; anything above requires typing RUN FULL BATCH.
    llm_run_full_batch_threshold_usd: float = 25.0

    # Per-model USD pricing per 1M tokens (input, output). Used for cost
    # estimation and accounting. Adjust when Anthropic updates prices.
    claude_sonnet_input_usd_per_mtok: float = 3.0
    claude_sonnet_output_usd_per_mtok: float = 15.0
    claude_haiku_input_usd_per_mtok: float = 0.8
    claude_haiku_output_usd_per_mtok: float = 4.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
