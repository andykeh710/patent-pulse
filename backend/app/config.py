from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://patent:secret@db:5432/patent_pulse"
    database_url_sync: str = "postgresql+psycopg2://patent:secret@db:5432/patent_pulse"
    redis_url: str = "redis://redis:6379/0"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    uspto_api_key: str = ""
    uspto_odp_api_key: str = ""
    uspto_odp_base_url: str = "https://api.uspto.gov/api/v1"
    google_cloud_project: str | None = None

    # Sprint 6: magic-link auth
    auth_secret_key: str = ""
    magic_link_ttl_minutes: int = 15
    magic_link_base_url: str = "http://localhost:3000"

    # Security: comma-separated allowlist of email addresses that are granted
    # admin. Used by migration 0035 to preserve known admins when flipping the
    # is_admin default to false, and by the auth flow to (re)grant admin to
    # these accounts on sign-in. Everyone else is a normal (non-admin) user.
    admin_emails: str = ""

    # Sprint 6: email
    resend_api_key: str = ""
    email_from_address: str = ""
    email_dev_recipient: str = ""
    email_send_mode: str = "dev"  # "dev" | "dry_run" | "production"
    email_production_acknowledged: str | None = None

    # Sprint 6.5: feature-flag USPTO citation ingestion (1 extra API call/patent).
    uspto_fetch_citations: bool = False

    # Sprint 7 / Phase 4: Stripe billing
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_basic: str = ""
    stripe_price_id_lifetime: str = ""
    stripe_price_id_enterprise: str = ""

    # Stripe mode enforcement (Phase 4 PR 1 — SAFETY GATE).
    #   stripe_mode: "test" | "live"  — which Stripe keys are in use
    #   stripe_live_acknowledged: must be "true" before stripe_mode=live will start
    stripe_mode: str = "test"
    stripe_live_acknowledged: str | None = None

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # PR8: Sentry error tracking (silently noops when DSN is unset)
    sentry_dsn: str = ""
    release_sha: str = ""  # populated by CI; stays empty for local dev

    claude_model: str = "claude-sonnet-4-20250514"
    claude_haiku_model: str = "claude-haiku-4-5"
    summarization_batch_size: int = 10
    max_summary_retries: int = 3
    ingest_lookback_days: int = 7
    bigquery_backfill_years: int = 5

    epo_ops_client_id: str | None = None
    epo_ops_client_secret: str | None = None

    # ScrapeGraphAI fallback provider for WIPO + image extraction
    scrapegraph_api_key: str = ""
    scrapegraph_enabled: bool = False
    scrapegraph_max_credits_per_run: int = 100
    scrapegraph_max_pages_per_run: int = 10

    # WIPO BigQuery via Google Patents public dataset
    wipo_bigquery_dataset: str = "patents-public-data"

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

    # DeepSeek — primary AI provider (all text generation)
    deepseek_api_key: str = ""
    deepseek_chat_model: str = "deepseek-v4-pro"
    deepseek_reasoner_model: str = "deepseek-v4-pro"
    deepseek_input_usd_per_mtok: float = 0.27
    deepseek_output_usd_per_mtok: float = 1.10

    # LLM provider: "deepseek" (primary) | "anthropic" (compatibility only)
    llm_provider: str = "deepseek"

    # Anthropic SDK compatibility path (routes to DeepSeek when base_url set)
    anthropic_base_url: str = "https://api.deepseek.com/anthropic"

    # Phase 3: Chatbot config — DeepSeek via Anthropic-compatible endpoint
    chat_model: str = "deepseek-v4-pro"
    chat_retrieve_k: int = 8
    chat_quota_free: int = 50
    chat_quota_basic: int = 100

    # V3.8I: patent figure storage + rate limiting
    figures_storage_dir: str = "/data/figures"
    figures_serve_url_prefix: str = "/api/v1/patents"
    epo_ops_max_rps: float = 2.0  # free tier: ~2 requests/second
    uspto_odp_max_rps: float = 5.0
    figure_retry_max_attempts: int = 3
    figure_retry_backoff_base: float = 5.0  # seconds
    google_patents_images_enabled: bool = False  # feature flag: ToS gray area

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
