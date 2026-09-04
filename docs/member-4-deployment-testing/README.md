# Member 4 — Deployment, Testing & Documentation

> Docker/Compose, Kubernetes, Helm, CI/CD, load testing, test organization/execution, installation/configuration documentation, user documentation, project documentation.

---

## 1. What This Module Does

Member 4 owns the **deployment infrastructure, testing pipeline, and documentation** for the Securi Sphere SIEM platform:

- **Docker Compose** — 7 configurations (base, dev, test, CI, prod, opensearch-dev, PITR)
- **Kubernetes** — Full manifest set with Kustomize overlays
- **Helm chart** — Production-ready Helm 3 chart with values profiles
- **CI/CD** — GitHub Actions workflows (unit, integration, E2E, security, Docker build, load tests)
- **Load testing** — k6 smoke tests
- **Test organization** — Structured test suites across all components
- **Documentation** — Installation guides, deployment guides, security checklists, runbooks
- **Scripts** — 26 deployment and utility scripts

---

## 2. Main Files & Folders

### Docker Compose Configurations

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base — PostgreSQL, Redis, backend, frontend, OpenSearch |
| `docker-compose.dev.yml` | Development overrides (hot reload, debug) |
| `docker-compose.prod.yml` | Production overrides (no dev tools, hardened) |
| `docker-compose.test.yml` | Test environment (isolated DB, in-memory Redis) |
| `docker-compose.ci.yml` | CI-specific configuration |
| `docker-compose.caddy.yml` | Caddy reverse proxy addition |
| `docker-compose.opensearch-dev.yml` | OpenSearch development setup |
| `docker-compose.pitr.yml` | Point-in-time recovery setup |

### Kubernetes Manifests (`k8s/`)

| File | Purpose |
|------|---------|
| `k8s/namespace.yaml` | Namespace definition |
| `k8s/backend.yaml` | Backend Deployment + Service |
| `k8s/frontend.yaml` | Frontend Deployment + Service |
| `k8s/worker.yaml` | Background worker Deployment |
| `k8s/postgres.yaml` | PostgreSQL StatefulSet + PVC |
| `k8s/redis.yaml` | Redis Deployment + Service |
| `k8s/ingress.yaml` | Ingress rules |
| `k8s/configmap.yaml` | Configuration |
| `k8s/secret.example.yaml` | Secret template |
| `k8s/network-policy.yaml` | Network policies |
| `k8s/kustomization.yaml` | Kustomize base |
| `k8s/overlays/managed-db/` | Managed database overlay (removes Postgres) |

### Helm Chart (`helm/`)

| File | Purpose |
|------|---------|
| `helm/securi/Chart.yaml` | Chart metadata |
| `helm/securi/values.yaml` | Default values |
| `helm/securi/values-managed-db.yaml` | Managed DB profile |
| `helm/securi/values-ingress.yaml` | Ingress profile |
| `helm/securi/templates/_helpers.tpl` | Template helpers |
| `helm/securi/templates/backend.yaml` | Backend template |
| `helm/securi/templates/frontend.yaml` | Frontend template |
| `helm/securi/templates/worker.yaml` | Worker template |
| `helm/securi/templates/postgresql.yaml` | PostgreSQL template |
| `helm/securi/templates/redis.yaml` | Redis template |
| `helm/securi/templates/ingress.yaml` | Ingress template |
| `helm/securi/templates/configmap.yaml` | ConfigMap template |
| `helm/securi/templates/secret.yaml` | Secret template |
| `helm/securi/templates/backup-pvc.yaml` | Backup PVC template |

### CI/CD (`.github/workflows/`)

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Full CI pipeline |
| `.github/workflows/release.yml` | Release workflow |

**CI Pipeline Jobs:**
1. `backend-unit` — Unit tests (no DB)
2. `backend-integration` — Full tests (PG + Redis)
3. `backend-lint` — Ruff linting
4. `backend-security` — Bandit security scan
5. `agent-test` — Agent tests
6. `frontend-test` — Unit tests + typecheck
7. `frontend-lint` — ESLint + build
8. `e2e-smoke` — Playwright smoke tests
9. `e2e-lab` — Full SOC lab E2E
10. `docker-build` — Docker image build
11. `container-scan` — Trivy vulnerability scan
12. `compose-smoke` — Docker Compose smoke test
13. `load-smoke` — k6 load test

