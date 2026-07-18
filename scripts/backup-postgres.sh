#!/usr/bin/env bash
# Daily PostgreSQL backup for Docker Compose deployments.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
    export "$key=$value"
  done < .env
fi

CONTAINER="${BACKUP_PG_CONTAINER:-securi-postgres}"
DB_USER="${POSTGRES_USER:-securi}"
DB_NAME="${POSTGRES_DB:-securi}"
BACKUP_DIR="${BACKUP_DIRECTORY:-./data/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
ARCHIVE="${BACKUP_DIR}/securi_pg_${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up ${DB_NAME} from ${CONTAINER} -> ${ARCHIVE}"
docker exec "$CONTAINER" pg_dump -U "$DB_USER" --no-owner --no-acl "$DB_NAME" | gzip > "$ARCHIVE"

SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
SIZE="$(stat -c%s "$ARCHIVE")"
cat > "${ARCHIVE%.sql.gz}.manifest.json" <<EOF
{
  "filename": "$(basename "$ARCHIVE")",
  "path": "$ARCHIVE",
  "size_bytes": $SIZE,
  "sha256": "$SHA256",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "trigger": "cron",
  "duration_seconds": 0,
  "database": "$DB_NAME",
  "status": "completed"
}
EOF

find "$BACKUP_DIR" -name 'securi_pg_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name 'securi_pg_*.manifest.json' -mtime +"$RETENTION_DAYS" -delete

echo "Backup complete (${SIZE} bytes)"
