# OpenSearch at Scale — Securi

Builds on the [OpenSearch spike](OPENSEARCH_SPIKE.md) with production-oriented indexing and operations.

## What changed (v2)

| Area | Before (spike) | At scale |
|------|----------------|----------|
| Event storage | Single flat `securi-events` index | Monthly rollover `securi-events-YYYY.MM` + legacy index support |
| Ingest | One HTTP index per event | Bulk batches (`OPENSEARCH_BULK_SIZE`, default 500) |
| Backfill | Sequential single-document index | Bulk batches via script or admin API |
| SIEM totals | Page size only | `track_total_hits` for accurate counts |
| Retention | Manual | ISM policy on `securi-events-*` (when ISM plugin available) |
| Ops | CLI script only | `POST /api/v1/system/opensearch/backfill` + cluster health in `/system/health` |

## Enable

```env
OPENSEARCH_URL=http://localhost:9200
SEARCH_BACKEND=opensearch
OPENSEARCH_BULK_SIZE=500
OPENSEARCH_RETENTION_DAYS=90
```

```bash
docker compose up -d opensearch
```

## Backfill

**CLI** (dev / one-off):

```bash
cd backend
SEARCH_BACKEND=opensearch python scripts/backfill_opensearch.py 50000
```

**Admin API** (requires admin JWT):

```http
POST /api/v1/system/opensearch/backfill?event_limit=50000&alert_limit=5000
```

## Index layout

| Index pattern | Purpose |
|---------------|---------|
| `securi-events-YYYY.MM` | Monthly event shards (writes) |
| `securi-events*` | Search pattern (includes legacy flat index) |
| `securi-alerts` | Alerts |
| `securi-hosts` | Hosts |

## Architecture

```
PostgreSQL (source of truth)
    │
    ├─ ingest batch ──► bulk_index_event_docs() ──► securi-events-YYYY.MM
    ├─ alert create ──► index_alert()
    └─ backfill job ──► run_opensearch_backfill()

GET /search, /search/siem
    └─ OpenSearch (track_total_hits) ──fallback──► PostgreSQL
```

## Health

`GET /api/v1/system/health` (admin) includes:

- `search_backend`: `opensearch` | `postgres`
- `opensearch`: cluster status, node count, index count

Readiness probe adds `opensearch` check when `SEARCH_BACKEND=opensearch`.

## Production notes (still manual)

- Enable OpenSearch security plugin + TLS (`docs/PRODUCTION_SECURITY.md`)
- Multi-node cluster + replicas for HA
- Dedicated bulk worker via job queue for very large backfills
- CDC (Debezium) if Postgres→OpenSearch lag must be sub-second at millions of events/day

## Files

| Path | Role |
|------|------|
| `app/search/index_names.py` | Monthly index naming |
| `app/search/bulk.py` | Bulk action builder |
| `app/search/mappings.py` | Templates, ISM policy, keyword subfields |
| `app/search/opensearch_client.py` | Client, bulk, search, health |
| `app/services/opensearch_backfill.py` | Shared backfill service |
| `scripts/backfill_opensearch.py` | CLI wrapper |
