# Team Contributions

This document records each team member's contributions to the Securi Sphere SIEM platform, mapped to actual code in the repository.

---

## Team Overview

| Member | Role | Primary Area | Key Directories |
|--------|------|-------------|-----------------|
| **Member 1** | Core SIEM / Backend / Security Engine | Backend architecture, detection, correlation, auth, API | `backend/app/` |
| **Member 2** | Frontend & Dashboard | Next.js SOC dashboard, UI components, real-time feed | `frontend/` |
| **Member 3** | Linux Agent & Telemetry | Host agent, log collection, metrics, offline buffer | `agent/` |
| **Member 4** | Deployment, Testing & Documentation | Docker, K8s, Helm, CI/CD, tests, documentation | `deploy/`, `helm/`, `k8s/`, `loadtests/`, `docs/` |

---

## Contribution Table

### Member 1 — Core SIEM / Backend / Security Engine

| Area | Contribution | Files / Directories | Evidence |
|------|-------------|---------------------|----------|
| **FastAPI Backend** | Application entry point, middleware stack, CORS, lifespan management | `backend/app/main.py`, `backend/app/config.py`, `backend/app/database.py` | App factory pattern with 41 routers registered |
| **Event Ingestion Pipeline** | Event validation, normalization, deduplication, processing pipeline | `backend/app/pipeline/` (6 files) | Pipeline processes agent events through validate → normalize → store → detect |
| **Detection Rule Engine** | Extensible registry-pattern detection engine with 7 rule types | `backend/app/services/detection.py`, `backend/app/models/alert_rule.py`, `backend/app/routers/alert_rules.py` | Registry pattern: `DetectionRegistry.register(rule_type, checker)` |
| **Correlation Engine** | Sequence, co-occurrence, and cross-host correlation algorithms | `backend/app/services/correlation/` (4 files), `backend/app/services/correlation_engine.py` | 3 correlation algorithms with confidence scoring |
| **Offense Engine** | Alert grouping into offenses with confidence scoring | `backend/app/services/offense_engine.py`, `backend/app/models/siem.py` (Offense, OffenseEvent) | Groups related alerts into QRadar-style offenses |
| **UEBA** | User & Entity Behavior Analytics with z-score anomaly detection | `backend/app/services/ueba.py`, `backend/app/models/ueba.py` | 7-day rolling baselines, configurable thresholds |
| **Attack Timeline** | Attack chain reconstruction from event sequences | `backend/app/services/timeline.py`, `backend/app/models/timeline.py` | Chains events into chronological attack narratives |
| **Threat/Risk Scoring** | Host threat scoring and risk trend tracking | `backend/app/services/threat_score.py`, `backend/app/services/risk_trends.py`, `backend/app/models/threat_score.py` | Per-host risk scores with historical trends |
| **Authentication** | JWT auth (HS256/RS256), HttpOnly cookies, refresh token rotation | `backend/app/auth_cookies.py`, `backend/app/security.py`, `backend/app/routers/auth.py` | Cookie-primary auth (XSS-safe) |
| **RBAC** | Role-based access control (admin, analyst, viewer) | `backend/app/dependencies.py`, `backend/app/models/role.py` | Dependency injection enforces roles on all mutations |
| **MFA** | TOTP multi-factor authentication | `backend/app/services/mfa.py` | pyotp-based TOTP with QR code generation |
| **Session Management** | Concurrent session limits, revocation, refresh rotation | `backend/app/services/auth_session.py`, `backend/app/models/user_session.py` | Session tracking with active session limits |
| **Rate Limiting** | Login brute-force protection with Retry-After headers | `backend/app/middleware/rate_limit.py` | Per-IP rate limiting with configurable thresholds |
| **Security Headers** | X-Content-Type-Options, X-Frame-Options, Referrer-Policy | `backend/app/middleware/security_headers.py` | Applied to all responses via middleware |
| **Audit Logging** | Tamper-evident SHA-256 hash chain audit log | `backend/app/services/audit.py`, `backend/app/services/audit_chain.py`, `backend/app/models/audit.py` | Each entry includes hash of previous entry |
| **Database Models** | 34 SQLAlchemy models for all SIEM entities | `backend/app/models/` (33 files) | Users, hosts, events, alerts, offenses, incidents, etc. |
| **API Routers** | 41 REST API endpoint files | `backend/app/routers/` (41 files) | Complete API surface for all SIEM operations |
| **WebSocket/Redis** | Real-time updates via WebSocket + Redis pub/sub | `backend/app/websocket/` (2 files), `backend/app/routers/ws.py` | Multi-instance broadcast via Redis pub/sub |
| **AI Security Assistant** | LLM-powered alert explanation, NL search, summaries | `backend/app/services/ai/` (5 files), `backend/app/routers/assistant.py` | Local-first with optional LLM enrichment |
| **OpenSearch Integration** | Optional search backend for scale | `backend/app/search/` (6 files) | PostgreSQL (default) + OpenSearch (optional) |
| **Background Jobs** | Job queue with memory or Redis backend | `backend/app/jobs/` (5 files) | Configurable: memory for dev, Redis for production |
| **Middleware Stack** | Rate limiting, request timeouts, security headers, request context | `backend/app/middleware/` (4 files) | 4 middleware layers on all requests |
| **Alembic Migrations** | 24 database migrations from baseline to latest features | `backend/alembic/versions/` (24 files) | Schema evolution with zero downtime |
| **Unit Tests** | 65+ unit tests covering all backend services | `backend/tests/` (65+ files) | Detection, correlation, auth, pipeline, WebSocket, etc. |
| **Integration Tests** | 36 integration tests with real PostgreSQL + Redis | `backend/tests/integration/` (36 files) | Full API endpoint testing |

