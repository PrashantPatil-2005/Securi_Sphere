# Read replicas

Optional PostgreSQL read replica routing offloads heavy **read** queries from the primary writer. When `DATABASE_READ_URL` is unset, all traffic uses the primary (no behavior change).

## Configuration

```env
# Primary (writes + fallback reads)
DATABASE_URL=postgresql+asyncpg://user:pass@primary:5432/securi

# Optional read replica (streaming replica / RDS read endpoint)
DATABASE_READ_URL=postgresql+asyncpg://user:pass@replica:5432/securi

# Readiness warns when replay lag exceeds threshold (seconds)
READ_REPLICA_LAG_WARN_SECONDS=30
```

Use the same pool settings as the primary (`DB_POOL_*` from `docs/CONNECTION_POOLING.md`). Each API process maintains **two** pools when a read URL is configured.

## Routed endpoints

Read replica sessions (`get_db_read`) are used for:

| Area | Routes |
|------|--------|
| Analytics | `GET /api/v1/analytics/*` |
| Events | `GET /api/v1/events`, `GET /api/v1/events/types` |
| Search | `GET /api/v1/search`, `GET /api/v1/search/siem` |
| SIEM dashboards | `GET /api/v1/siem/*` |
| Threat scores | `GET /api/v1/threat-scores` |
| MITRE | `GET /api/v1/mitre/*` |
| UEBA (read) | `GET /api/v1/ueba/summary`, `GET /api/v1/ueba/anomalies` |
| Overview | `GET /api/v1/overview` |
| System (read) | `GET /api/v1/system/pipeline`, `GET /api/v1/system/stats` |

**Writes** (agent ingest, auth, incidents, exports, mutations) always use `DATABASE_URL` via `get_db`.

## Operations

### Admin API

```
GET /api/v1/system/replicas
```

Returns lag (`pg_last_xact_replay_timestamp`), health, and routed endpoint list.

`GET /api/v1/system/pool` includes separate `primary` and `read` pool stats.

### Health

Readiness reports `read_replica: ok` when configured and reachable. High lag adds `read_replica_lag: warn:Ns` without failing readiness (primary remains authoritative).

## Replication lag

Analytics and search may be slightly stale on the replica. For strict consistency, leave `DATABASE_READ_URL` unset or route only reporting workloads.

Typical managed Postgres setup:

- **AWS RDS** — use the cluster read endpoint
- **Cloud SQL** — read replica connection name
- **Patroni / HAProxy** — replica service DNS

Failover and promotion are infrastructure concerns; the app does not auto-promote replicas.

## Implementation

- `backend/app/database.py` — `read_engine`, `get_db_read()`, `read_session_factory()`
- `backend/app/core/read_replica.py` — lag probe and status

## Related

- `docs/CONNECTION_POOLING.md` — per-process connection budgets
- `docs/DB_ENCRYPTION_AT_REST.md` — TLS to managed Postgres
- `backend/docs/03-scalability-audit-report.md` — scale roadmap
