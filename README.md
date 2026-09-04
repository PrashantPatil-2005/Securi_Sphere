# Securi Sphere — A SIEM That Tells a Story

A lightweight Security Information and Event Management platform for small Linux fleets. Built as a final year engineering project, inspired by IBM QRadar's architecture.

---

## What is Securi Sphere?

Securi Sphere is a complete SOC (Security Operations Center) platform that monitors Linux servers in real time. It collects telemetry, detects threats, correlates attacks, groups them into offenses, and presents everything through a modern dashboard — giving analysts the full picture of an attack from first login to final resolution.

**Inspired by IBM QRadar** — the same 3-layer pipeline architecture used by enterprise SIEM tools costing $1M+, built as an open-source educational project.

---

## Features

### Telemetry Collection
- **Linux agent** — lightweight Python daemon collecting system logs, auth logs, CPU/memory/disk metrics, running processes, network connections
- **Offline buffer** — SQLite local buffer when network is down; auto-replays on reconnect
- **HMAC-SHA256 signing** — every request is cryptographically signed with nonce + timestamp validation

### Detection & Correlation
- **7 built-in detection rules** — failed logins, brute force, high CPU/memory/disk, service failure, agent offline
- **Extensible rule engine** — registry pattern; add new rules by registering a checker class
- **3 correlation algorithms** — sequence matching, co-occurrence, cross-host attack detection
- **Offense engine** — groups related alerts into offenses with confidence scoring
- **Attack timeline reconstruction** — chains events into chronological attack narratives

### Investigation
- **Alert investigation pane** — host details, related events, MITRE ATT&CK mapping, IOC lookup (VirusTotal)
- **MITRE ATT&CK heatmap** — visual matrix of technique coverage
- **UEBA (User & Entity Behavior Analytics)** — anomaly detection with z-score thresholding
- **AI Security Assistant** — local-first copilot for alert explanation, NL search, investigation summaries

### Operations
- **Real-time WebSocket updates** — live feed of alerts, offenses, host status changes
- **Tamper-evident audit log** — SHA-256 hash chain integrity verification
- **RBAC** — admin, analyst, viewer roles with enforced permissions
- **MFA** — TOTP-based multi-factor authentication
- **Session management** — concurrent session limits, refresh token rotation, session revocation
- **Rate limiting** — login brute-force protection with Retry-After headers
- **Incident management** — offense → incident promotion with notes and workflow

### Dashboard
- **SOC dashboard** — KPI cards, active threats, severity distribution, host risk, live feed
- **24 dedicated pages** — alerts, offenses, incidents, MITRE, UEBA, hosts, events, settings, reports
- **Dark mode** — optimized SOC aesthetic with glass panels and ambient gradient
- **Virtualized lists** — performant rendering of thousands of alerts/events

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SECURI PLATFORM                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    HTTPS/JSON     ┌──────────────┐    WebSocket     │
│  │  Linux    │ ──────────────▶  │   FastAPI     │ ◀────────────▶  │
│  │  Agent    │  (HMAC-signed)   │   Backend     │   (real-time)   │
│  │  (Python) │                  │   (Python)    │                 │
│  └──────────┘                  └──────┬───────┘                 │
│       │                               │                          │
│       │  heartbeat (30s)              │  SQL (async)             │
│       │  metrics (30s)                ▼                          │
│       │  logs (10s)            ┌──────────────┐                  │
│       │                        │  PostgreSQL   │                  │
│       ▼                        │  (primary +   │                  │
│  ┌──────────┐                  │   replica)    │                  │
│  │  SQLite   │                 └──────────────┘                  │
│  │  (offline │                        │                          │
│  │  buffer)  │                 ┌──────┴───────┐                 │
│  └──────────┘                  │    Redis      │                 │
│                                │  (queue +     │                 │
│                                │   pub/sub)    │                 │
│                                └──────────────┘                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Next.js Dashboard                          │  │
│  │  Alerts • Offenses • Incidents • MITRE • UEBA • Hosts       │  │
│  │  Events • Settings • Reports • AI Assistant                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full pipeline map.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + SQLAlchemy (async) + PostgreSQL |
| Frontend | Next.js 14 + TypeScript + TailwindCSS |
| Agent | Python + requests + SQLite offline buffer |
| Real-time | WebSocket + Redis pub/sub |
| Cache | Redis (job queue + session state) |
| Search | PostgreSQL (default) + OpenSearch (optional) |
| Auth | JWT (HS256/RS256) + HttpOnly cookies + MFA (TOTP) |
| Agent Auth | HMAC-SHA256 + nonce + timestamp validation |

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Backend and agent |
| Node.js | 20+ | Frontend |
| Docker | latest | PostgreSQL, Redis, optional OpenSearch |
| Docker Compose | v2+ | Multi-container orchestration |

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repository-url>
cd securi-sphere
cp .env.example .env
```

Edit `.env` and set at minimum:
- `POSTGRES_PASSWORD` — database password
- `JWT_SECRET` — random secret for JWT signing (generate with `openssl rand -base64 48`)
- `DATABASE_URL` — connection string (default: `postgresql+asyncpg://securi:securi_dev@localhost:5432/securi`)