### Deployment Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `scripts/deploy-linux.sh` | Linux VPS deployment |
| `scripts/deploy-windows-lan.ps1` | Windows LAN deployment |
| `scripts/start-infra.ps1` | Start infrastructure services |
| `scripts/dev-stop.ps1` | Stop development environment |
| `scripts/dev-windows.ps1` | Windows development startup |
| `scripts/compose-smoke.sh` / `.ps1` | Docker Compose smoke test |
| `scripts/compose-smoke.ps1` | Windows Docker Compose smoke |
| `scripts/demo-setup.sh` / `.ps1` | Demo environment setup |
| `scripts/validate-demo-flow.sh` / `.ps1` | Demo flow validation |
| `scripts/run-tests.ps1` | Test runner |
| `scripts/run-e2e.ps1` | E2E test runner |
| `scripts/smoke-api.ps1` | API smoke test |
| `scripts/verify-local.ps1` | Local environment verification |
| `scripts/ensure-docker-env.ps1` | Docker environment setup |
| `scripts/agent-install-help.ps1` | Agent installation helper |
| `scripts/open-firewall.ps1` | Firewall configuration |
| `scripts/pilot-harden.ps1` | Pilot environment hardening |
| `scripts/helm-validate.sh` | Helm chart validation |
| `scripts/k8s-validate.sh` | Kubernetes manifest validation |
| `scripts/backup-postgres.sh` / `.ps1` | Database backup |
| `scripts/pitr-base-backup.sh` | PITR base backup |
| `scripts/pitr-check.sh` | PITR verification |
| `scripts/check-utf8.js` | UTF-8 encoding check |

### Load Tests (`loadtests/`)

| File | Purpose |
|------|---------|
| `loadtests/smoke.js` | k6 smoke test (auth + event ingestion) |
| `loadtests/README.md` | Load testing documentation |

### Deployment Config (`deploy/`)

| File | Purpose |
|------|---------|
| `deploy/Caddyfile` | Caddy reverse proxy configuration |
| `deploy/postgres-pitr.conf` | PostgreSQL PITR WAL configuration |
| `deploy/cert-manager/cluster-issuer.yaml` | cert-manager Let's Encrypt issuer |

### Documentation (`docs/`)

Member 4 authored/maintains these documentation files:

| Document | Purpose |
|----------|---------|
| `docs/DEPLOYMENT.md` | Complete deployment guide |
| `docs/HELM.md` | Helm chart documentation |
| `docs/KUBERNETES.md` | Kubernetes deployment guide |
| `docs/KUBERNETES_INGRESS.md` | Ingress + TLS setup |
| `docs/VPS_DEPLOY.md` | VPS deployment handoff |
| `docs/BACKUP_AUTOMATION.md` | Automated backup setup |
| `docs/PITR_RUNBOOK.md` | Point-in-time recovery runbook |
| `docs/PRODUCTION_SECURITY.md` | Pre-deployment security checklist |
| `docs/HEALTH_PROBES.md` | Liveness/readiness probe setup |

---

## 3. Architecture / Design

### Docker Compose Network Topology

```
┌─────────────────────────────────────────────────────┐
│                  securi-frontend (bridge)             │
│  ┌──────────────┐                                   │
│  │   Frontend    │                                   │
│  │   (Next.js)   │                                   │
│  └──────┬───────┘                                   │
│         │                                            │
├─────────┼───────────────────────────────────────────┤
│         │  securi-backend (bridge)                   │
│  ┌──────▼───────┐    ┌──────────────┐              │
│  │   Backend     │◄──►│   Worker      │              │
│  │   (FastAPI)   │    │   (Jobs)      │              │
│  └──────┬───────┘    └──────────────┘              │
│         │                                            │
├─────────┼───────────────────────────────────────────┤
│         │  securi-data (bridge)                      │
│  ┌──────▼───────┐    ┌──────────────┐              │
│  │  PostgreSQL   │    │    Redis      │              │
│  │  (primary)    │    │  (queue+pub)  │              │
│  └──────────────┘    └──────────────┘              │
│  ┌──────────────┐                                   │
│  │  OpenSearch   │                                   │
│  │  (optional)   │                                   │
│  └──────────────┘                                   │
└─────────────────────────────────────────────────────┘
```

### CI/CD Pipeline Flow

```
Push to main/master
    │
    ├── backend-unit (pytest, no DB)
    ├── backend-integration (pytest + PG + Redis)
    ├── backend-lint (ruff)
    ├── backend-security (bandit)
    ├── agent-test (pytest)
    ├── frontend-test (vitest + tsc)
    ├── frontend-lint (eslint + build)
    │
    └── After all pass:
        ├── docker-build (backend + frontend images)
        ├── container-scan (trivy)
        ├── compose-smoke
        ├── e2e-smoke (playwright)
        └── load-smoke (k6)
```

### Kubernetes Deployment Architecture