### Member 2 — Frontend & Dashboard

| Area | Contribution | Files / Directories | Evidence |
|------|-------------|---------------------|----------|
| **Next.js App** | 14+ App Router configuration, routing, layouts | `frontend/app/`, `frontend/next.config.mjs`, `frontend/package.json` | App Router with (auth) and (dashboard) route groups |
| **Dashboard** | Executive KPIs, active threats, severity breakdown, live feed | `frontend/app/(dashboard)/page.tsx`, `frontend/components/dashboard/` (10 files) | Main dashboard with 9 section components |
| **Alerts UI** | Alert list, detail, triage, bulk actions, MITRE mapping | `frontend/app/(dashboard)/alerts/`, `frontend/components/alerts/` (14 files) | Full alert management workflow |
| **Hosts UI** | Host list, detail, enrollment, risk, agent health | `frontend/app/(dashboard)/hosts/`, `frontend/components/hosts/` (11 files) | Host lifecycle management |
| **Events UI** | Event browser, detail drawer, raw JSON, filtering | `frontend/app/(dashboard)/events/`, `frontend/components/events/` (8 files) | Event investigation interface |
| **Offenses/Incidents** | Offense list, detail, timeline, incident management | `frontend/app/(dashboard)/offenses/`, `frontend/components/offenses/` (10 files), `frontend/components/incidents/` (7 files) | Offense → incident promotion workflow |
| **MITRE Visualization** | ATT&CK heatmap, click-to-drill-down, technique details | `frontend/app/(dashboard)/mitre/`, `frontend/components/mitre/` (3 files) | Full MITRE matrix with interactive drill-down |
| **UEBA Viewer** | Anomaly list, summary cards | `frontend/app/(dashboard)/ueba/`, `frontend/components/ueba/` (3 files) | UEBA anomaly visualization |
| **Analytics** | Dashboard stats, charts, threat scores, host risk trends | `frontend/app/(dashboard)/analytics/`, `frontend/components/analytics/` (4 files), `frontend/components/charts/` (5 files) | Analytics with Recharts visualizations |
| **Timeline** | Attack timeline with replay player | `frontend/app/(dashboard)/timeline/`, `frontend/components/timeline/` (6 files) | Play/pause/step/scrubber controls |
| **Search** | Global search, saved searches | `frontend/app/(dashboard)/search/`, `frontend/components/search/` (2 files) | Search with saved query management |
| **Reports** | Compliance report generation UI | `frontend/app/(dashboard)/reports/` | SOC2, ISO27001, HIPAA templates |
| **Settings** | User, notification, system settings | `frontend/app/(dashboard)/settings/`, `frontend/components/settings/` (3 files) | Platform configuration interface |
| **Attack Lab** | Simulation runner, results, history, guided investigation | `frontend/app/(dashboard)/simulation/`, `frontend/components/attack-lab/` (12 files) | Full attack simulation interface |
| **Design System** | Reusable UI primitives (Button, Card, DataTable, Badge, etc.) | `frontend/components/design-system/` (18 files) | Consistent design language |
| **Base UI Components** | Generic components (Dialog, Drawer, Toast, Tabs, etc.) | `frontend/components/ui/` (20 files) | Shared UI primitives |
| **Layout** | AppShell, Sidebar, TopNav, BrandLogo, page transitions | `frontend/components/layout/` (7 files) | Dashboard layout system |
| **Auth Guard** | Route protection, auth state management | `frontend/components/guards/` (2 files), `frontend/lib/auth/session.ts` | Protected route wrapper |
| **Custom Hooks** | 21 React hooks for data fetching and UI state | `frontend/lib/hooks/` (21 files) | useAlerts, useEvents, useHosts, useOffenses, etc. |
| **API Client** | Authenticated API client with error handling | `frontend/lib/api.ts`, `frontend/lib/api/endpoints.ts` | Centralized API communication |
| **WebSocket** | Real-time update management | `frontend/lib/websocket.tsx` | WebSocket connection with auto-reconnect |
| **TypeScript Types** | 10 type definition files for all entities | `frontend/lib/types/` (10 files) | Alert, Event, Host, Offense, Incident, etc. |
| **Dark Mode** | SOC-optimized dark theme with glass panels | `frontend/lib/theme/`, `frontend/app/globals.css` | Default dark mode with toggle |
| **Virtualized Lists** | High-performance rendering for large datasets | `frontend/components/virtual-table/` (2 files) | TanStack Virtual for 10k+ rows |
| **Unit Tests** | 19 frontend test files | `frontend/__tests__/` (19 files) | Vitest + React Testing Library |
| **E2E Tests** | 7 Playwright E2E test specs | `frontend/e2e/` (7 files) | Full SOC lab scenario testing |
| **Onboarding** | First-run wizard and activation coach | `frontend/components/onboarding/` (2 files) | New analyst guided setup |

