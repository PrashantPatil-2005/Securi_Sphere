# Member 1 — Core SIEM / Backend / Security Engine

> Overall SIEM architecture, FastAPI backend, event ingestion pipeline, detection rule engine, correlation engine, offense engine, threat/risk scoring, UEBA, attack timeline, authentication/authorization, RBAC/MFA/session security, database models, real-time WebSocket/Redis, AI security assistant.

---

## 1. What This Module Does

Member 1 owns the **entire backend** of the Securi Sphere SIEM platform. This is the core technical contribution — a FastAPI-based security operations center backend that:

- **Ingests events** from Linux agents via HMAC-signed HTTP endpoints
- **Normalizes and validates** incoming telemetry (logs, metrics, flows)
- **Detects threats** using an extensible rule engine (7 rule types)
- **Correlates alerts** into multi-stage attack patterns (sequence, co-occurrence, cross-host)
- **Groups related alerts into offenses** with confidence scoring
- **Scores host risk** using threat scoring and UEBA anomaly detection
- **Reconstructs attack timelines** from event chains
- **Enforces security** — JWT auth, RBAC, MFA, rate limiting, tamper-evident audit logs
- **Provides real-time updates** via WebSocket + Redis pub/sub
- **Powers the AI assistant** for alert explanation and NL search

---

## 2. Main Files & Folders

### Application Entry Point

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app factory, middleware, router registration, lifespan |
| `backend/app/config.py` | Pydantic settings (env vars, defaults) |
| `backend/app/database.py` | SQLAlchemy async engine + session factory |
| `backend/app/scheduler.py` | APScheduler for periodic tasks (UEBA scans, retention) |

### Event Ingestion Pipeline (`backend/app/pipeline/`)

| File | Purpose |
|------|---------|
| `pipeline/__init__.py` | Pipeline package |
| `pipeline/ingestion.py` | Event ingestion endpoint handler |
| `pipeline/normalizer.py` | Field normalization (syslog, journald, custom formats) |
| `pipeline/validator.py` | Schema validation for incoming events |
| `pipeline/processor.py` | Pipeline orchestration (validate → normalize → store → detect) |
| `pipeline/flow_collector.py` | Network flow collection |
| `pipeline/windows_collector.py` | Windows event log collection |

### Detection Engine (`backend/app/services/detection.py`)

| File | Purpose |
|------|---------|
| `services/detection.py` | Extensible rule engine with registry pattern |
| `models/alert_rule.py` | Alert rule database model |
| `models/alert.py` | Alert database model |
| `routers/alert_rules.py` | Detection rule CRUD API |
| `routers/alerts.py` | Alert list, detail, bulk actions, feedback |

**7 built-in detection rules:**
1. Failed login threshold
2. Brute force detection
3. High CPU usage
4. High memory usage
5. High disk usage
6. Service failure
7. Agent offline

### Correlation Engine (`backend/app/services/correlation/`)

| File | Purpose |
|------|---------|
| `services/correlation/__init__.py` | Correlation package |
| `services/correlation/framework.py` | Core correlation framework |
| `services/correlation/rules.py` | Correlation rule definitions |
| `services/correlation/validation.py` | Rule validation |
| `services/correlation_engine.py` | Correlation engine orchestration |
| `models/correlation.py` | CorrelationRule + CorrelationResult models |
| `routers/correlation_rules.py` | Correlation rule CRUD API |

**3 correlation algorithms:**
1. **Sequence matcher** — ordered event sequences (e.g., login → privilege escalation → data access)
2. **Co-occurrence matcher** — related events within time window
3. **Cross-host matcher** — lateral movement detection across hosts

### Offense Engine (`backend/app/services/offense_engine.py`)

| File | Purpose |
|------|---------|
| `services/offense_engine.py` | Groups related alerts into offenses with confidence scoring |
| `services/incident_promotion.py` | Offense → incident promotion workflow |
| `models/siem.py` | Offense, OffenseEvent, HostRiskHistory models |
| `routers/offenses.py` | Offense list, detail, timeline API |
| `routers/incidents.py` | Incident management API |

### UEBA (`backend/app/services/ueba.py`)

| File | Purpose |
|------|---------|
| `services/ueba.py` | User & Entity Behavior Analytics |
| `services/risk_trends.py` | Host risk score history tracking |
| `models/ueba.py` | UebaAnomaly model |
| `models/threat_score.py` | HostThreatScore model |
| `routers/ueba.py` | UEBA anomaly viewer API |
| `routers/threat_scores.py` | Threat score history API |

**Detection method:** 7-day rolling baselines with z-score anomaly detection.

### Attack Timeline (`backend/app/services/timeline.py`)

| File | Purpose |
|------|---------|
| `services/timeline.py` | Attack chain reconstruction from events |
| `models/timeline.py` | AttackTimeline model |
| `routers/timeline.py` | Timeline reconstruction API |

### Authentication & Security

