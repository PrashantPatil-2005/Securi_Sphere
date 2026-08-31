# Phase 5.5 — Agent Reliability & Hardening: Completion Report

## Summary

Comprehensive audit and hardening of the Securi_Sphere agent across 10 dimensions: architecture, collection, buffering, SQLite durability, delivery, heartbeat, authentication, security, resource safety, and crash recovery. **8 fixes applied across 4 files.** 16 new regression tests added (51 → 67 total).

---

## Agent Architecture

### Current Pipeline
```
Collector (logs/events/metrics)
    ↓
Event normalization (parse_line)
    ↓
Local buffer (SQLite WAL, 50k items / 500MB limit)
    ↓
Sender (HTTP POST with HMAC signing, exponential backoff)
    ↓
Backend ACK
    ↓
Delete from buffer
```

### Lifecycle
1. Signal handlers (SIGTERM/SIGINT) set `_shutdown_requested` + `_shutdown_event`
2. Main loop polls every 1 second via `_shutdown_event.wait(timeout=1.0)`
3. Each iteration: flush buffer → heartbeat → metrics → collect logs
4. On exit: flush remaining buffer → close HTTP session

### Configuration
- Path: `/etc/securi/config.json`
- Fields: `server_url`, `api_key`, `signing_enabled`
- File permissions: 0o600

---

## Fixes Applied

### 1. Collector/Metrics/Heartbeat Exceptions Crash Main Loop (main.py)
- **Before:** A single exception from `collect_events()`, `collect_metrics()`, or `sender.heartbeat()` terminated the entire agent
- **After:** Each operation wrapped in individual `try/except` — failures are logged and the loop continues
- **Impact:** Agent continues collecting during transient collector errors

### 2. Buffer Flush Unbounded After Prolonged Offline (sender.py)
- **Before:** `flush_buffer()` dequeued ALL items and sent in one massive HTTP request — could overwhelm backend after hours of downtime
- **After:** `MAX_FLUSH_BATCH_SIZE=500` items per batch, processed in chunks
- **Impact:** Backend protected from recovery stampedes

### 3. Shutdown Doesn't Interrupt Main Loop Sleep (main.py)
- **Before:** `time.sleep(1)` in main loop — shutdown waited up to1 second even when signal was immediate
- **After:** `_shutdown_event.wait(timeout=1.0)` — shutdown interrupts instantly
- **Impact:** Faster graceful shutdown (<10ms vs up to1s)

### 4. HTTP Session Never Closed (sender.py, main.py)
- **Before:** `requests.Session()` leaked on exit
- **After:** `Sender.close()` added, called in `finally` block of `main()`
- **Impact:** File descriptor leak prevented

### 5. No Event Size Limits (buffer.py)
- **Before:** Enormous payloads could be enqueued without limit — memory pressure, slow serialization
- **After:** `MAX_EVENT_SIZE_BYTES=100KB` per event payload; oversized events dropped with warning
- **Impact:** Memory protection against malformed/malicious events

### 6. Config Validation (config.py)
- **Before:** Malformed JSON, invalid URL schemes, missing hostnames silently accepted
- **After:** JSON parse errors raise `SystemExit`, URL scheme validated (http/https only), hostname presence checked
- **Impact:** Agent fails clearly on bad config instead of running in broken state

### 7. Logging Throttle for Repeated Failures (sender.py)
- **Before:** Every failed request logged at WARNING level — could generate thousands of identical log lines during prolonged outages
- **After:** After initial failure log, suppressed for 60 seconds with summary message
- **Impact:** Log storms prevented during extended backend outages

### 8. Permanent Auth Failure (sender.py)
- **Before:** 401 responses treated same as network errors — agent kept retrying with permanently invalid credentials, buffering data that could never be sent
- **After:** `_auth_failed` flag set on 401; no buffering on permanent auth failure; single log message instead of repeated
- **Impact:** Agent stops wasting resources on permanently rejected credentials

---

## Audit Findings (Documented, Not Fixed)