### 2. Start dependencies

```bash
docker compose up -d
```

This starts PostgreSQL (port 5432) and Redis (port 6379).

### 3. Start backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Migrations run automatically on first startup.

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Access the platform

- **Dashboard:** http://localhost:3000
- **API docs:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health/ready

### 6. Register and explore

1. Open http://localhost:3000/register
2. Create your first account (first user becomes admin)
3. Add a host from the dashboard
4. Enroll an agent — see [docs/AGENT_INSTALL.md](docs/AGENT_INSTALL.md)
5. Run a simulation from the Simulation page to generate test telemetry

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_PASSWORD` | Yes | — | Database password |
| `JWT_SECRET` | Yes | — | JWT signing secret |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `REDIS_URL` | No | — | Redis connection (optional, defaults to in-memory) |
| `SERVER_URL` | No | `http://localhost:8000` | Backend public URL |
| `FRONTEND_URL` | No | `http://localhost:3000` | Frontend public URL |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `DEBUG` | No | `false` | Enable debug logging |
| `ALLOW_REGISTRATION` | No | `true` | Allow new user registrations |
| `ENABLE_SIMULATION` | No | `true` | Enable attack simulation |

### Frontend Configuration

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Agent Configuration

The agent is configured via its install script or config file. See [docs/AGENT_INSTALL.md](docs/AGENT_INSTALL.md).

### Production Toggles

| Variable | Default | Purpose |
|----------|---------|---------|
| `JOB_QUEUE_BACKEND` | `memory` | Set `redis` for durable background jobs |
| `WS_PUBSUB_BACKEND` | `memory` | Set `redis` for multi-instance WebSockets |
| `JWT_ALGORITHM` | `HS256` | Set `RS256` for asymmetric JWT with key pairs |
| `AGENT_MTLS_ENABLED` | `false` | Enable agent TLS certificate verification |
| `SEARCH_BACKEND` | `postgres` | Set `opensearch` with `OPENSEARCH_URL` for scale |
| `UEBA_ENABLED` | `true` | Enable anomaly detection scans |
| `VIRUSTOTAL_API_KEY` | — | Enable IOC enrichment in investigation |

Full production checklist: [docs/PRODUCTION_SECURITY.md](docs/PRODUCTION_SECURITY.md)

---

## Testing

### Backend (541 tests)

```bash
cd backend

# Unit tests (no DB required)
pytest tests/ -v --ignore=tests/integration -m "not integration"

# All tests (requires PostgreSQL + Redis via Docker)
pytest tests/ -v

# Security scan
bandit -r app --severity-level high
```

### Agent (67 tests)

```bash
cd agent
pytest tests/ -v
```

### Frontend (249 tests)

```bash
cd frontend

# Unit tests
npm run test:unit

# TypeScript check
npx tsc --noEmit

# Lint
npm run lint

# Build
npm run build

# E2E tests (requires Playwright)
npx playwright install chromium
npx playwright test
```

### Docker Integration

```bash
# Full stack with Docker
docker compose up -d --build

# Smoke test
./scripts/compose-smoke.sh  # Linux
.\scripts\compose-smoke.ps1  # Windows
```

---

## Security

- **JWT authentication** with HS256/RS256 support and refresh token rotation
- **RBAC** — admin, analyst, viewer roles enforced on all mutation endpoints
- **MFA** — TOTP-based multi-factor authentication
- **Rate limiting** — login brute-force protection with Retry-After headers
- **HMAC-SHA256** — agent request signing with nonce and timestamp validation
- **Security headers** — X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy
- **CORS** — whitelist-only origin validation
- **Tamper-evident audit log** — SHA-256 hash chain integrity
- **Session management** — concurrent session limits, revocation on logout
- **Password security** — bcrypt hashing, complexity requirements