| File | Purpose |
|------|---------|
| `app/auth_cookies.py` | JWT in HttpOnly cookie management |
| `app/security.py` | Password hashing, JWT creation |
| `app/dependencies.py` | FastAPI dependency injection (get_current_user, require_role) |
| `services/auth_session.py` | Session management, refresh token rotation |
| `services/mfa.py` | TOTP multi-factor authentication |
| `services/oidc.py` | OIDC/SSO integration |
| `services/oidc_roles.py` | OIDC role mapping |
| `services/user_provisioning.py` | Admin user provisioning |
| `middleware/rate_limit.py` | Login brute-force protection |
| `middleware/security_headers.py` | X-Content-Type-Options, X-Frame-Options, etc. |
| `middleware/request_timeout.py` | Request timeout enforcement |
| `middleware/request_context.py` | Request context propagation |
| `routers/auth.py` | Login, register, logout, password reset, MFA |
| `routers/oidc.py` | OIDC/SSO callback |
| `routers/users.py` | User management (admin) |

### Database Models (`backend/app/models/`)

33 SQLAlchemy models across:
- **Users & Auth:** User, Role, RefreshToken, UserSession, PasswordResetToken, UserInvite
- **Core SIEM:** Host, Event, Metric, AlertRule, Alert, MitreTechnique
- **Detection & Response:** CorrelationRule, CorrelationResult, AttackTimeline, HostThreatScore, Offense, Incident
- **Investigation:** ReferenceSet, BuildingBlock, SavedSearch, GeneratedReport, UebaAnomaly
- **Operations:** AuditLog, NotificationSettings, NotificationRule, Playbook, DashboardLayout, TelemetryEvent

### Real-Time WebSocket (`backend/app/websocket/`)

| File | Purpose |
|------|---------|
| `websocket/manager.py` | WebSocket connection manager |
| `websocket/redis_pubsub.py` | Redis pub/sub for multi-instance broadcast |
| `routers/ws.py` | WebSocket endpoint |

### AI Security Assistant (`backend/app/services/ai/`)

| File | Purpose |
|------|---------|
| `services/ai/__init__.py` | AI package |
| `services/ai/assistant.py` | Alert explanation, investigation summaries |
| `services/ai/context.py` | Context assembly for LLM calls |
| `services/ai/llm.py` | LLM provider abstraction |
| `services/ai/nl_search.py` | Natural language search |
| `services/ai/summaries.py` | Alert/investigation summarization |
| `routers/assistant.py` | AI copilot API endpoints |

### Search (`backend/app/search/`)

| File | Purpose |
|------|---------|
| `search/opensearch_client.py` | OpenSearch client |
| `search/siem_opensearch.py` | SIEM-specific OpenSearch queries |
| `search/indexer.py` | Event indexing |
| `search/mappings.py` | Index mappings |
| `search/bulk.py` | Bulk operations |
| `routers/search.py` | Global search API |
| `routers/siem.py` | SIEM query execution |

### Background Jobs (`backend/app/jobs/`)

| File | Purpose |
|------|---------|
| `jobs/queue.py` | Job queue (memory or Redis backend) |
| `jobs/worker.py` | Background worker |
| `jobs/handlers.py` | Job handler registration |
| `jobs/redis_broker.py` | Redis broker |
| `jobs/serialization.py` | Job serialization |

### API Routers (`backend/app/routers/`)

41 API endpoint files covering all SIEM functionality.

### Alembic Migrations (`backend/alembic/`)

24 database migrations from baseline to latest features.

### Tests (`backend/tests/`)

- **65+ unit tests** (no DB required)
- **36 integration tests** (require PostgreSQL + Redis)
- **5 performance tests**
- **3 unit test modules**

---

## 3. Architecture / Design

### QRadar-Style 3-Layer Pipeline

```
Layer 1: COLLECTION    → Agent logs, metrics, flows
Layer 2: PROCESSING    → Detection rules, correlation, offense grouping, UEBA, MITRE
Layer 3: SEARCH        → SIEM query parser, global search, OpenSearch (optional)
```

### Extensible Rule Engine Pattern

The detection engine uses a **registry pattern** — new rule types are added by registering a checker class:

```python
# services/detection.py
class DetectionRegistry:
    _checkers: dict[str, Type[BaseChecker]] = {}

    @classmethod
    def register(cls, rule_type: str, checker: Type[BaseChecker]):
        cls._checkers[rule_type] = checker
```

### Security-First Auth Design

- **JWT in HttpOnly cookies** (XSS-safe, not localStorage)
- **RBAC** enforced on all mutation endpoints
- **MFA** via TOTP authenticator apps
- **Rate limiting** with Retry-After headers
- **Tamper-evident audit log** with SHA-256 hash chain

---

## 4. Important Implementation Details

