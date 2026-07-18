# Securi Enterprise Roadmap

> Last updated: July 2026

## Current State

Score: **8.5/10** (final year project). Core SIEM pipeline functional: Collection → Detection → Correlation → Offense → Investigation. 20 Alembic migrations, OpenSearch integration, Redis pub/sub, OIDC SSO, 34 DB models, 39 API routers.

## What Exists (Implemented)

| Capability | Status | Notes |
|------------|--------|-------|
| OpenSearch search backend | Done | Optional, toggled via `SEARCH_BACKEND` |
| Redis job queue + worker | Done | `JOB_QUEUE_BACKEND=redis` |
| Redis WebSocket pub/sub | Done | `WS_PUBSUB_BACKEND=redis` |
| Alembic migrations | Done | 20 migrations (001–020) |
| Event table partitioning | Done | Optional `EVENT_PARTITIONING_ENABLED` |
| OIDC/SSO | Done | Google, Azure AD, compatible IdPs |
| User invites + provisioning | Done | `docs/USER_PROVISIONING.md` |
| Offense → incident promotion | Done | API + UI |
| RS256 JWT | Done | `JWT_ALGORITHM=RS256` |
| Agent mTLS | Done | Cert fingerprint enrollment |
| Read replicas | Done | `DATABASE_READ_URL` |
| Analytics materialized views | Done | Daily rollups |
| MITRE ATT&CK mapping | Done | Per-alert tactic/technique |
| UEBA (statistical anomaly) | Done | Z-score vs rolling baselines |
| SOAR playbooks | Done | Webhook-based response |
| IOC lookup (VirusTotal) | Done | Investigation pane |
| Compliance reports | Done | SOC2, ISO27001 templates |
| Executive PDF reports | Done | Generated reports |
| Immutable audit store | Done | Hash-chained audit logs |
| False-positive feedback | Done | Alert feedback loop |
| Threat intel feeds | Done | Reference sets |
| Correlation engine | Done | Sequence, co-occurrence, cross-host |

## Remaining Gaps

| Gap | Impact | Effort |
|-----|--------|--------|
| Multi-tenancy (org_id scoping) | HIGH | 1–2 weeks |
| Native Windows agent / Sysmon | MEDIUM | 1 week |
| Packet capture / network forensics | LOW | 1 week |
| Hash-pinned dependencies (supply chain) | MEDIUM | 2h |
| Migrate to PyJWT (replace python-jose) | MEDIUM | 4h |
| Frontend unit tests | HIGH | 1 day |
| Load tests (k6) in CI | MEDIUM | 4h |
| OpenSearch security plugin (non-dev) | HIGH | 2 days |
| NetworkPolicy manifests for K8s | MEDIUM | 4h |
| PodDisruptionBudgets for K8s | LOW | 2h |
| mTLS for agent transport (active, not just docs) | HIGH | 1 day |

## Phase Deliverables Index

| Deliverable | Location |
|-------------|----------|
| Security audit | `backend/docs/02-security-audit-report.md` |
| Architecture | `backend/docs/diagrams/architecture.mmd` |
| ERD | `backend/docs/diagrams/database-erd.mmd` |
| Deployment | `docs/DEPLOYMENT.md` |
| API reference | `docs/API.md` |
| Production security | `docs/PRODUCTION_SECURITY.md` |
| OIDC setup | `docs/OIDC_SSO.md` |

## Recommended Next Sprint (2 weeks)

1. Frontend unit tests (5–10 key components)
2. Load tests (k6) in CI
3. Migrate to PyJWT
4. Hash-pinned dependencies
5. Agent test coverage (buffer, sender, main)
