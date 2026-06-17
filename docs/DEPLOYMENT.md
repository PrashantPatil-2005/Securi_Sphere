# Deployment Guide

## Phase 1: Local Development

See README.md. Copy .env.example to .env and set secrets locally.

## Phase 2: LAN Deployment

1. Set SERVER_URL and FRONTEND_URL in backend .env to your LAN IP
2. Run backend: uvicorn app.main:app --host 0.0.0.0 --port 8000
3. Allow firewall ports 8000 and 3000

## Phase 3: Internet Deployment (HTTPS)

Use Caddy or nginx as reverse proxy. Update URLs to HTTPS.

## Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string (set in local .env only) |
| JWT_SECRET | Secret for JWT signing (required) |
| POSTGRES_PASSWORD | Postgres password for docker-compose |
| MAIL_* | Optional email alerts (MAIL_HOST, MAIL_USER, MAIL_PASSWORD) |
| TELEGRAM_BOT_TOKEN | Optional Telegram alerts |
