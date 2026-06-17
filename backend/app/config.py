from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://securi:securi_dev@localhost:5432/securi"
    jwt_secret: str = "change-me-to-a-long-random-secret-key"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    server_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@securi.local"
    telegram_bot_token: str = ""
    debug: bool = True
    environment: str = "development"
    retention_days: int = 90


settings = Settings()