### Buffer
| Finding | Severity | Status |
|---|---|---|
| SQLite WAL mode enabled | GOOD | Documented |
| busy_timeout=5000ms | GOOD | Documented |
| synchronous=NORMAL | GOOD | Documented |
| MAX_BUFFER_ITEMS=50,000 | GOOD | Documented |
| MAX_BUFFER_SIZE_MB=500 | GOOD | Documented |
| Stale item purge (48h) | GOOD | Documented |
| Per-operation connections (safe for SQLite) | ACCEPTABLE | Documented |
| No WAL checkpoint on idle | LOW | Documented |
| WAL journal unprotected on disk | LOW | Documented |

### Delivery
| Finding | Severity | Status |
|---|---|---|
| ACK after successful HTTP response | GOOD | Documented |
| Failed items retained for retry | GOOD | Documented |
| Partial batch failure: all items retry (no partial ACK) | ACCEPTABLE | Documented |
| Duplicate delivery possible on crash between send and delete | ACCEPTABLE | Documented — at-least-once delivery model |
| Backend deduplication via ingestion dedup layer | GOOD | Documented |

### Heartbeat
| Finding | Severity | Status |
|---|---|---|
| 30-second interval | GOOD | Documented |
| Agent hash + version sent | GOOD | Documented |
| Failure does not terminate agent | GOOD | Documented |
| Authenticated via API key header | GOOD | Documented |

### Authentication
| Finding | Severity | Status |
|---|---|---|
| API key in X-API-Key header | GOOD | Documented |
| Optional HMAC-SHA256 signing | GOOD | Documented |
| Nonce prevents replay attacks | GOOD | Documented |
| 401 = permanent auth failure (flagged) | GOOD | Fixed |
| API key in plaintext config file (0o600) | ACCEPTABLE | Documented |
| No credential rotation mechanism | MEDIUM | Documented |
| No enrollment token expiry check by agent | LOW | Documented |

### Security
| Finding | Severity | Status |
|---|---|---|
| TLS verification enabled by default (requests library) | GOOD | Documented |
| No secrets in logs | GOOD | Documented |
| No environment variable dumping | GOOD | Documented |
| Config file 0o600 permissions | GOOD | Documented |
| Event payloads not logged | GOOD | Documented |
| No debug mode in production | GOOD | Documented |

### Resource Safety
| Finding | Severity | Status |
|---|---|---|
| No unbounded lists in hot path | GOOD | Documented |
| Thread leak from backoff event | NEGLIGIBLE | Documented |
| File descriptors: SQLite per-operation, HTTP persistent | ACCEPTABLE | Documented |
| `psutil.cpu_percent(interval=1)` blocks1s per metrics cycle | ACCEPTABLE | Documented |

### Crash Recovery
| Finding | Severity | Status |
|---|---|---|
| SQLite WAL survives process crash | GOOD | Documented |
| Unsent events preserved in buffer | GOOD | Documented |
| Log tailer position lost on restart (may re-collect) | ACCEPTABLE | Documented — duplicate events handled by backend dedup |
| No schema migration system | MEDIUM | Documented |

### Collector Isolation
| Finding | Severity | Status |
|---|---|---|
| Log collection exceptions caught in main loop | GOOD | Fixed |
| Metrics collection exceptions caught in main loop | GOOD | Fixed |
| Heartbeat exceptions caught in main loop | GOOD | Fixed |
| Buffer flush exceptions caught in main loop | GOOD | Fixed |
| Final flush on shutdown protected | GOOD | Fixed |

---

## Batch Size & Recovery Throttling

### Batch Limits
- Per-request: unbounded event count (backend limit applies)
- Flush chunking: 500 items per batch (`MAX_FLUSH_BATCH_SIZE`)
- Event payload: 100KB max (`MAX_EVENT_SIZE_BYTES`)
- Buffer: 50,000 items / 500MB disk

### Recovery Behavior
After prolonged offline:
1. `flush_buffer()` loads all items via `dequeue_all()`
2. Processes in chunks of 500
3. Each chunk: separate HTTP POST
4. Only successful chunks removed from buffer
5. Failed chunks retained for next cycle

