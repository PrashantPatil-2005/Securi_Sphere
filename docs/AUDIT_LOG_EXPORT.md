# Audit log export

Admins can download audit trail entries for compliance reviews and offline analysis.

## API

`GET /api/v1/audit/export` — **admin only**

| Query | Description |
|-------|-------------|
| `format` | `csv` (default), `json`, or `pdf` |
| `action` | Filter by action name |
| `from` | ISO timestamp lower bound |
| `to` | ISO timestamp upper bound |
| `limit` | Max rows (default 5000, max 10000) |

Each export writes a meta-audit entry (`audit_export`) with format, row count, and active filters.

## UI

The **Audit Log** page header includes CSV / JSON / PDF buttons. Exports honor the current action filter.

## Verify

1. Sign in as admin → **Audit Log**
2. Click **csv** — file downloads with headers `id,user_id,action,...`
3. Check newest audit row is `audit_export` with `details.format`

## RBAC

Viewers and analysts receive `403` on `/audit/export`.
