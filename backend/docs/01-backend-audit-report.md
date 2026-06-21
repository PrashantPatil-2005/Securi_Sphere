# 1. Backend Audit Report

## Executive Summary

SecuriSphere backend was a functional student-project SIEM API. This audit identifies architectural gaps that would prevent operation at hundreds of hosts and millions of events/day, and documents the v2.0 production refactor.

**Overall Grade (Pre-Refactor):** C+ — Feature-complete for demos, not production-ready  
**Overall Grade (Post-Refactor Foundation):** B+ — Production patterns in place; scale-out components pending

---

## Project Structure Analysis

### Before (Problems)

```
backend/app/
├── routers/          # 20+ routers — HTTP concerns mixed with orchestration
├── services/         # Flat module list — no domain boundaries
├── models/           # ORM only — no repository layer
├── middleware/       # Single rate limiter
└── main.py           # God file: scheduler, WS, overview, lifespan
```

| Issue | Severity | Impact |
|-------|----------|--------|
| No domain separation (ingestion vs detection vs analytics) | High | Unmaintainable at scale |
| Synchronous pipeline in HTTP handler | Critical | Ingestion latency grows with event volume |
| `create_all()` + raw SQL migrations | High | No versioned schema history |
| Dead code (`correlation.py`) | Low | Confusion |
| Global singletons everywhere | Medium | Hard to test, no DI container |
| No structured logging | High | Cannot debug production incidents |
| No request tracing | High | Cannot correlate logs across services |

### After (Refactored)

```
backend/app/
├── core/             # Logging, errors, health
├── pipeline/         # Ingestion: validate → normalize → enrich → persist
├── jobs/             # Async job queue + handlers
├── middleware/       # Request context, rate limiting
├── services/
│   ├── correlation/  # Extensible rule framework
│   └── analytics/    # Pre-aggregated stats
├── routers/          # Thin HTTP layer
└── models/           # ORM + new security/analytics tables
```

---

## Service Layer Review

### Detection Service (`services/detection.py`)

**Problems Found:**
- `run_detection_for_host()` called `update_all_threat_scores()` for ALL hosts on every single event — O(n×hosts) per ingestion
- Duplicate correlation/timeline calls from both agent router and detection service
- Notifications sent synchronously in alert creation path

**Fixes Applied:**
- Removed global threat score update from per-host detection
- Notifications enqueued via job queue
- Post-ingestion pipeline isolated in `pipeline/processor.py`

### Correlation Engine

**Problems Found:**
- Only 2 hardcoded rules
- No extensibility framework
- Sequence matcher only — no co-occurrence patterns

**Fixes Applied:**
- `CorrelationRuleMatcher` ABC with `SequenceMatcher` and `CoOccurrenceMatcher`
- 5 system rules including Brute Force Success, Privilege Escalation, Host Compromise

### Offense Engine

**Problems Found:**
- Host-only grouping, no related users/hosts/timeline
- Only auth events linked directly

**Fixes Applied:**
- `related_hosts`, `related_users`, `timeline`, `alert_count` on offenses
- Expanded event types for offense linking

---

## API Design Review

### Endpoint Inventory: 60+ routes across 20 routers

| Category | Count | Auth Coverage |
|----------|-------|---------------|
| Auth | 6 | Partial rate limit |
| Agent | 4 | API key |
| Hosts | 8 | JWT + RBAC |
| Events/Alerts | 12 | JWT |
| SIEM/Analytics | 15 | JWT |
| Admin | 5 | admin role |

### API Problems

| Endpoint | Issue | Recommendation |
|----------|-------|----------------|
| `GET /api/v1/overview` | Unauthenticated | Require JWT or internal network only |
| `GET /health` | No DB check | Split into live/ready (implemented) |
| All list endpoints | No cursor pagination | Add keyset pagination for events |
| Export endpoints | Unbounded result sets | Stream + limit |
| Agent `/events` | Sync pipeline | Async pipeline (implemented) |

### Missing (Now Partially Added)

- [x] Request IDs (`X-Request-ID`)
- [x] Correlation IDs (`X-Correlation-ID`)
- [x] Structured error responses
- [ ] Idempotency keys on agent ingest
- [ ] OpenAPI response schemas on all endpoints
- [ ] API versioning strategy beyond `/v1`

---

## Business Logic Separation

| Concern | Before | After |
|---------|--------|-------|
| Event validation | Inline in router | `pipeline/validator.py` |
| Normalization | None (raw metadata JSONB) | `pipeline/normalizer.py` |
| Detection | Mixed in ingestion | `pipeline/processor.py` + jobs |
| Analytics | Direct SQL on events | `analytics_daily_stats` table |
| Notifications | Sync in create_alert | Job queue |

---

## Dependency Injection

**Before:** FastAPI `Depends()` only — no service interfaces, no test doubles.

**After:** Same pattern but with clear module boundaries. Recommended Phase 2:
- Repository interfaces for Event, Alert, Host
- Settings injection via `Depends(get_settings)`
- Factory for job queue (in-memory vs Redis)

---

## Separation of Concerns Scorecard

| Layer | Before | After |
|-------|--------|-------|
| HTTP/Routing | 6/10 | 8/10 |
| Business Logic | 5/10 | 8/10 |
| Data Access | 6/10 | 7/10 |
| Infrastructure | 3/10 | 8/10 |
| Security | 5/10 | 8/10 |

---

## Priority Remediation Roadmap

### P0 — Done in v2.0
1. Async event processing pipeline
2. Event normalization schema
3. Structured logging + request tracing
4. Fix O(n) threat score bug
5. Account lockout + session tracking

### P1 — Next Sprint
1. Alembic versioned migrations (replace create_all)
2. Redis job queue
3. Idempotency on agent ingest
4. Keyset pagination on events/alerts
5. Authenticate `/overview`

### P2 — Scale Phase
1. Event table partitioning
2. OpenSearch for full-text
3. Read replicas
4. Dedicated worker service
