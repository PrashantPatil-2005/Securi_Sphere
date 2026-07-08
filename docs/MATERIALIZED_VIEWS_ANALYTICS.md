# Materialized views for analytics

Pre-aggregated **PostgreSQL materialized views** speed up dashboard and SIEM historical queries by scanning daily rollups instead of raw `events` and `alerts` tables.

## Views

| View | Purpose |
|------|---------|
| `mv_events_daily` | Events per day × host × type × severity |
| `mv_alerts_daily` | Alerts per day × severity |
| `mv_failed_logins_daily` | SSH login failures per day × host × user |

Simulation events (`source = 'simulation'`) are excluded from event views.

Created by migration **`016_analytics_materialized_views`**. Unique indexes support `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

## Configuration

```env
ANALYTICS_MATERIALIZED_VIEWS_ENABLED=true
ANALYTICS_MV_REFRESH_INTERVAL_MINUTES=60
```

When disabled, analytics endpoints fall back to live SQL on raw tables.

## Refresh schedule

- **Automatic** — APScheduler job every `ANALYTICS_MV_REFRESH_INTERVAL_MINUTES` (default 60)
- **Manual** — admin API below
- **After migration** — initial `REFRESH` runs in migration upgrade

Daily `analytics_daily_stats` aggregation (cron 03:00) remains separate; MVs complement it for chart queries.

## Routed endpoints

When enabled, these use materialized views (with fallback on error):

| Endpoint | Data |
|----------|------|
| `GET /api/v1/siem/historical` | Events, alerts, active hosts trends |
| `GET /api/v1/analytics/retention` | Event/alert bucket counts |

Responses include `"source": "materialized_views"` when served from MVs.

Risk score trends still query `host_risk_history` directly (no MV yet).

## Admin API

```
GET  /api/v1/system/analytics-mvs
POST /api/v1/system/analytics-mvs/refresh
```

Requires **admin** role. Status includes `ispopulated` from `pg_matviews`.

## Operations

- Run `alembic upgrade head` to create views
- After large backfills, call **refresh** or wait for the scheduled job
- Pair with read replicas (`docs/READ_REPLICAS.md`) — refresh runs on primary; reads can use replica if MVs exist there (streaming replica) or primary pool

## Related

- `docs/CONNECTION_POOLING.md` — connection budgets
- `backend/app/services/analytics/aggregator.py` — `analytics_daily_stats` table
- `backend/docs/04-database-optimization-plan.md` — OLAP strategy
