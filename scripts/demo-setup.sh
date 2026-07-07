#!/usr/bin/env bash
# Prepare a live demo: admin user, demo host, optional attack simulation.
# Usage: ./scripts/demo-setup.sh [API_BASE_URL]
set -euo pipefail

API="${1:-http://localhost:8000}"
EMAIL="${DEMO_EMAIL:-demo@securi.local}"
PASSWORD="${DEMO_PASSWORD:-Demo1234!}"
HOST_NAME="${DEMO_HOST_NAME:-demo-server}"

echo "Securi demo setup → $API"

register() {
  curl -sf -X POST "$API/api/v1/auth/register" \
    -H "Content-Type: application/json" \
    -c /tmp/securi-demo-cookies.txt \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"full_name\":\"Demo Admin\"}" \
    && echo "Registered $EMAIL" || echo "User may already exist — trying login..."
}

login() {
  curl -sf -X POST "$API/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -c /tmp/securi-demo-cookies.txt \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" >/dev/null
  echo "Logged in as $EMAIL"
}

create_host() {
  HOST_ID=$(curl -sf -X POST "$API/api/v1/hosts" \
    -H "Content-Type: application/json" \
    -b /tmp/securi-demo-cookies.txt \
    -d "{\"name\":\"$HOST_NAME\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  echo "Created host: $HOST_NAME ($HOST_ID)"
  echo "$HOST_ID"
}

run_simulation() {
  local host_id="$1"
  curl -sf -X POST "$API/api/v1/simulation/run/multi_stage_attack?host_id=$host_id" \
    -b /tmp/securi-demo-cookies.txt >/dev/null
  echo "Ran multi_stage_attack simulation on $HOST_NAME"
}

register || true
login
HOST_ID="$(create_host)"

if [[ "${RUN_SIMULATION:-true}" == "true" ]]; then
  run_simulation "$HOST_ID"
fi

echo ""
echo "=== Demo ready ==="
echo "  Dashboard: set FRONTEND_URL from .env (default http://localhost:3000)"
echo "  Email:    $EMAIL"
echo "  Password: $PASSWORD"
echo ""
echo "For dashboard charts to include simulated events during the demo, set:"
echo "  EXCLUDE_SIMULATED_FROM_DASHBOARD=false"
echo "Then restart the backend. After the demo, use Simulation → Purge simulated data."
