# Immutable audit store

Audit logs are append-only with a SHA-256 hash chain for tamper detection.

## Design

Each `audit_logs` row includes:

| Column | Purpose |
|--------|---------|
| `chain_seq` | Monotonic sequence (PostgreSQL sequence) |
| `prev_hash` | Previous entry hash (genesis uses 64 zeros) |
| `entry_hash` | SHA-256 of canonical JSON payload + `prev_hash` |

PostgreSQL blocks `UPDATE` and `DELETE` on `audit_logs` via trigger `audit_logs_immutable`.

Retention skips audit rows when `AUDIT_IMMUTABLE=true` (default).

## API

`GET /api/v1/audit/integrity` — **admin only**

| Query | Description |
|-------|-------------|
| `limit` | Max entries to verify (default 10000) |
| `from_seq` | Start verification at this `chain_seq` |

Response includes `valid`, `entries_checked`, `chain_head_hash`, and failure details when tampered.

## Configuration

```env
AUDIT_IMMUTABLE=true
AUDIT_RETENTION_DAYS=2555
```

Set `AUDIT_IMMUTABLE=false` only in dev if you need retention purges.

## Migration

```powershell
cd backend; python -m alembic upgrade head
```

Migration `015_immutable_audit` backfills `chain_seq` and hashes for existing rows.

## Verify

1. Admin → **Audit Log** — green “Audit chain verified” banner
2. `GET /api/v1/audit/integrity` returns `"valid": true`
3. Direct `UPDATE audit_logs` in psql raises `audit_logs are immutable`
