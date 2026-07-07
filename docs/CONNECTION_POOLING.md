# Connection pooling

Securi uses SQLAlchemy's **QueuePool** (via `asyncpg`) with tunable limits so API workers and job processes share Postgres connections efficiently without exhausting `max_connections`.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_SIZE` | `20` | Persistent connections per process |
| `DB_MAX_OVERFLOW` | `10` | Extra connections allowed under burst load |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait for a free connection |
| `DB_POOL_RECYCLE` | `1800` | Recycle connections after N seconds (stale NAT/LB) |
| `DB_POOL_PRE_PING` | `true` | Validate connections before checkout |

```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true
```

**Per-process maximum** = `DB_POOL_SIZE + DB_MAX_OVERFLOW` (default **30**).

## Sizing for production

Plan Postgres `max_connections` above total app usage:

```
cluster_connections ≈ (API_replicas + worker_replicas) × (pool_size + max_overflow)
```

Example: 3 API pods + 2 workers × 30 = **150** connections → set Postgres `max_connections` ≥ 200 (leave headroom for admin/migrations).

| Workload | Suggested `pool_size` | `max_overflow` |
|----------|----------------------|----------------|
| Dev / single instance | 5–10 | 5 |
| Production API | 20 | 10 |
| Dedicated job worker | 10 | 5 |

Lower `pool_size` when running many replicas; raise it for single large nodes with heavy agent ingest.

## Operations

### Admin API

```
GET /api/v1/system/pool?api_replicas=3&worker_replicas=2
```

Requires **admin** role. Returns live pool stats (`checked_out`, `overflow`, `utilization`) and a cluster connection budget estimate.

### Health

Readiness still checks `SELECT 1`. Pool exhaustion surfaces as database errors in readiness (`database: error: ...`) or slow responses before `pool_timeout` elapses.

### Shutdown

`engine.dispose()` on graceful shutdown closes all pooled connections cleanly (`docs/GRACEFUL_SHUTDOWN.md`).

## Implementation

- `backend/app/core/db_pool.py` — pool kwargs and status helpers
- `backend/app/database.py` — `create_async_engine(..., **engine_options())`

Test mode (`TESTING=true`) uses smaller pools (`5` + `5`) to reduce connection use in CI.

## Related

- `docs/REQUEST_TIMEOUTS.md` — request-level timeouts
- `docs/DB_ENCRYPTION_AT_REST.md` — TLS to managed Postgres
- `backend/docs/03-scalability-audit-report.md` — broader scale guidance