```
Namespace: securi
├── Deployment/backend (2 replicas)
├── Deployment/frontend (2 replicas)
├── Deployment/worker (1 replica)
├── StatefulSet/postgresql (1 replica, PVC)
├── Deployment/redis (1 replica)
├── Service/backend
├── Service/frontend
├── Service/postgresql
├── Service/redis
├── Ingress/securi
├── ConfigMap/securi-config
├── Secret/securi-secrets
└── NetworkPolicy/*
```

---

## 4. Important Implementation Details

- **Health checks** on all services (liveness + readiness probes)
- **Resource limits** defined in K8s manifests and Helm values
- **Persistent volumes** for PostgreSQL and OpenSearch data
- **Secret management** via Kubernetes Secrets or environment variables
- **Rolling updates** with zero-downtime deployment
- **Network policies** restrict inter-service communication
- **PITR** via PostgreSQL WAL archiving + base backups

---

## 5. Technologies Used

| Technology | Purpose |
|-----------|---------|
| Docker | Container runtime |
| Docker Compose | Multi-container orchestration |
| Kubernetes | Container orchestration (production) |
| Helm 3 | Kubernetes package manager |
| Kustomize | Kubernetes manifest customization |
| GitHub Actions | CI/CD automation |
| Playwright | E2E testing |
| k6 | Load testing |
| Trivy | Container vulnerability scanning |
| Ruff | Python linting |
| Bandit | Python security scanning |
| Caddy | Reverse proxy with auto-TLS |
| PostgreSQL 16 | Database |
| Redis 7 | Cache + queue + pub/sub |

---

## 6. Testing

### Running Tests

```bash
# Docker Compose smoke test
chmod +x scripts/compose-smoke.sh && ./scripts/compose-smoke.sh

# Kubernetes validation
chmod +x scripts/k8s-validate.sh && ./scripts/k8s-validate.sh

# Helm validation
chmod +x scripts/helm-validate.sh && ./scripts/helm-validate.sh

# Load test (requires running backend)
k6 run loadtests/smoke.js

# Full CI pipeline locally
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d
# Run all test suites...
docker compose -f docker-compose.yml -f docker-compose.test.yml down
```

### Test Organization

| Suite | Framework | Count | Runs In |
|-------|-----------|-------|---------|
| Backend unit | pytest | 65+ | CI (no DB) |
| Backend integration | pytest | 36 | CI (PG + Redis) |
| Backend perf | pytest | 5 | CI (PG + Redis) |
| Backend unit modules | pytest | 3 | CI (no DB) |
| Agent | pytest | 67 | CI |
| Frontend unit | Vitest | 19 | CI |
| Frontend E2E | Playwright | 7 | CI (full stack) |
| Load | k6 | 1 | CI (full stack) |

---

## 7. Screenshots / Diagrams for Report

| Screenshot/Diagram | Description |
|-------------------|-------------|
| Docker Compose up | All services starting with health checks |
| GitHub Actions CI | Pipeline running all 13 jobs |
| Kubernetes dashboard | Deployments, services, pods in namespace |
| Helm values | Configuration profiles |
| Load test results | k6 output showing throughput and latency |
| PITR recovery | Restoring database to specific point in time |

---

## 8. Possible Viva Questions

### Deployment
1. **Q: Why Docker Compose for development and Kubernetes for production?**
   A: Docker Compose is simpler for local dev — one command starts everything. Kubernetes provides auto-scaling, self-healing, rolling updates for production.

2. **Q: How do you handle secrets in production?**
   A: Kubernetes Secrets (encrypted at rest), environment variables, never committed to repo. `.env.example` provides template without real values.

3. **Q: What is the CI/CD pipeline structure?**
   A: 13 jobs across 4 stages: lint/security, unit tests, integration tests, E2E/load. All must pass before merge. Docker images built and scanned on main branch.

### Testing
4. **Q: How do you ensure test coverage across the stack?**
   A: Separate test suites for each component: backend (unit + integration), agent (unit), frontend (unit + E2E), load (k6). CI runs all suites on every PR.

5. **Q: What does the E2E test cover?**
   A: Full SOC lab scenario: login, alert investigation, offense promotion, maintenance windows, threat intel, simulation. Uses Playwright with real backend.

### Operations
6. **Q: How do you perform zero-downtime deployments?**
   A: Kubernetes rolling update strategy with readiness probes. New pods must pass health check before old pods are terminated.

7. **Q: How does PITR work?**
   A: PostgreSQL WAL archiving to S3/local. Base backup + WAL replay to restore to any point in time. Runbook in `docs/PITR_RUNBOOK.md`.
