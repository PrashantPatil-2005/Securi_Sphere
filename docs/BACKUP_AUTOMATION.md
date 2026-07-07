# Backup automation

Automated PostgreSQL backups via `pg_dump`, gzip compression, SHA-256 manifests, and retention pruning.

## Built-in scheduler

When `BACKUP_ENABLED=true` (default), the API runs a daily backup at `BACKUP_SCHEDULE_HOUR` UTC (default `1`).

| Env | Default | Description |
|-----|---------|-------------|
| `BACKUP_ENABLED` | `true` | Enable scheduled + manual backups |
| `BACKUP_DIRECTORY` | `data/backups` | Output directory (use a mounted volume in prod) |
| `BACKUP_RETENTION_DAYS` | `30` | Delete archives older than this |
| `BACKUP_SCHEDULE_HOUR` | `1` | Hour (0–23) for daily cron job |

Production Compose (`docker-compose.prod.yml`) mounts `securi_backups` at `/var/backups/securi`.

## API (admin)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/backups` | List recent backups + config |
| `POST` | `/api/v1/backups/run` | Trigger manual backup |

Manual runs write an audit entry (`backup_triggered`).

## UI

**System Health** → **Database backups** panel — recent files, **Run backup now**.

## Host cron (alternative)

If the API container cannot reach Postgres, use the host script against the Docker Postgres container:

```bash
# Linux — daily at 02:15 UTC
15 2 * * * /opt/securi/scripts/backup-postgres.sh >> /var/log/securi-backup.log 2>&1
```

```powershell
# Windows Task Scheduler
powershell -File C:\Securi\scripts\backup-postgres.ps1
```

## Output format

Each run creates:

- `securi_pg_YYYYMMDD_HHMMSS.sql.gz` — plain SQL dump (gzip)
- `securi_pg_YYYYMMDD_HHMMSS.manifest.json` — size, SHA-256, trigger, timestamp

## Restore

**Empty database** (destructive — test in staging first):

```bash
gunzip -c data/backups/securi_pg_20260707_010000.sql.gz \
  | docker exec -i securi-postgres psql -U securi -d securi
```

Or from inside Postgres container:

```bash
gunzip -c /backups/securi_pg_20260707_010000.sql.gz | psql -U securi -d securi
```

Stop the backend during restore to avoid concurrent writes.

## Encryption

Backup files contain full database contents. Store on **encrypted volumes** and restrict filesystem permissions. See `docs/DB_ENCRYPTION_AT_REST.md`.

For off-site copies:

```bash
gpg --symmetric --cipher-algo AES256 securi_pg_20260707_010000.sql.gz
```

## Verify

1. Admin → **System Health** → **Run backup now**
2. `GET /api/v1/backups` lists the new archive with `sha256`
3. Confirm file exists in `BACKUP_DIRECTORY`
4. Optional: `sha256sum` matches manifest

## Managed Postgres (RDS / Cloud SQL)

Use provider snapshots and **point-in-time restore** as primary DR for production. See `docs/PITR_RUNBOOK.md`.

Application `pg_dump` backups remain useful for portable restores and compliance exports. Combine both.

## Related

- `docs/DB_ENCRYPTION_AT_REST.md` — encrypt backup storage
- `docs/VPS_DEPLOY.md` — manual pg_dump examples
- PITR runbook — see `docs/PITR_RUNBOOK.md`