### Member 3 — Linux Agent & Telemetry

| Area | Contribution | Files / Directories | Evidence |
|------|-------------|---------------------|----------|
| **Agent Core** | Main loop, signal handling, lifecycle management | `agent/agent/main.py` | Daemon with graceful shutdown on SIGTERM/SIGINT |
| **Configuration** | YAML/env var configuration with overrides | `agent/agent/config.py` | Configurable collection intervals, backend URL, etc. |
| **Event Collector** | Security event collection (login, process, network) | `agent/agent/collector/events.py` | Collects authentication events, process starts, network connections |
| **Metrics Collector** | CPU, memory, disk, load average collection | `agent/agent/collector/metrics.py` | 30-second metric intervals via psutil |
| **Log Collector** | System log and auth log tailing | `agent/agent/collector/logs.py` | Syslog, journald, auth.log/secure parsing |
| **Offline Buffer** | SQLite local buffer for network outages | `agent/agent/buffer.py` | WAL-mode SQLite with FIFO flush on reconnect |
| **HMAC Sender** | HMAC-SHA256 signed HTTP requests | `agent/agent/sender.py` | Timestamp + nonce + payload signing with retry logic |
| **Integrity Checking** | Agent binary hash verification | `agent/agent/integrity.py` | SHA-256 hash verification on startup |
| **Installation Script** | One-line installer for Linux hosts | `agent/install.sh` | Automated download, configure, enable systemd |
| **Systemd Service** | Service unit file for daemon management | `agent/securi-agent.service` | Auto-restart, resource limits, logging |
| **Requirements** | Agent Python dependencies | `agent/requirements.txt` | Minimal: requests, psutil |
| **Agent Tests** | 67 tests covering all agent components | `agent/tests/` (8 test files) | Buffer, sender, config, collectors, integrity, main |

### Member 4 — Deployment, Testing & Documentation

