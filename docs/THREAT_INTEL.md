# Threat Intel — Reference Sets & Building Blocks

QRadar-style watchlists and reusable SIEM query templates.

## Reference sets

Named lists of indicators by type: `ip`, `username`, `hostname`, `domain`, `hash`, `port`.

### Search usage

Use in SIEM search with `ref:` prefix:

```
source_ip:ref:bad_ips severity:high date:24h
username:ref:privileged_users
```

### Real-time detection

Enabled reference sets are checked on **every ingested event**. Matching values create a **Threat Intel Match** alert (severity: high). Field mapping by type:

| Set type | Event fields checked |
|----------|---------------------|
| ip | `source_ip` |
| username | `username` |
| hostname | host name / hostname |
| domain, hash, port | event metadata |

Matched sets are also stored in event `metadata.intel_matches` for investigation.

### Feed-backed sets

Reference sets can be created with `source_type=feed` to sync indicators from remote URLs (`txt`, `csv`, `json`).

- Manual sync: `POST /api/v1/reference-sets/{id}/sync-feed`
- Scheduled sync: APScheduler job (`THREAT_INTEL_FEEDS_ENABLED=true`)

Config:

```env
THREAT_INTEL_FEEDS_ENABLED=true
THREAT_INTEL_FEED_SYNC_MINUTES=60
```

Feed sync metadata is stored on each set (`feed_last_sync_at`, `feed_last_sync_status`, `feed_last_sync_error`).

## Building blocks

Saved SIEM queries analysts can run from **Threat Intel → Building blocks** or link to Search. Building blocks are **search templates only** — they do not create detection rules.

Demo data seeds on first startup (`bad_ips`, `privileged_users`, two sample blocks).

## UI

**Management → Threat Intel** (`/intel`)

- Reference sets tab — full CRUD: create, enable/disable, edit description, bulk-add/delete entries
- Building blocks tab — create, edit, enable/disable, delete, run in Search

## API

| Method | Path |
|--------|------|
| GET/POST | `/api/v1/reference-sets` |
| GET | `/api/v1/reference-sets/lookup?value=&set_type=` |
| GET/POST | `/api/v1/reference-sets/{id}/entries` |
| POST | `/api/v1/reference-sets/{id}/sync-feed` |
| GET/POST | `/api/v1/building-blocks` |

Analysts can create sets and blocks; delete reference sets is admin-only.

## Migration

```bash
cd backend && alembic upgrade head
```

Revision `009_reference_sets`.
