# 10. Refactored Backend Structure

## Directory Layout (v2.0)

```
backend/
├── alembic/                    # Schema migrations (configure versions/)
├── docs/                       # Audit reports & architecture docs
├── tests/
│   └── test_security.py
├── requirements.txt
└── app/
    ├── main.py                 # App factory, lifespan, health, WS
    ├── config.py               # Pydantic settings
    ├── database.py             # Async engine + session
    ├── dependencies.py         # Auth DI
    ├── security.py             # JWT, hashing, tokens
    │
    ├── core/                   # ★ NEW — Platform infrastructure
    │   ├── logging.py          # Structured JSON logging
    │   ├── errors.py           # Standard error responses
    │   └── health.py           # Liveness/readiness probes
    │
    ├── middleware/
    │   ├── request_context.py  # ★ NEW — Request/correlation IDs
    │   └── rate_limit.py       # Expanded rate limits
    │
    ├── pipeline/               # ★ NEW — Event ingestion pipeline
    │   ├── validator.py        # Input validation
    │   ├── normalizer.py       # Canonical event format
    │   ├── ingestion.py        # Batch orchestrator
    │   └── processor.py        # Post-ingestion security processing
    │
    ├── jobs/                   # ★ NEW — Background processing
    │   ├── queue.py            # Priority async job queue
    │   └── handlers.py         # Job handler registry
    │
    ├── models/                 # SQLAlchemy ORM
    │   ├── event.py            # + normalized_event, source_ip, username
    │   ├── user.py             # + lockout fields
    │   ├── host.py             # + api_key lifecycle
    │   ├── siem.py             # + offense timeline/related entities
    │   ├── user_session.py     # ★ NEW
    │   ├── agent_nonce.py      # ★ NEW
    │   └── analytics.py        # ★ NEW — daily stats
    │
    ├── routers/                # Thin HTTP handlers
    │   └── agent.py            # Uses pipeline, key rotation
    │
    ├── schemas/                # Pydantic models
    │
    ├── services/
    │   ├── correlation/        # ★ NEW — Extensible framework
    │   │   ├── framework.py    # Matcher ABC
    │   │   └── rules.py        # System rule definitions
    │   ├── analytics/          # ★ NEW
    │   │   └── aggregator.py   # Daily stat rollups
    │   ├── agent_auth.py       # ★ NEW — Signing + replay protection
    │   ├── correlation_engine.py  # Refactored engine
    │   ├── offense_engine.py   # Enhanced grouping
    │   ├── threat_score.py     # + offense factor
    │   ├── detection.py        # Fixed perf bug
    │   ├── migrate.py          # Extended DDL
    │   └── ...
    │
    └── websocket/
        └── manager.py
```

---

## Data Flow (New)

```
Agent POST /events
    │
    ▼
pipeline/ingestion.py
    ├─ validator.py      (reject bad data)
    ├─ normalizer.py     (canonical event)
    ├─ mitre enrich      (technique mapping)
    └─ persist to DB
    │
    ├─ [async] jobs/queue → correlation_pipeline
    │       ├─ detection.py
    │       ├─ correlation_engine.py
    │       ├─ timeline.py
    │       └─ threat_score.py
    │
    └─ offense_engine.link_event_to_offense()
```

---

## Module Responsibilities

| Module | Single Responsibility |
|--------|----------------------|
| `routers/*` | HTTP translation only |
| `pipeline/*` | Event ingest lifecycle |
| `jobs/*` | Async work execution |
| `services/detection.py` | Threshold-based alerting |
| `services/correlation/*` | Pattern matching |
| `services/offense_engine.py` | Alert/event grouping |
| `services/threat_score.py` | Risk calculation |
| `services/analytics/*` | Pre-aggregated metrics |
| `core/*` | Cross-cutting infrastructure |

---

## Configuration

| Setting | Default | Purpose |
|---------|---------|---------|
| `ASYNC_EVENT_PIPELINE` | true | Offload correlation to jobs |
| `AGENT_REQUEST_SIGNING` | false | HMAC agent auth |
| `ACCOUNT_LOCKOUT_ATTEMPTS` | 5 | Brute force protection |
| `ACCOUNT_LOCKOUT_MINUTES` | 15 | Lockout duration |
| `RETENTION_DAYS` | 90 | Event retention |

---

## Testing Strategy

```
tests/
├── unit/
│   ├── test_normalizer.py
│   ├── test_correlation_matchers.py
│   └── test_threat_score.py
├── integration/
│   ├── test_agent_ingest.py
│   ├── test_auth_lockout.py
│   └── test_offense_grouping.py
└── load/
    └── test_ingest_throughput.py
```

---

## Phase 2 Structure Additions

```
app/
├── repositories/       # Data access abstraction
│   ├── event_repo.py
│   └── alert_repo.py
├── workers/
│   └── standalone.py   # Redis consumer process
└── observability/
    ├── metrics.py      # Prometheus counters
    └── tracing.py      # OpenTelemetry spans
```
