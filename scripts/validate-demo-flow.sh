#!/usr/bin/env bash
# Validate UI flow + demo path (requires Postgres, backend :8000, frontend :3000).
# Usage: ./scripts/validate-demo-flow.sh [API_BASE] [FRONTEND_BASE]
set -euo pipefail

API="${1:-http://localhost:8000}"
FRONTEND="${2:-http://localhost:3000}"
SKIP_E2E="${SKIP_E2E:-0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

printf 'NEXT_PUBLIC_API_URL=%s\n' "$API" >"$ROOT/frontend/.env.local"

check() {
  local url="$1" label="$2"
  if curl -sf --max-time 5 "$url" >/dev/null; then
    echo "OK  $label"
    return 0
  fi
  echo "FAIL $label"
  return 1
}

echo "=== Securi demo flow validation ==="

if ! check "$API/health" "Backend health" || ! check "$FRONTEND/login" "Frontend login page"; then
  echo ""
  echo "Start the stack first:"
  echo "  docker compose -f docker-compose.dev.yml up -d"
  echo "  cd backend && uvicorn app.main:app --reload --port 8000"
  echo "  cd frontend && npx next dev --turbo -p 3000"
  exit 1
fi

echo ""
echo "Running demo-setup..."
"$ROOT/scripts/demo-setup.sh" "$API"

echo ""
echo "Public settings:"
curl -sf "$API/api/v1/settings/public" | python -m json.tool

echo ""
echo "Typecheck frontend..."
(cd "$ROOT/frontend" && npx tsc --noEmit)

if [[ "$SKIP_E2E" != "1" ]]; then
  echo ""
  echo "Playwright smoke + lab flow (E2E_FULL_STACK=1)..."
  (
    cd "$ROOT/frontend"
    export E2E_FULL_STACK=1
    export PLAYWRIGHT_BASE_URL="$FRONTEND"
    npx playwright test e2e/smoke.spec.ts e2e/lab-flow.spec.ts --workers=1
  )
fi

echo ""
echo "=== Validation passed ==="
echo "Manual walkthrough: docs/GUIDE_DEMO.md"
echo "Login: demo@securi.local / Demo1234!"