Full security checklist: [docs/PRODUCTION_SECURITY.md](docs/PRODUCTION_SECURITY.md)

---

## Demo Mode

Enable demo mode for a pre-configured demonstration environment:

```bash
# In .env
DEMO_MODE=true
```

This creates a demo admin account:
- **Email:** demo@securi.local
- **Password:** Demo1234!

Demo mode includes pre-seeded detection rules, sample hosts, and attack simulation scenarios.

For a full walkthrough: [docs/SOC_LAB_SCENARIO.md](docs/SOC_LAB_SCENARIO.md)

---

## Project Structure

```
Securi_Sphere/
├── agent/                    # Member 3: Linux agent & telemetry
│   ├── agent/                #   Collector, sender, buffer, integrity
│   └── tests/                #   67 agent tests
├── backend/                  # Member 1: Core SIEM / backend
│   ├── app/
│   │   ├── pipeline/         #   Ingestion: validation, normalization, dedup
│   │   ├── services/         #   Detection, correlation, offense, UEBA, auth
│   │   │   ├── detection.py  #     Extensible rule engine (registry pattern)
│   │   │   ├── correlation/  #     Sequence, co-occurrence, cross-host
│   │   │   ├── offense_engine.py #  Alert grouping into offenses
│   │   │   ├── timeline.py   #     Attack chain reconstruction
│   │   │   └── ueba.py       #     UEBA anomaly detection
│   │   ├── models/           #   34 SQLAlchemy models
│   │   ├── routers/          #   41 API routers
│   │   └── middleware/        #   Rate limiting, security headers, timeouts
│   └── tests/                #   541 unit + integration tests
├── frontend/                 # Member 2: SOC dashboard
│   ├── app/(dashboard)/      #   28+ pages (alerts, offenses, MITRE, ...)
│   ├── components/           #   130+ React components
│   └── lib/                  #   API client, hooks, WebSocket
├── deploy/                   # Member 4: Deployment config
├── helm/                     # Member 4: Helm chart
├── k8s/                      # Member 4: Kubernetes manifests
├── loadtests/                # Member 4: k6 load tests
├── scripts/                  # Member 4: 26 deployment scripts
├── docs/
│   ├── architecture/         #   Cross-cutting architecture
│   ├── member-1-core-siem/   #   Member 1's documentation index
│   ├── member-2-frontend/    #   Member 2's documentation index
│   ├── member-3-agent/       #   Member 3's documentation index
│   └── member-4-deployment-testing/ # Member 4's documentation index
├── CONTRIBUTIONS.md          # Team contribution table
└── PROJECT_CONTEXT.md        # Full project context
```

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend routers | 37 |
| API endpoints | 183 |
| Database models | 34 |
| Alembic migrations | 24 |
| Frontend pages | 24 |
| UI components | 42+ |
| Backend tests | 541 |
| Agent tests | 67 |
| Frontend tests | 249 |
| Total tests | 857 |

---

## Deployment

### Docker Compose (recommended)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes

See [docs/KUBERNETES.md](docs/KUBERNETES.md) and [k8s/](k8s/) manifests.

### Helm

See [docs/HELM.md](docs/HELM.md) and [helm/](helm/) chart.

### Render

See `render.yaml` for Render.com deployment configuration.

### Linux VPS

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and `scripts/deploy-linux.sh`.

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/API.md](docs/API.md) | REST API reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline architecture |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment |
| [docs/AGENT_INSTALL.md](docs/AGENT_INSTALL.md) | Agent setup guide |
| [docs/AGENT_MTLS.md](docs/AGENT_MTLS.md) | Agent mTLS hardening |
| [docs/PRODUCTION_SECURITY.md](docs/PRODUCTION_SECURITY.md) | Security checklist |
| [docs/KUBERNETES.md](docs/KUBERNETES.md) | K8s deployment |
| [docs/HELM.md](docs/HELM.md) | Helm chart |
| [docs/SOC_LAB_SCENARIO.md](docs/SOC_LAB_SCENARIO.md) | Attack lab walkthrough |
| [docs/GUIDE_DEMO.md](docs/GUIDE_DEMO.md) | 5-minute demo guide |
| [CONTRIBUTIONS.md](CONTRIBUTIONS.md) | Team contributions and responsibility map |

---

## License

MIT