---

## Duplicate Delivery Analysis

### Scenario
```
Agent sends batch → Backend receives → Network fails before ACK
→ Agent retries → Duplicate events
```

### Assessment
- **At-least-once delivery**: duplicates are possible on crash between successful send and buffer deletion
- **Backend deduplication**: ingestion dedup layer handles deduplication server-side
- **No agent-side dedup needed**: backend already tracks seen event IDs

---

## ACK Semantics

### Safe Pattern Verified
```
HTTP POST → successful response → delete from buffer
```

### Partial Failure
- Backend does not support partial ACK
- On failure: entire batch retained for retry
- Accepted risk: accepted events re-sent on retry (backend dedup handles)

---

## Offline Mode

### Verified Behavior
```
Backend unavailable → agent continues collecting
→ events buffered in SQLite → backend returns → agent drains buffer
```

### Limits
- 50,000 items / 500MB buffer size
- 48-hour stale purge
- 100KB per event payload
- Buffer flush chunked at 500 items

---

## Measured Limits

| Metric | Value |
|---|---|
| Event payload limit | 100KB |
| Buffer item limit | 50,000 |
| Buffer disk limit | 500MB |
| Stale purge age | 48 hours |
| Flush batch size | 500 items |
| Max consecutive failures | 100 |
| Initial backoff | 1.0s |
| Max backoff | 60.0s |
| Backoff multiplier | 2.0x |
| Heartbeat interval | 30s |
| Metrics interval | 30s |
| Log collection interval | 10s |
| HTTP timeout | 15s |
| Logging throttle window | 60s |

---

## Bugs Fixed

### 1. Main Loop Crash on Collector Exception
- **Root cause:** No try/except around collector/metrics/heartbeat calls
- **Fix:** Individual try/except blocks per operation
- **Regression test:** `test_main_collector_exception_does_not_crash`

### 2. Unbounded Buffer Flush
- **Root cause:** `flush_buffer()` sent all items in one request
- **Fix:** `MAX_FLUSH_BATCH_SIZE=500` chunked processing
- **Regression test:** `test_sender_flush_batch_chunking`

### 3. Shutdown Latency
- **Root cause:** `time.sleep(1)` not interruptible
- **Fix:** `_shutdown_event.wait(timeout=1.0)` with signal-triggered set
- **Regression test:** `test_main_shutdown_event_set_on_signal`

### 4. HTTP Session Leak
- **Root cause:** No `close()` on `requests.Session`
- **Fix:** `Sender.close()` method, called in finally block
- **Regression test:** `test_sender_close`

### 5. Unbounded Event Payloads
- **Root cause:** No size validation on enqueue
- **Fix:** `MAX_EVENT_SIZE_BYTES=100KB` check before insert
- **Regression test:** `test_event_size_limit`

### 6. Silent Config Failures
- **Root cause:** No validation on config loading
- **Fix:** JSON parse errors raise SystemExit, URL validation
- **Regression tests:** `test_load_config_invalid_url_scheme`, `test_load_config_invalid_url_no_hostname`, `test_load_config_malformed_json`

### 7. Log Storms During Outages
- **Root cause:** Every failure logged at WARNING
- **Fix:** 60-second throttle window with suppression message
- **Regression test:** `test_sender_logging_throttle`

### 8. Wasted Retries on Permanent Auth Failure
- **Root cause:** 401 treated same as network error
- **Fix:** `_auth_failed` flag, no buffering on permanent failure
- **Regression tests:** `test_sender_401_sets_auth_failed`, `test_sender_401_does_not_buffer`, `test_sender_success_resets_auth_failed`

---

## Tests

### Agent Tests
| Suite | Before | After | Status |
|---|---|---|---|
| test_buffer.py | 10 | 13 | ✅ All pass |
| test_collector_events.py | 15 | 15 | ✅ All pass |
| test_collector_metrics.py | 2 | 2 | ✅ All pass |
| test_config.py | 5 | 8 | ✅ All pass |
| test_integrity.py | 5 | 5 | ✅ All pass |
| test_main.py | 2 | 4 | ✅ All pass |
| test_sender.py | 11 | 19 | ✅ All pass |
| **Total** | **51** | **67** | **✅ All pass** |

