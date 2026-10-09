from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CAREERPILOT_",
        extra="ignore",
    )

    app_name: str = "CareerPilot API"
    app_version: str = "0.1.0"
    environment: str = "local"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://careerpilot:careerpilot@localhost:5432/careerpilot"
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: str = "http://localhost:3000"

    jwt_secret_key: str = "dev-insecure-secret-change-me-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    # Fernet master key wrapping each user's data key (dev default; override in prod).
    master_key: str = "E4vHUnDMy5_jzV639cZBKAJuCoxLLH1XVMjKS8wfC1s="

    # S3-compatible object storage (adobe/s3mock locally).
    s3_endpoint_url: str = "http://localhost:9090"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "careerpilot"
    s3_region: str = "us-east-1"

    max_upload_mb: int = 10

    # Outbound fetch (user-URL job ingestion).
    user_agent: str = "CareerPilotBot/0.1 (+https://careerpilot.local)"
    fetch_timeout_seconds: float = 15.0
    robots_cache_ttl_seconds: int = 3600
    enable_user_url_ingestion: bool = True
    # Greenhouse/Lever/Ashby public-API adapters, selected from the pasted URL.
    enable_ats_ingestion: bool = True

    # Leads & discovery (RSS/Atom + Google Programmable Search).
    enable_rss_discovery: bool = True
    enable_google_pse: bool = False
    google_pse_api_key: str | None = None
    google_pse_cx: str | None = None
    google_pse_daily_quota: int = 100
    google_pse_cache_seconds: int = 86400
    lead_discovery_interval_minutes: int = 360
    lead_discovery_batch_size: int = 100

    # Job lifecycle re-checks (Celery beat).
    job_recheck_hours: int = 24
    job_recheck_interval_minutes: int = 60
    recheck_batch_size: int = 100
    celery_task_always_eager: bool = False

    # Scheduled alerts (Celery beat).
    alert_run_interval_minutes: int = 15
    alerts_batch_size: int = 100

    # Analytics: minimum segment size before a rate is reported (below it, value is null).
    analytics_min_sample: int = 5

    # Insights: daily-plan / skill-gap thresholds.
    strong_match_threshold: float = 8.0
    daily_plan_follow_up_days: int = 7
    daily_plan_max_items: int = 12

    # Email notifications. Default provider only logs — nothing leaves the box unless SMTP is set.
    email_provider: str = "console"
    email_enabled: bool = True
    email_from: str = "no-reply@careerpilot.local"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_timeout_seconds: float = 15.0

    # Email/calendar integration. Gmail inbox stays off until read-only OAuth is implemented.
    gmail_enabled: bool = False

    llm_provider: str = "openai"
    llm_default_model: str = "gpt-4o-mini"
    llm_cheap_model: str = "gpt-4o-mini"
    llm_strong_model: str = "gpt-4o"
    llm_request_timeout_seconds: float = 30.0
    llm_max_retries: int = 3
    openai_api_key: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
