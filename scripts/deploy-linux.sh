#!/usr/bin/env bash
# Securi — one-command Linux deployment with Docker Compose.
# Usage: ./scripts/deploy-linux.sh [SERVER_IP_OR_DOMAIN]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST="${1:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
if [[ -z "$HOST" ]]; then
  echo "Could not detect server IP. Pass it as the first argument."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install: https://docs.docker.com/engine/install/"
  exit 1
fi

COMPOSE="docker compose"
if ! $COMPOSE version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  JWT_SECRET="$(openssl rand -hex 32)"
  PG_PASS="$(openssl rand -hex 16)"
  {
    echo "POSTGRES_PASSWORD=$PG_PASS"
    echo "JWT_SECRET=$JWT_SECRET"
    echo "DATABASE_URL=postgresql+asyncpg://securi:${PG_PASS}@postgres:5432/securi"
    echo "SERVER_URL=http://${HOST}:8000"
    echo "FRONTEND_URL=http://${HOST}:3000"
    echo "ENVIRONMENT=production"
    echo "DEBUG=false"
    echo "ALLOW_REGISTRATION=true"
    echo "ENABLE_SIMULATION=true"
    echo "EXCLUDE_SIMULATED_FROM_DASHBOARD=true"
  } >> .env
  echo "Created .env with generated secrets."
else
  echo "Using existing .env"
fi

echo "Building and starting Securi on http://${HOST}:3000 (API :8000)..."
$COMPOSE -f docker-compose.yml -f docker-compose.prod.yml up -d --build

echo ""
echo "Securi is starting. Wait ~30s, then open:"
echo "  Dashboard: http://${HOST}:3000"
echo "  API docs:  http://${HOST}:8000/docs"
echo ""
echo "First login: register at /register (first user becomes admin)."
echo "Pilot demo: set DEMO_MODE=true in .env and restart, or run ./scripts/demo-setup.sh"
echo "For HTTPS with Caddy, see docs/DEPLOYMENT.md"
