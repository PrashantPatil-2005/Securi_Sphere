# Securi Production Transformation

This document consolidates Phases 1–15 of the production-grade transformation: audit findings, implemented improvements, and the enterprise roadmap.

## Phase 1 — Audit Summary (Post-Transformation)

### Critical (addressed in this pass)
| Issue | Fix |
|-------|-----|
| No HTTP security headers | `SecurityHeadersMiddleware`, `next.config.mjs` headers |
| localStorage token XSS surface | Cookie-primary auth in `frontend/lib/api.ts` |
| Simulation in production | `ENABLE_SIMULATION` config gate |
| Agent signing mismatch | HMAC headers in `agent/agent/sender.py` |
| Offense list O(n) memory | SQL `COUNT` + `OFFSET/LIMIT` pagination |
| Investigation workflow gaps | `InvestigationTrail`, offense timeline fields, incident detail API |

### Critical (remaining)
| Issue | Priority |
|-------|----------|
| No OpenSearch / partitioned events | P0 for >1M events/day |
| In-process job queue / WebSocket | P0 for horizontal scale |
| Alembic migrations empty | P0 for prod schema governance |
| No mTLS / agent TLS enforcement | P0 for enterprise agent deploy |

### High (partially addressed)
- System health dashboard (`/system`, `/api/v1/system/*`)
- Expanded retention (alerts, timelines, audit, dedup)
- OpenAPI disabled outside development
- Admin-only simulation and system routes

## Phase 2–3 — Frontend / UX
- Cookie-primary authentication
- Investigation trail component linking Alert → Offense → Host → Timeline → Incident
- System health page (admin)
- Security headers on Next.js
- Settings page honest about “Coming soon” (prior ROI pass)
- Tier A pages on TanStack Query; offenses/incidents/rules migrated

## Phase 4–6 — Backend / DB / Agent
- Security headers middleware
- System router with health + stats
- Offense API enriched (`timeline`, `related_hosts`, `related_users`, `alert_count`)
- `GET /incidents/{id}` with notes and linked alerts
- Retention policy expanded
- Agent request signing (HMAC) when enabled
- Agent version header `X-Agent-Version`

## Phase 7–8 — SIEM / Investigation
Existing: pipeline, correlation, offenses, threat scores, MITRE, timelines.
Added: investigation navigation trail, offense timeline in UI, incident detail API foundation.

## Phase 9 — Performance Targets
| Target | Status |
|--------|--------|
| Dashboard < 2s | Achievable with TanStack Query + memo (executive page) |
| API < 200ms | Offense pagination fix removes full-table load |
| Search < 500ms | Limited by PostgreSQL ILIKE until OpenSearch |
| WS instant | In-process; breaks multi-replica without Redis pub/sub |

## Phase 10 — Security
Implemented: headers, cookie auth, lockout, RBAC, rate limit, signing, simulation gate, docs off in prod.
Remaining: RS256/JWKS, secrets manager, MFA, SSO, mTLS.

## Phase 11 — Enterprise Features
| Feature | Status |
|---------|--------|
| User profile | Wired |
| Settings | Wired (honest scope) |
| Audit logs | API + page |
| Reports/PDF/CSV | Existing |
| Notification center | WS + settings API |
| System health | **New** |
| Rule management | Wired with meta API |
| Investigation workspace | Trail component |
| Executive dashboard | Existing |

## Phase 13 — Documentation Index
- Architecture: `backend/docs/diagrams/architecture.mmd`
- ERD: `backend/docs/diagrams/database-erd.mmd`
- Agent flow: `backend/docs/diagrams/agent-flow.mmd`
- Deployment: `docs/DEPLOYMENT.md`, `backend/docs/09-production-deployment-architecture.md`
- API: `docs/API.md`
- This report: `docs/PRODUCTION_TRANSFORMATION.md`

## Phase 14 — Testing
- 16+ backend unit tests
- CI: pytest, ruff, frontend lint/tsc, docker build
- Gap: HTTP integration tests, Playwright E2E, load tests

## Phase 15 — Top 20 Enterprise Roadmap
1. OpenSearch for search/analytics
2. Redis job broker + dedicated worker process
3. Redis WebSocket pub/sub
4. Real Alembic migration chain
5. OIDC/SAML SSO + MFA
6. mTLS agent transport
7. Event table partitioning
8. Keyset pagination on events
9. Incident detail UI with notes
10. Offense → incident promotion
11. Playwright E2E in CI
12. Kubernetes manifests + ingress TLS
13. Secrets manager integration
14. UEBA / baseline anomaly detection
15. Windows agent
16. SOAR webhook playbooks
17. Multi-tenancy
18. Compliance report templates
19. Load test suite (k6)
20. 24/7 on-call runbooks

## Production Readiness Score: 62/100
Suitable for **controlled pilot** (single tenant, <50 hosts, trusted network). Not yet suitable for **internet-facing enterprise SOC** without items 1–6 above.
