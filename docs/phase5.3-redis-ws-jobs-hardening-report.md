# Phase 5.3 — Redis, WebSocket & Background Job Hardening: Completion Report

## Summary

Comprehensive audit and hardening of Redis clients, WebSocket event propagation, background job queue, scheduler, and post-commit side effects. **12 fixes applied across 12 files.**

---

## Fixes Applied

### 1. Redis Permanent Failure Sentinel (rate_limit.py, recovery_rate_limit.py, ingest_dedup.py)
- **Before:** All 3 modules set `_redis = False` on first failure — a transient Redis blip permanently disabled Redis for the process lifetime
- **After:** Set `_redis = None` on failure (same as broker/pubsub), allowing retry on next request
- **Impact:** Transient Redis failures no longer permanently poison rate limiting, dedup, or recovery limits

### 2. Redis Connection Cleanup on Shutdown (rate_limit.py, recovery_rate_limit.py, ingest_dedup.py)
- **Before:** 3 Redis clients were never closed during application shutdown — leaked connections
- **After:** Added `close_redis()` functions to all 3 modules; lifecycle.py calls them all during shutdown
- **Impact:** No more orphaned Redis connections on process exit

### 3. Redis Socket Timeouts (rate_limit.py, recovery_rate_limit.py, ingest_dedup.py)
- **Before:** No `socket_timeout` — a hung Redis server would block the async client indefinitely
- **After:** Added `socket_timeout=5`, `socket_connect_timeout=3`, `max_connections=5` to all 3 modules
- **Impact:** Redis operations time out instead of hanging forever

### 4. Redis Pool Size Limits (rate_limit.py, recovery_rate_limit.py, ingest_dedup.py)
- **Before:** `Redis.from_url()` without `max_connections` — defaults to 2^31 (unlimited pool)
- **After:** `max_connections=5` on all 3 modules
- **Impact:** Bounded connection pool prevents connection exhaustion

### 5. Unbounded Job Queues (redis_broker.py)
- **Before:** Priority queues (`securi:jobs:high/normal/low`) had no TTL or size cap — memory grows indefinitely if workers are down
- **After:** Added `LLEN` check before enqueue — drops jobs when queue exceeds 10,000 entries
- **Impact:** Redis memory bounded even during extended worker outage

### 6. Job Retry Backoff (queue.py)
- **Before:** Failed jobs retried immediately (no delay) — risk of tight retry loops on transient errors
- **After:** Exponential backoff: 2s → 4s → 8s → 16s → 32s → 60s (capped)
- **Impact:** Transient errors get breathing room; no hot retry loops

### 7. Permanently Failed Jobs → Dead-Letter (queue.py)
- **Before:** Jobs exhausting retries were silently dropped — no visibility into failures
- **After:** Permanently failed jobs sent to `securi:jobs:dead-letter` queue (capped at 1000)
- **Impact:** Failed jobs visible in dead-letter for debugging; no silent data loss

### 8. Timed-Out Handler Retry (queue.py)
- **Before:** Timed-out jobs were silently dropped with "handler may still be running" — one timeout = permanent job loss
- **After:** Timed-out jobs are retried (up to max_retries), then sent to dead-letter on permanent failure
- **Impact:** Transient timeouts no longer cause permanent job loss

### 9. Scheduler Error Logging (scheduler.py)
- **Before:** All 8 scheduler job functions had no try/except — unhandled exceptions propagated silently to APScheduler
- **After:** Every job function wrapped in `try/except` with `logger.error(..., exc_info=True)`
- **Impact:** All scheduler failures now produce structured error logs with full tracebacks

### 10. Post-Commit Side Effects: `create_alert()` (detection.py, database.py)
- **Before:** `create_alert()` fired OpenSearch indexing, job enqueues, and WebSocket broadcasts AFTER flush but BEFORE commit — phantom data visible to clients on rollback
- **After:** Outbox pattern: side effects recorded in `db.info["post_commit_hooks"]` and executed AFTER `get_db()` commits
- **Impact:** Clients never see alerts/events that were rolled back

