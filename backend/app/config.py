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
    recovery_forgot_ip_limit: int = 5
    recovery_forgot_ip_window_seconds: int = 3600
    recovery_forgot_email_limit: int = 3
    recovery_forgot_email_window_seconds: int = 3600
    recovery_reset_ip_limit: int = 15
    recovery_reset_ip_window_seconds: int = 3600
    recovery_reset_token_fail_limit: int = 5
    recovery_reset_token_fail_window_seconds: int = 900
    recovery_mfa_ip_limit: int = 10
    recovery_mfa_ip_window_seconds: int = 300
    csp_enabled: bool = True
    csp_report_uri: str = ""
    audit_immutable: bool = True
    audit_retention_days: int = 2555
    backup_enabled: bool = True
    backup_directory: str = "data/backups"
    backup_retention_days: int = 30
    backup_schedule_hour: int = 1
    shutdown_grace_seconds: int = 30
    circuit_breakers_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_seconds: float = 30.0
    request_timeout_enabled: bool = True
    request_timeout_seconds: float = 60.0
    request_timeout_agent_seconds: float = 120.0
    request_timeout_export_seconds: float = 300.0
    outbound_http_timeout_seconds: float = 30.0
    outbound_http_timeout_short_seconds: float = 15.0
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: float = 30.0
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True
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
    opensearch_bulk_size: int = 500
    opensearch_retention_days: int = 0
    oidc_enabled: bool = False
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_auto_provision: bool = False
    oidc_default_role: str = "analyst"
    oidc_provider_label: str = "SSO"
    oidc_scopes: str = "openid email profile"
    oidc_groups_claim: str = "groups"
    oidc_role_map: str = ""
    oidc_sync_roles_on_login: bool = True
    oidc_allowed_email_domains: str = ""
    ai_assistant_enabled: bool = True
    ai_provider: str = "local"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ueba_enabled: bool = True
    ueba_z_threshold: float = 2.5
    ueba_min_observed: int = 5
    ueba_baseline_days: int = 7
    ueba_min_baseline_samples: int = 3
    ueba_window_hours: int = 24
    ueba_create_alerts: bool = True
    ueba_scan_interval_minutes: int = 60
    demo_mode: bool = False

    @model_validator(mode="after")
    def apply_testing_env(self) -> "Settings":
        import os
        if os.environ.get("TESTING", "").lower() in ("1", "true", "yes"):
            self.testing = True
            self.debug = False
            self.backup_enabled = False
            self.db_pool_size = 5
            self.db_max_overflow = 5
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
