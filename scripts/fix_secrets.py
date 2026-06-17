from pathlib import Path

root = Path(__file__).resolve().parents[1]

(root / "backend" / "app" / "config.py").write_text(
    """from pydantic import model_validator
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
""",
    encoding="utf-8",
)

(root / ".env.example").write_text(
    """# Copy to .env and fill in values locally. Never commit .env.

POSTGRES_USER=securi
POSTGRES_DB=securi
# Generate a strong password and set it here:
POSTGRES_PASSWORD=

# Build DATABASE_URL from the values above, e.g.:
# postgresql+asyncpg://USER:PASSWORD@localhost:5432/DBNAME
DATABASE_URL=

# Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
JWT_SECRET=

JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

SERVER_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Optional email alerts - see docs/DEPLOYMENT.md
MAIL_HOST=
MAIL_PORT=587
MAIL_USER=
MAIL_PASSWORD=
MAIL_FROM=noreply@securi.local

TELEGRAM_BOT_TOKEN=

DEBUG=true
ENVIRONMENT=development
""",
    encoding="utf-8",
)

print("Updated config.py and .env.example")