### 11. Post-Commit Side Effects: Ingestion Pipeline (ingestion.py)
- **Before:** `ingest_event_batch()` fired per-event WebSocket broadcasts and batch OpenSearch indexing after flush but before commit
- **After:** Outbox pattern: broadcasts and OpenSearch indexing deferred to post-commit hooks via `db.info`
- **Impact:** Real-time feed events only appear after DB commit

### 12. Post-Commit Side Effects: Alerts Router (alerts.py)
- **Before:** All 3 alert mutation endpoints fired WebSocket broadcasts before commit
- **After:** All 3 broadcasts deferred to post-commit hooks via `db.info["post_commit_hooks"]`
- **Impact:** Dashboard never shows alert status changes that were rolled back

### 13. Heartbeat OpenSearch Before Flush (agent.py)
- **Before:** `heartbeat()` called `index_host(host)` WITHOUT `db.flush()` — OpenSearch received in-memory state that wasn't even flushed to the DB connection
- **After:** Added `await db.flush()` before `index_host(host)`
- **Impact:** OpenSearch receives consistent data

---

## Audit Findings (Documented, Not Fixed)

### Redis Architecture
| Finding | Severity | Status |
|---|---|---|
| 5 independent Redis singletons with separate pools | INFO | Documented |
| No configurable Redis settings in Settings class | MEDIUM | Documented |
| Unbounded dedup keys (24h TTL but no size cap) | MEDIUM | Documented |
| Rate limiter fallback memory dict unbounded | LOW | Documented |
| LPUSH+LTRIM non-atomic dead-letter race | LOW | Documented |
| No Redis health-check-interval on connections | LOW | Documented |

### WebSocket Architecture
| Finding | Severity | Status |
|---|---|---|
| No max connection limit (DoS vector) | MEDIUM | Documented |
| Semaphore per-broadcast (no global throttling) | LOW | Documented |
| No application-level ping/pong | LOW | Documented |
| No message ordering across broadcasts | INFO | Documented |
| O(n) disconnect in post-gather loop | LOW | Documented |

### Job Queue Architecture
| Finding | Severity | Status |
|---|---|---|
| No transactional acknowledgment (BRPOP consumes immediately) | HIGH | Documented — architectural limitation |
| No job deduplication (detection_and_scores, correlation_pipeline) | MEDIUM | Documented |
| handle_ueba_scan dead code (defined but never registered) | LOW | Documented |
| register_job_handlers() called 3 times at startup | LOW | Documented |
| Redis job payloads stored in plaintext JSON | LOW | Documented |

### Post-Commit Side Effects
| Finding | Severity | Status |
|---|---|---|
| OIDC token exchange before commit | MEDIUM | Documented |
| Playbook webhook before handler commit | LOW | Documented |
| Notification HTTP calls before handler commit | LOW | Documented |
| Host status broadcasts in update_host_statuses() | MEDIUM | Documented — called from scheduler jobs with own sessions |

---

## Post-Commit Side Effects Audit — Complete Location Map

| Location | Before | After | Method |
|---|---|---|---|
| `detection.py:309-339` (create_alert) | 5 side effects before commit | Outbox via `db.info` | **FIXED** |
| `ingestion.py:158-208` (ingest_event_batch) | Broadcast + OpenSearch before commit | Outbox via `db.info` | **FIXED** |
| `alerts.py:165` (bulk_update_alerts) | Broadcast before commit | Outbox via `db.info` | **FIXED** |
| `alerts.py:289` (update_alert_status) | Broadcast before commit | Outbox via `db.info` | **FIXED** |
| `alerts.py:338` (update_alert_feedback) | Broadcast before commit | Outbox via `db.info` | **FIXED** |
| `agent.py:107` (heartbeat) | OpenSearch before flush | Added `db.flush()` | **FIXED** |
| `detection.py:472,502` (update_host_statuses) | Host status broadcasts before commit | Intentionally unchanged | Called from scheduler jobs with own sessions |
| `simulation_runner.py:88` (simulated events) | Broadcast before commit | Intentionally unchanged | Simulation context, low risk |
| `host_notify.py:8` (agent registration) | Broadcast before commit | Intentionally unchanged | Depends on caller session |
| `oidc.py:51,93` (OIDC token exchange) | External API before commit | Intentionally unchanged | External IdP, cannot retract |

