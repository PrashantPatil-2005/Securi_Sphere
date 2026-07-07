#!/usr/bin/env bash
# Create a compressed base backup for point-in-time recovery (requires archive_mode=on).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

CONTAINER="${PITR_PG_CONTAINER:-securi-postgres}"
DB_USER="${POSTGRES_USER:-securi}"
OUT_DIR="${PITR_BASE_DIRECTORY:-data/pitr/base}"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
ARCHIVE="${OUT_DIR}/base_${STAMP}.tar.gz"

mkdir -p "$OUT_DIR"

echo "Creating base backup from ${CONTAINER} -> ${ARCHIVE}"
docker exec "$CONTAINER" pg_basebackup -U "$DB_USER" -D - -Ft -z -P -X fetch > "$ARCHIVE"

SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
SIZE="$(stat -c%s "$ARCHIVE")"
cat > "${ARCHIVE%.tar.gz}.manifest.json" <<EOF
{
  "filename": "$(basename "$ARCHIVE")",
  "size_bytes": $SIZE,
  "sha256": "$SHA256",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "type": "pg_basebackup",
  "note": "Pair with WAL archive for PITR — not interchangeable with pg_dump SQL backups"
}
EOF

echo "Base backup complete (${SIZE} bytes)"