| Area | Contribution | Files / Directories | Evidence |
|------|-------------|---------------------|----------|
| **Docker Compose** | 7 Compose configurations for different environments | `docker-compose*.yml` (7 files) | Base, dev, test, CI, prod, caddy, opensearch-dev, PITR |
| **Backend Dockerfile** | Multi-stage Docker build for backend | `backend/Dockerfile` | Python 3.11-slim, non-root user, health check |
| **Frontend Dockerfile** | Multi-stage Docker build for frontend | `frontend/Dockerfile` | Node 20-alpine, standalone output, non-root user |
| **Kubernetes Manifests** | Full K8s deployment (Deployments, Services, Ingress, etc.) | `k8s/` (12 files + overlays) | Production-ready with network policies |
| **Helm Chart** | Helm 3 chart with multiple value profiles | `helm/securi/` (11 templates + 3 values files) | Configurable for managed DB, ingress profiles |
| **Kustomize Overlays** | Managed database overlay | `k8s/overlays/managed-db/` | Removes PostgreSQL for managed DB services |
| **CI/CD Pipeline** | GitHub Actions with 13 jobs across all components | `.github/workflows/ci.yml` | Unit, integration, E2E, security, Docker, load tests |
| **Release Workflow** | Automated release pipeline | `.github/workflows/release.yml` | Version tagging and release creation |
| **Load Tests** | k6 smoke test for API load testing | `loadtests/smoke.js` | Auth + event ingestion load test |
| **Deploy Scripts** | 26 deployment and utility scripts | `scripts/` (26 files) | Linux, Windows, Docker, Kubernetes helpers |
| **Deploy Config** | Caddy, PostgreSQL PITR, cert-manager configs | `deploy/` (3 files) | Reverse proxy, backup, TLS automation |
| **Deployment Docs** | Complete deployment guides | `docs/DEPLOYMENT.md`, `docs/VPS_DEPLOY.md` | Docker Compose, VPS, production setup |
| **Kubernetes Docs** | K8s deployment and ingress guides | `docs/KUBERNETES.md`, `docs/KUBERNETES_INGRESS.md` | Manifest-based and Helm-based deployment |
| **Helm Docs** | Helm chart documentation | `docs/HELM.md` | Chart configuration and deployment |
| **Backup Docs** | Automated backup and PITR runbook | `docs/BACKUP_AUTOMATION.md`, `docs/PITR_RUNBOOK.md` | pg_dump, WAL archiving, recovery procedures |
| **Security Docs** | Production security checklist | `docs/PRODUCTION_SECURITY.md` | Pre-deployment security validation |
| **Health Probe Docs** | Liveness, readiness, startup probe setup | `docs/HEALTH_PROBES.md` | Docker/K8s/load balancer health checks |
| **Phase Reports** | 7 phase hardening and readiness reports | `docs/phase5.*-report.md` (7 files) | Database, Redis, auth, agent, performance, production, release |
| **Additional Docs** | Architecture, schema, API reference, guides | `docs/` (remaining files) | Cross-cutting documentation |

---

## Quantitative Summary

| Metric | Member 1 | Member 2 | Member 3 | Member 4 |
|--------|----------|----------|----------|----------|
| **Code files** | ~160+ | ~180+ | ~10 | ~30 (infra) |
| **Test files** | 109 | 26 | 8 | — |
| **Documentation** | 32 docs | 13 docs | 4 docs | 9 docs + 7 phase reports |
| **Database models** | 33 | — | — | — |
| **API endpoints** | 41 routers | — | — | — |
| **UI components** | — | 130+ | — | — |
| **Pages** | — | 28+ | — | — |
| **Custom hooks** | — | 21 | — | — |
| **Docker configs** | — | — | — | 7 Compose files |
| **K8s manifests** | — | — | — | 12+ files |
| **Helm templates** | — | — | — | 11 templates |
| **CI/CD jobs** | — | — | — | 13 jobs |
| **Scripts** | — | — | — | 26 scripts |

---

## Architecture Responsibility Map

```
Linux Agent (Member 3)
    ↓  HMAC-signed HTTPS
Event Ingestion Pipeline (Member 1)
    ↓  validate → normalize → store
Detection Engine (Member 1)
    ↓  7 rule types, threshold matching
Correlation Engine (Member 1)
    ↓  sequence, co-occurrence, cross-host
Offense / Risk / UEBA (Member 1)
    ↓  grouping, scoring, anomaly detection
SOC Dashboard (Member 2)
    ↓  Next.js, real-time WebSocket
Deployment & Operations (Member 4)
    ↓  Docker, K8s, Helm, CI/CD
```
