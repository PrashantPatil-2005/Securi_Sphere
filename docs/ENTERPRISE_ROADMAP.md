# SecuriSphere Enterprise Roadmap

Final review (Phase 15) after production transformation pass. Score: **62/100** — pilot-ready, not internet-facing enterprise SOC.

## Remaining Critical Weaknesses

1. **No OpenSearch** — PostgreSQL ILIKE search breaks at scale
2. **Single-process jobs + WebSocket** — no horizontal scaling
3. **Empty Alembic chain** — schema via `migrate.py` only
4. **No mTLS / agent TLS** — API key in transit unless HTTPS terminated
5. **HS256 JWT** — no JWKS / key rotation
6. **Event table unpartitioned** — retention helps but inserts slow at volume

## Top 100 Improvements (Prioritized)

### P0 — Block production scale
1. OpenSearch cluster for events/search
2. Redis job queue + worker service
3. Redis WebSocket pub/sub
4. Real Alembic migrations from baseline
5. Event table partitioning by month
6. Keyset pagination on `/events`
7. mTLS for agent transport
8. RS256 JWT + refresh rotation hardening
9. Secrets manager (Vault/AWS SM)
10. OIDC/SAML SSO

### P1 — Enterprise SOC
11. Offense → incident promotion UI
12. Alert detail page with full context
13. Investigation workspace (single pane)
14. Playbooks / SOAR webhooks
15. UEBA baseline anomalies
16. Windows agent
17. Multi-tenancy (org_id scoping)
18. Compliance report templates (SOC2, ISO)
19. Executive PDF reports
20. Load tests (k6) in CI

### P2 — Analyst productivity
21–30. Virtualized alert table, keyboard nav, bulk actions, saved searches, custom dashboards, MITRE heatmap drill-down, timeline replay, host risk score trends, notification rules UI, Slack/email test button

### P3 — Platform hardening
31–50. MFA, account recovery rate limits, CSP nonces, audit log export, immutable audit store, DB encryption at rest docs, backup automation, PITR runbook, K8s manifests, Helm chart, ingress + cert-manager, health probes, graceful shutdown, circuit breakers, request timeouts, connection pooling tuning, read replicas, materialized views for analytics, correlation rule editor v2, false-positive feedback loop, threat intel feeds

### P4 — Product polish
51–70. Onboarding wizard, empty states per role, contextual help, dark/light theme tokens audit, motion reduced preference, mobile responsive tables, i18n foundation, role-based home dashboards, agent install wizard, host grouping/tags, network map v2, simulation sandbox banner, demo data seeder, changelog in-app, status page integration

### P5 — Engineering excellence
71–100. HTTP integration tests, Playwright E2E, agent integration tests, security regression suite, performance budgets in CI, API contract tests, OpenAPI client generation, structured logging JSON, trace IDs to frontend, Sentry integration, dependency scanning, SBOM, license audit, ADR folder, runbooks, on-call playbook, disaster recovery drill, chaos testing, feature flags, blue/green deploy docs, canary strategy, cost monitoring, data classification tags, GDPR export/delete, pen test remediation tracker, bug bounty prep, vendor security questionnaire answers, SOC2 control mapping

## Phase Deliverables Index

| Deliverable | Location |
|-------------|----------|
| Complete audit (condensed) | `docs/PRODUCTION_TRANSFORMATION.md` |
| Security audit | `backend/docs/02-security-audit-report.md` |
| Performance audit | `docs/PERFORMANCE_AUDIT.md` |
| Architecture | `backend/docs/diagrams/architecture.mmd` |
| ERD | `backend/docs/diagrams/database-erd.mmd` |
| Deployment | `docs/DEPLOYMENT.md` |
| API reference | `docs/API.md` |
| Frontend redesign notes | `frontend/REDESIGN_AUDIT.md` |

## Microsoft / Splunk / Wazuh Lens — Final Gaps

- **Sentinel**: No KQL, no entity graph, no automated response
- **QRadar**: Offense engine exists but no reference sets / building blocks UI
- **Splunk**: No SPL, no forwarder protocol, no index-time fields
- **Wazuh**: Linux agent only, no FIM/decoders/ruleset parity
- **CrowdStrike**: No EDR telemetry, no process tree

## Recommended Next Sprint (2 weeks)

1. HTTP integration tests (auth, RBAC, offenses pagination)
2. Offense → incident promotion button
3. Virtualized alerts table (`@tanstack/react-virtual`)
4. Migrate metrics/reports/simulation to TanStack Query
5. Document production `.env` with `ALLOW_REGISTRATION=false`, `ENABLE_SIMULATION=false`
