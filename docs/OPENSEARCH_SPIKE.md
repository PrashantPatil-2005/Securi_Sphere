# OpenSearch Spike — SecuriSphere

## Status: Spike complete (pilot-ready)

OpenSearch is integrated as an **optional** search backend. PostgreSQL remains the default.

## Enable

```env
OPENSEARCH_URL=http://localhost:9200
SEARCH_BACKEND=opensearch
```

Start stack:

```bash
docker compose up -d opensearch
```

Backfill existing data:

```bash
cd backend
SEARCH_BACKEND=opensearch python scripts/backfill_opensearch.py 5000
```

## Architecture

| Component | Path |
|-----------|------|
| Index mappings | `app/search/mappings.py` |
| Client + search | `app/search/opensearch_client.py` |
| Document builders | `app/search/indexer.py` |
| Ingest hook | `app/pipeline/ingestion.py` |
| API switch | `app/routers/search.py` (`backend` field in response) |

## Indices

- `securi-events` — event_type, severity, description, raw_log, timestamp
- `securi-alerts` — title, description, severity, status
- `securi-hosts` — name, hostname, ip

## API behavior

`GET /api/v1/search?q=...` returns `"backend": "opensearch"` or `"postgres"`.

On OpenSearch failure, the router **falls back** to PostgreSQL automatically.

## Go / no-go (pilot)

| Criterion | Result |
|-----------|--------|
| Same JSON response shape | Yes |
| Real-time indexing on ingest | Yes |
| Fallback to Postgres | Yes |
| SIEM query parser (`/search/siem`) | Still Postgres (future work) |
| Production cluster (replicas, ISM, security) | No — out of spike scope |

**Recommendation:** Adopt OpenSearch for global search in staging; keep SIEM parser on Postgres until field mapping is complete.

## Next steps (post-spike)

1. OpenSearch backend for `/search/siem`
2. ISM retention policies on indices
3. Enable security plugin + TLS in production
4. Bulk worker for backfill instead of inline indexing
