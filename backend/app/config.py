from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_private_key_path: str = ""
    jwt_public_key_path: str = ""
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    server_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    mail_host: str = ""
    mail_port: int = 587
    mail_user: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@securi.local"
    telegram_bot_token: str = ""
    debug: bool = True
    sql_echo: bool = False
    environment: str = "development"
    retention_days: int = 90
    async_event_pipeline: bool = True
    cross_host_correlation_interval_seconds: int = 60
    agent_request_signing: bool = False
    account_lockout_attempts: int = 5
    account_lockout_minutes: int = 15
    idempotency_ttl_seconds: int = 86400
    allow_registration: bool = True
    enable_simulation: bool = True
    exclude_simulated_from_dashboard: bool = True
    redis_url: str = ""
    job_queue_backend: str = "memory"
    job_queue_workers: int = 2
    job_queue_run_workers: bool = True
    ws_pubsub_backend: str = "memory"
    event_partitioning_enabled: bool = False
    virustotal_api_key: str = ""
    agent_mtls_enabled: bool = False
    agent_mtls_ca_cert_path: str = ""
    trusted_proxy: bool = False
    testing: bool = False
    opensearch_url: str = ""
    search_backend: str = "postgres"
    ai_assistant_enabled: bool = True
    ai_provider: str = "local"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    @model_validator(mode="after")
    def apply_testing_env(self) -> "Settings":
        import os
        if os.environ.get("TESTING", "").lower() in ("1", "true", "yes"):
            self.testing = True
            self.debug = False
        return self

    @model_validator(mode="after")
    def require_secrets(self) -> "Settings":
        if not self.database_url:
            raise ValueError("DATABASE_URL must be set in .env")
        if self.jwt_algorithm.upper() == "HS256" and not self.jwt_secret:
            raise ValueError("JWT_SECRET must be set in .env for HS256")
        if self.jwt_algorithm.upper() == "RS256" and (
            not self.jwt_private_key_path or not self.jwt_public_key_path
        ):
            raise ValueError("JWT key paths required for RS256")
        return self

    @property
    def smtp_host(self) -> str:
        return self.mail_host

    @property
    def smtp_port(self) -> int:
        return self.mail_port

    @property
    def smtp_user(self) -> str:
        return self.mail_user

    @property
    def smtp_password(self) -> str:
        return self.mail_password

    @property
    def smtp_from(self) -> str:
        return self.mail_from


settings = Settings()
