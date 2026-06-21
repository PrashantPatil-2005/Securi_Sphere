from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = ""
    jwt_secret: str = ""
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
    environment: str = "development"
    retention_days: int = 90
    async_event_pipeline: bool = True
    agent_request_signing: bool = False
    account_lockout_attempts: int = 5
    account_lockout_minutes: int = 15
    idempotency_ttl_seconds: int = 86400
    allow_registration: bool = True
    enable_simulation: bool = True
    redis_url: str = ""
    trusted_proxy: bool = False
    testing: bool = False
    opensearch_url: str = ""
    search_backend: str = "postgres"

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
        if not self.jwt_secret:
            raise ValueError("JWT_SECRET must be set in .env")
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
