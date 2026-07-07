#!/usr/bin/env bash
# Verify PostgreSQL is configured for WAL archiving (self-hosted PITR).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CONTAINER="${PITR_PG_CONTAINER:-securi-postgres}"
DB_USER="${POSTGRES_USER:-securi}"

echo "Checking PITR prerequisites on ${CONTAINER}..."

docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -Atqc "SHOW wal_level;"
docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -Atqc "SHOW archive_mode;"
docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -Atqc "SHOW archive_command;"

WAL_COUNT="$(docker exec "$CONTAINER" sh -c 'ls -1 /var/lib/postgresql/wal_archive 2>/dev/null | wc -l' || echo 0)"
echo "WAL segments in archive: ${WAL_COUNT}"

if docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -Atqc "SELECT setting FROM pg_settings WHERE name = 'archive_mode';" | grep -qx on; then
  echo "OK: archive_mode=on"
else
  echo "WARN: archive_mode is off — apply docker-compose.pitr.yml or managed PITR"
  exit 1
fi