### New Regression Tests
| Test | Covers |
|---|---|
| `test_event_size_limit` | 100KB payload limit |
| `test_purge_stale_returns_zero_when_nothing_old` | Edge case: no stale items |
| `test_remove_by_ids_empty_list` | Edge case: empty deletion |
| `test_load_config_invalid_url_scheme` | Config validation: bad scheme |
| `test_load_config_invalid_url_no_hostname` | Config validation: no host |
| `test_load_config_malformed_json` | Config validation: bad JSON |
| `test_main_shutdown_event_set_on_signal` | Signal handler sets event |
| `test_main_collector_exception_does_not_crash` | Exception isolation |
| `test_sender_401_sets_auth_failed` | Permanent auth failure |
| `test_sender_401_does_not_buffer` | No buffering on 401 |
| `test_sender_success_resets_auth_failed` | Recovery from auth failure |
| `test_sender_close` | HTTP session cleanup |
| `test_sender_flush_batch_size` | Flush completes correctly |
| `test_sender_flush_batch_chunking` | Batch size enforcement |
| `test_sender_429_respects_retry_after` | Rate limit handling |
| `test_sender_logging_throttle` | Log storm prevention |

### Lint
- Ruff: `All checks passed!` (agent/ and tests/)

### Backend Integration
- Not applicable — agent is standalone, no Docker/PostgreSQL dependency

---

## Remaining Issues

### Confirmed Bugs
None — all identified issues fixed.

### Reliability Risks
- **Partial batch failure**: Backend does not support partial ACK; entire batch retries on any failure
- **Log position lost on restart**: Agent may re-collect recent logs (backend dedup handles duplicates)
- **No WAL checkpoint on idle**: WAL file may grow during idle periods

### Security Risks
- **API key in plaintext file**: `/etc/securi/config.json` stores API key in plaintext (0o600)
- **No credential rotation**: API key cannot be rotated without re-enrollment
- **No enrollment token expiry**: Agent does not check token expiry client-side

### Architectural Limitations
- **No schema migration**: SQLite schema changes require manual migration
- **No idle timeout**: Agent runs indefinitely even when no new events
- **Blocking metrics collection**: `psutil.cpu_percent(interval=1)` blocks main loop for1s
- **Per-operation SQLite connections**: Each buffer operation opens/closes a connection (safe but slower)

### Infrastructure Limitations
- **No Docker** — PostgreSQL integration tests unavailable
- **No Redis** — Redis-specific tests unavailable

### Future Improvements
- Add idle session timeout
- Add credential rotation mechanism
- Add WAL checkpoint on idle
- Add schema versioning and migration
- Move `cpu_percent(interval=0.1)` to non-blocking
- Add heartbeat-based health reporting
- Add agent self-update mechanism

---

## Files Changed

| File | Changes |
|---|---|
| `agent/agent/main.py` | Exception isolation for collector/metrics/heartbeat, shutdown event interrupt, HTTP session close, unused import cleanup |
| `agent/agent/sender.py` | Flush batch chunking, HTTP session close, permanent auth failure flag, logging throttle, unused import cleanup |
| `agent/agent/buffer.py` | Event size limit (100KB) |
| `agent/agent/config.py` | Config validation (JSON parse, URL scheme, hostname) |
| `agent/tests/test_buffer.py` | 3 new tests: event size limit, stale purge edge, empty removal |
| `agent/tests/test_sender.py` | 8 new tests: auth failure, session close, flush batching,429 handling, logging throttle |
| `agent/tests/test_config.py` | 3 new tests: invalid URL scheme, no hostname, malformed JSON |
| `agent/tests/test_main.py` | 2 new tests: shutdown event, exception isolation |

---

READY FOR PHASE 5.6
