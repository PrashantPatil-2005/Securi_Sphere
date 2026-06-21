# SecuriSphere Backend Audit — Master Index

Production-grade backend audit and redesign for SecuriSphere SIEM platform.

**Version:** 2.0.0  
**Date:** 2026-06-21  
**Scope:** Backend only (FastAPI + PostgreSQL)

---

## Deliverables

| # | Document | Description |
|---|----------|-------------|
| 1 | [01-backend-audit-report.md](./01-backend-audit-report.md) | Architecture, API, service layer findings |
| 2 | [02-security-audit-report.md](./02-security-audit-report.md) | Auth, agent, API security findings |
| 3 | [03-scalability-audit-report.md](./03-scalability-audit-report.md) | Scale limits, bottlenecks, growth path |
| 4 | [04-database-optimization-plan.md](./04-database-optimization-plan.md) | Schema, indexes, partitioning |
| 5 | [05-correlation-engine-design.md](./05-correlation-engine-design.md) | Extensible correlation framework |
| 6 | [06-offense-engine-design.md](./06-offense-engine-design.md) | QRadar-style offense grouping |
| 7 | [07-threat-scoring-design.md](./07-threat-scoring-design.md) | Host risk scoring model |
| 8 | [08-search-architecture.md](./08-search-architecture.md) | SIEM search design |
| 9 | [09-production-deployment-architecture.md](./09-production-deployment-architecture.md) | K8s deployment topology |
| 10 | [10-refactored-backend-structure.md](./10-refactored-backend-structure.md) | New module layout |

## Diagrams

| Diagram | File |
|---------|------|
| System Architecture | [diagrams/architecture.mmd](./diagrams/architecture.mmd) |
| Database ERD | [diagrams/database-erd.mmd](./diagrams/database-erd.mmd) |
| Event Ingestion Sequence | [diagrams/event-ingestion-sequence.mmd](./diagrams/event-ingestion-sequence.mmd) |
| Agent Flow | [diagrams/agent-flow.mmd](./diagrams/agent-flow.mmd) |
| Correlation Engine | [diagrams/correlation-engine.mmd](./diagrams/correlation-engine.mmd) |
| Offense Engine | [diagrams/offense-engine.mmd](./diagrams/offense-engine.mmd) |

## Implementation Status (v2.0.0)

The following production foundations were implemented in code:

- **Event pipeline:** `app/pipeline/` — validate → normalize → enrich → persist → async process
- **Job queue:** `app/jobs/` — background correlation, notifications, retention, analytics
- **Structured logging:** `app/core/logging.py` — JSON logs with request_id, correlation_id
- **API hardening:** Request context middleware, structured errors, expanded rate limits
- **Event normalization:** Dedicated columns + JSONB `normalized_event` on every event
- **Correlation framework:** Extensible matchers (sequence, co-occurrence) + 5 system rules
- **Offense engine:** Related hosts/users, timeline, alert_count
- **Threat scoring:** Offense factor added to risk calculation
- **Auth hardening:** Account lockout, session tracking, refresh token rotation
- **Agent security:** API key rotation, revocation, optional HMAC signing
- **Analytics layer:** `analytics_daily_stats` pre-aggregation table
- **Health checks:** `/health/live`, `/health/ready`

## Migration Path

1. Run backend — `migrate_schema()` applies additive DDL on startup
2. Set env vars: `ASYNC_EVENT_PIPELINE=true`, `AGENT_REQUEST_SIGNING=false` (enable when agents updated)
3. Phase 2: Deploy Redis + dedicated worker pods for job queue
4. Phase 3: Partition `events` table by month; add read replicas
5. Phase 4: OpenSearch/Elasticsearch for full-text search at scale