- **Event deduplication** uses `ingest_dedup` table with configurable TTL
- **Correlation engine** runs synchronously in the request path for real-time results
- **UEBA scans** run on a scheduler (configurable interval, default daily)
- **Read replicas** supported for offloading heavy read queries
- **Circuit breakers** protect outbound calls to flaky external services
- **Graceful shutdown** drains in-flight requests before exit

---

## 5. Technologies Used

| Technology | Purpose |
|-----------|---------|
| FastAPI | Async Python web framework |
| SQLAlchemy 2.0 (async) | ORM with async PostgreSQL |
| PostgreSQL 16 | Primary database |
| Redis 7 | Job queue, WebSocket pub/sub, session state |
| OpenSearch 2.11 | Optional full-text search |
| Alembic | Database migrations |
| Pydantic v2 | Settings + request/response validation |
| python-jose | JWT creation/verification |
| pyotp | TOTP MFA |
| passlib + bcrypt | Password hashing |
| APScheduler | Periodic task scheduling |
| uvicorn | ASGI server |

---

## 6. Testing

### Running Tests

```bash
cd backend

# Unit tests (no DB required)
pytest tests/ -v --ignore=tests/integration -m "not integration"

# All tests (requires PostgreSQL + Redis via Docker)
pytest tests/ -v

# Specific test file
pytest tests/test_detection.py -v

# Integration tests
pytest tests/integration/ -v

# Security scan
bandit -r app --severity-level high

# Lint
ruff check app tests
```

### Test Coverage Areas

- Detection rule engine (unit + integration)
- Correlation engine (matchers, validation)
- Offense engine (grouping, timelines)
- UEBA (anomaly detection)
- Auth (JWT, RBAC, MFA, OIDC)
- Pipeline (ingestion, normalization, validation)
- WebSocket (manager, Redis pub/sub)
- Job queue (memory + Redis)
- Database (read replicas, connection pooling)
- Middleware (rate limiting, timeouts, security headers)

---

## 7. Screenshots / Diagrams for Report

Include these from `backend/docs/diagrams/`:

| Diagram | File | Description |
|---------|------|-------------|
| Architecture | `backend/docs/diagrams/architecture.mmd` | High-level system architecture |
| Event Ingestion | `backend/docs/diagrams/event-ingestion-sequence.mmd` | Sequence diagram for event flow |
| Correlation Engine | `backend/docs/diagrams/correlation-engine.mmd` | Correlation algorithm flow |
| Offense Engine | `backend/docs/diagrams/offense-engine.mmd` | Alert → offense grouping |
| Database ERD | `backend/docs/diagrams/database-erd.mmd` | Entity-relationship diagram |
| Agent Flow | `backend/docs/diagrams/agent-flow.mmd` | Agent → backend data flow |

Additional docs to reference in report:

| Document | Purpose |
|----------|-------------|
| `backend/docs/01-backend-audit-report.md` | Backend code quality audit |
| `backend/docs/02-security-audit-report.md` | Security review |
| `backend/docs/05-correlation-engine-design.md` | Correlation design deep-dive |
| `backend/docs/06-offense-engine-design.md` | Offense engine design |
| `backend/docs/07-threat-scoring-design.md` | Threat scoring design |

---

## 8. Possible Viva Questions

### Architecture
1. **Q: How does the 3-layer SIEM pipeline work?**
   A: Collection (agent → events), Processing (detection, correlation, offense, UEBA), Search (query parser, OpenSearch). Mirrors IBM QRadar's architecture.

2. **Q: Why did you choose FastAPI over Django/Flask?**
   A: Native async support for PostgreSQL (asyncpg), WebSocket, and Redis. Higher throughput for real-time event ingestion. Automatic OpenAPI docs.

### Detection
3. **Q: How is the detection engine extensible?**
   A: Registry pattern — new rule types register a checker class. The engine iterates registered checkers against incoming events. Currently 7 built-in rules.

4. **Q: What correlation algorithms do you use?**
   A: Three: sequence matching (ordered events), co-occurrence (related events in time window), cross-host (lateral movement detection). Each uses confidence scoring.

### Security
5. **Q: How do you prevent XSS attacks?**
   A: JWT stored in HttpOnly, Secure cookies (not localStorage). CSP nonces in Next.js middleware. Security headers on all responses.

6. **Q: How does RBAC work?**
   A: Three roles (admin, analyst, viewer). FastAPI dependency injection checks role on every mutation endpoint. Admin can manage users and settings.

7. **Q: What is the tamper-evident audit log?**
   A: Each audit entry includes SHA-256 hash of the previous entry, creating a hash chain. Any tampering breaks the chain integrity verification.

### Performance
8. **Q: How do you handle high event volumes?**
   A: Async pipeline, connection pooling (QueuePool/asyncpg), optional read replicas, OpenSearch for search offload, materialized views for analytics.

9. **Q: How does the UEBA anomaly detection work?**
   A: 7-day rolling baseline per user/entity. Z-score calculation against baseline. Configurable threshold for anomaly flagging.
