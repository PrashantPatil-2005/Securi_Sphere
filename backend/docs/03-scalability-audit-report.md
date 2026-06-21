# 3. Scalability Audit Report

## Capacity Targets

| Metric | Target | Current Capacity (Est.) |
|--------|--------|-------------------------|
| Hosts | 500+ | ~100 (pre-refactor), ~300 (post) |
| Events/day | 10M+ | ~500K (pre), ~2M (post with async) |
| API response | <200ms | 50-500ms depending on endpoint |
| Search | <500ms | 200ms-2s on large tables |
| Dashboard | <1s | 500ms-3s |

---

## Bottleneck Analysis

### Critical (Pre-Refactor)

| Bottleneck | Root Cause | Fix |
|------------|------------|-----|
| Event ingestion latency | Sync detection+correlation+scoring in HTTP | **Async job pipeline** |
| Threat score storm | `update_all_threat_scores()` per event | **Removed — per-host only** |
| Single PostgreSQL writer | All writes to one DB | Read replicas + partitioning |
| In-memory rate limit | Not shared across instances | Redis rate limiter |
| In-process scheduler | APScheduler in API process | Dedicated cron/worker pods |
| WebSocket broadcast | In-memory ConnectionManager | Redis pub/sub |

### High

| Bottleneck | Impact at Scale |
|------------|-----------------|
| Unpartitioned `events` table | Table scans degrade after ~50M rows |
| ILIKE search on `raw_log` | Full table scan, no index |
| No connection pooling config | Connection exhaustion under load |
| Batch size 100 with full pipeline | Long request times |

---

## Horizontal Scaling Architecture

```
                    ┌─────────────┐
                    │   Load      │
                    │   Balancer  │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ API Pod 1  │  │ API Pod 2  │  │ API Pod N  │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                   ┌─────────────┐
                   │    Redis    │
                   │  (jobs+pub) │
                   └──────┬──────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ Worker 1   │  │ Worker 2   │  │ Worker N   │
    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
          │               │               │
          └───────────────┼───────────────┘
                          ▼
              ┌───────────────────────┐
              │ PostgreSQL Primary    │
              └───────────┬───────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       ┌────────────┐         ┌────────────┐
       │ Read       │         │ Read       │
       │ Replica 1  │         │ Replica 2  │
       └────────────┘         └────────────┘
```

---

## Performance Optimizations Applied

1. **Async pipeline** — HTTP returns after persist; correlation runs in job queue
2. **Removed N×hosts threat scoring** from ingestion hot path
3. **Background notifications** — email/telegram via jobs
4. **Daily analytics pre-aggregation** — dashboard reads summary tables
5. **Composite indexes** on events (timestamp+host, type+timestamp)
6. **Dedicated columns** for username/source_ip — avoids JSONB scans

---

## Remaining Scale Work

| Phase | Work | Enables |
|-------|------|---------|
| 2 | Redis job queue | Multi-instance API |
| 2 | Connection pool tuning (`pool_size=20, max_overflow=10`) | Higher concurrency |
| 3 | Monthly event partitioning | 100M+ events |
| 3 | OpenSearch index | Sub-500ms full-text search |
| 4 | CQRS read models | Sub-200ms dashboards |
| 4 | Kafka ingest buffer | Burst handling (1M events/min) |

---

## Load Testing Recommendations

```bash
# Agent ingest load test
wrk -t4 -c100 -d60s -s ingest.lua http://api:8000/api/v1/agent/events

# Target: 1000 req/s sustained, p99 < 200ms (post-persist only)
```

Monitor: API latency histogram, job queue depth, DB connections, replication lag.