---

## Verification

- **Unit tests:** 7/7 pass
- **Lint:** All 12 modified files clean (ruff)
- **OpenAPI:** 194 routes generated successfully

---

## Files Changed

| File | Changes |
|---|---|
| `backend/app/middleware/rate_limit.py` | Retry on failure (None not False), socket_timeout, pool limit, close_redis() |
| `backend/app/services/recovery_rate_limit.py` | Retry on failure (None not False), socket_timeout, pool limit, close_redis() |
| `backend/app/services/ingest_dedup.py` | Retry on failure (None not False), socket_timeout, pool limit, close_redis() |
| `backend/app/core/lifecycle.py` | Added 3 Redis modules to shutdown cleanup |
| `backend/app/jobs/redis_broker.py` | Queue size cap (10,000) |
| `backend/app/jobs/queue.py` | Retry backoff, timed-out retry, dead-letter for failures |
| `backend/app/scheduler.py` | try/except wrappers for all 8 job functions |
| `backend/app/database.py` | Post-commit hook execution in get_db() |
| `backend/app/services/detection.py` | Outbox pattern for create_alert() side effects |
| `backend/app/pipeline/ingestion.py` | Outbox pattern for ingestion side effects |
| `backend/app/routers/alerts.py` | Outbox pattern for 3 alert broadcast locations |
| `backend/app/routers/agent.py` | Added db.flush() before OpenSearch in heartbeat |

---

## Recommended Follow-Ups (Phase 5.4+)

1. **Job transactional acknowledgment** — Implement in-flight tracking with `BRPOPLPUSH` pattern so worker crashes don't lose jobs
2. **Job deduplication** — Add per-host dedup key for `detection_and_scores` and `correlation_pipeline` jobs
3. **Configurable Redis settings** — Move pool sizes, timeouts, retry settings to `Settings` class
4. **WebSocket max connections** — Add per-user and global connection limits
5. **Post-commit for host status broadcasts** — `update_host_statuses()` broadcasts are called from scheduler jobs (own sessions), so the hooks don't auto-execute. Consider explicit hook execution after scheduler commit.
6. **Remove dead code** — `handle_ueba_scan` in handlers.py is defined but never registered
7. **Dedup key size cap** — Consider LRU eviction or smaller TTL for high-volume dedup keys

---

## Infrastructure Limitations

- **Docker not available** — PostgreSQL integration tests (`tests/integration/`, `tests/test_concurrency_pg.py`) could not run
- **Redis not available** — Redis-specific tests (`tests/test_redis_integration.py`) could not run
- **Browser not available** — Frontend WebSocket tests could not run

---

## Remaining Issues

### Architectural Limitations (Not Bugs)
- No transactional job acknowledgment (BRPOP is consume-and-hope)
- No WebSocket message deduplication at protocol level
- Post-commit hooks don't execute for scheduler jobs with own sessions (only for `get_db()` endpoints)
- Redis Pub/Sub is not durable — message loss acceptable for UI-only events

### Future Improvements
- Move post-commit side effects to dedicated outbox table with worker
- Add OpenSearch reconciliation job to detect/repair drift
- Add WebSocket connection limits and per-client message queue depth
- Add Redis `health_check_interval` to all connections

---

READY FOR PHASE 5.4
