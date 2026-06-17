from pathlib import Path

root = Path(__file__).resolve().parents[1]

(root / "docker-compose.yml").write_text(
    """services:
  postgres:
    image: postgres:16-alpine
    container_name: securi-postgres
    env_file:
      - .env
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-securi}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
      POSTGRES_DB: ${POSTGRES_DB:-securi}
    ports:
      - "5432:5432"
    volumes:
      - securi_pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U securi -d securi"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  securi_pg_data:
""",
    encoding="utf-8",
)

(root / ".env.example").write_text(
    """# Copy to .env and set your own values. Never commit .env.

POSTGRES_USER=securi
POSTGRES_PASSWORD=REPLACE_WITH_A_STRONG_LOCAL_PASSWORD
POSTGRES_DB=securi
DATABASE_URL=postgresql+asyncpg://securi:REPLACE_WITH_A_STRONG_LOCAL_PASSWORD@localhost:5432/securi

JWT_SECRET=REPLACE_WITH_A_LONG_RANDOM_SECRET
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

SERVER_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@securi.local

TELEGRAM_BOT_TOKEN=

DEBUG=true
ENVIRONMENT=development
""",
    encoding="utf-8",
)

print("Updated docker-compose.yml and .env.example")
