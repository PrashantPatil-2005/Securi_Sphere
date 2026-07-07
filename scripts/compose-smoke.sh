#!/usr/bin/env bash
# Bring up CI compose stack and verify API health endpoints.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE="docker compose"
if ! $COMPOSE version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-smokepass}"
export JWT_SECRET="${JWT_SECRET:-ci-smoke-test-secret-key-minimum-length}"

cleanup() {
  $COMPOSE -f docker-compose.ci.yml down -v --remove-orphans 2>/dev/null || true
}
trap cleanup EXIT

echo "==> Starting compose CI smoke stack"
$COMPOSE -f docker-compose.ci.yml up -d --build --wait

echo "==> Checking liveness"
curl -sf http://localhost:8000/health/live | grep -q '"status"'

echo "==> Checking readiness"
curl -sf http://localhost:8000/health/ready | grep -q '"status"'

echo "==> Checking public settings"
curl -sf http://localhost:8000/api/v1/settings/public | grep -q '"environment"'

echo "Compose smoke test passed."
