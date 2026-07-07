# Mini SIEM (Securi)

A lightweight security monitoring platform inspired by Wazuh, built for small Linux environments (4-5 systems).

## Stack

- Frontend: Next.js 14, TypeScript, TailwindCSS
- Backend: FastAPI, Python 3.10+
- Database: PostgreSQL 16
- Agent: Python (systemd service)
- Real-time: WebSockets

## Quick Start

### One-command dev (Windows)

```powershell
cd c:\Users\Prash\Desktop\Securi
.\scripts\start-infra.ps1          # Postgres + Redis only (first time or after reboot)
.\scripts\dev-windows.ps1
```

Stop dev servers: `.\scripts\dev-stop.ps1`

Verify Postgres, Redis, and API health:

```powershell
.\scripts\verify-local.ps1
.\scripts\run-tests.ps1 -Quick          # fast backend smoke
.\scripts\run-tests.ps1 -IntegrationOnly  # all integration tests
.\scripts\run-e2e.ps1                   # Playwright E2E (stack must be running)
```

**Demo / presentation mode** (faster page loads, no dev compilation):

```powershell
.\scripts\dev-windows.ps1 -Demo
```

**LAN access from other devices** on the same network:

```powershell
.\scripts\dev-windows.ps1 -LanIp 192.168.0.105
```

Open Windows Firewall for TCP ports 3000 and 8000.

### Manual start

#### 1. Start PostgreSQL

```powershell
cd c:\Users\Prash\Desktop\Securi
docker compose up -d
```

### 2. Backend

```powershell
cd backend
copy ..\.env.example .env
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000

Dev login (seeded in development): `admin@test.local` / `testpass123`

### LAN pilot deploy (Windows + Docker)

```powershell
.\scripts\deploy-windows-lan.ps1 -LanIp 192.168.0.105
```

After registering admin: `.\scripts\pilot-harden.ps1`

Agent install on Ubuntu VM:

```powershell
.\scripts\agent-install-help.ps1 -ServerUrl http://192.168.0.105:8000 -EnrollToken YOUR_TOKEN
```

See [docs/VPS_DEPLOY.md](docs/VPS_DEPLOY.md) for Linux VPS deployment and backups.

### API smoke test

With backend running:

```powershell
.\scripts\smoke-api.ps1
```

### 4. First Login

1. Open http://localhost:3000/register
2. Create an account (first user becomes admin)
3. Log in and add a host from the Hosts page

### 5. Install Agent (Ubuntu VM)

See **[docs/AGENT_INSTALL.md](docs/AGENT_INSTALL.md)** for the full guide (add host → enroll → install → verify).

Quick install:

```bash
curl -fsSL http://YOUR_SERVER_IP:8000/install.sh | sudo bash -s -- --token ENROLL_TOKEN --server http://YOUR_SERVER_IP:8000
```

## Documentation

### Getting started
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Linux hosting, HTTPS, agents, demo walkthrough
- [docs/GUIDE_DEMO.md](docs/GUIDE_DEMO.md) — 5-minute demo (simulation-only or with agent)
- [docs/SOC_LAB_SCENARIO.md](docs/SOC_LAB_SCENARIO.md) — Multi-stage attack lab for portfolio
- [docs/AGENT_INSTALL.md](docs/AGENT_INSTALL.md) — Add hosts, install agents, monitoring
- [docs/ROADMAP_STATUS.md](docs/ROADMAP_STATUS.md) — Completion scorecard

### Platform
- [docs/API.md](docs/API.md) — API reference
- [docs/SCHEMA.md](docs/SCHEMA.md) — Database schema
- [docs/SIEM_PIPELINE_ARCHITECTURE.md](docs/SIEM_PIPELINE_ARCHITECTURE.md) — QRadar-style 3-layer pipeline
- [docs/PRODUCTION_SECURITY.md](docs/PRODUCTION_SECURITY.md) — Production env checklist
- [docs/DB_ENCRYPTION_AT_REST.md](docs/DB_ENCRYPTION_AT_REST.md) — Database encryption at rest
- [docs/BACKUP_AUTOMATION.md](docs/BACKUP_AUTOMATION.md) — Scheduled Postgres backups
- [docs/PITR_RUNBOOK.md](docs/PITR_RUNBOOK.md) — Point-in-time recovery
- [docs/KUBERNETES.md](docs/KUBERNETES.md) — Kubernetes manifests (`k8s/`)
- [docs/HELM.md](docs/HELM.md) — Helm chart (`helm/securi/`)
- [docs/KUBERNETES_INGRESS.md](docs/KUBERNETES_INGRESS.md) — Ingress + cert-manager TLS
- [docs/HEALTH_PROBES.md](docs/HEALTH_PROBES.md) — Liveness / readiness / startup probes
- [docs/GRACEFUL_SHUTDOWN.md](docs/GRACEFUL_SHUTDOWN.md) — SIGTERM drain and rollouts
- [docs/CIRCUIT_BREAKERS.md](docs/CIRCUIT_BREAKERS.md) — External dependency circuit breakers
- [docs/REQUEST_TIMEOUTS.md](docs/REQUEST_TIMEOUTS.md) — API and outbound HTTP timeouts
- [docs/CONNECTION_POOLING.md](docs/CONNECTION_POOLING.md) — Postgres connection pool tuning
- [docs/WRAP_UP.md](docs/WRAP_UP.md) — Feature checklist and handoff

### Features
- [docs/OIDC_SSO.md](docs/OIDC_SSO.md) — SSO login
- [docs/USER_PROVISIONING.md](docs/USER_PROVISIONING.md) — Invites and team management
- [docs/THREAT_INTEL.md](docs/THREAT_INTEL.md) — Reference sets and building blocks
- [docs/UEBA.md](docs/UEBA.md) — User behavior analytics
- [docs/PLAYBOOKS_SOAR.md](docs/PLAYBOOKS_SOAR.md) — SOAR webhooks
- [docs/NOTIFICATION_RULES.md](docs/NOTIFICATION_RULES.md) — Alert routing rules
- [docs/MITRE_HEATMAP.md](docs/MITRE_HEATMAP.md) — ATT&CK coverage
- [docs/COMPLIANCE_REPORTS.md](docs/COMPLIANCE_REPORTS.md) — Compliance exports
- [docs/EXECUTIVE_REPORTS.md](docs/EXECUTIVE_REPORTS.md) — Executive summaries
- [docs/ALERTS_TABLE.md](docs/ALERTS_TABLE.md) — Alerts UI
- [docs/SAVED_SEARCHES_DASHBOARDS.md](docs/SAVED_SEARCHES_DASHBOARDS.md) — Saved searches
- [docs/OPENSEARCH_AT_SCALE.md](docs/OPENSEARCH_AT_SCALE.md) — Search scaling
- [docs/AI_AND_UX_ROADMAP.md](docs/AI_AND_UX_ROADMAP.md) — AI copilot features
- [docs/AGENT_MTLS.md](docs/AGENT_MTLS.md) — Agent mTLS enrollment

### Dev infrastructure
- `docker-compose.dev.yml` — Postgres + Redis only (no OpenSearch) for native dev
- `docker-compose.ci.yml` — Postgres + Redis + backend for compose smoke tests
- `scripts/demo-setup.ps1` / `scripts/demo-setup.sh` — One-command demo prep
- `scripts/compose-smoke.ps1` / `scripts/compose-smoke.sh` — Verify Docker stack health

### Deploy on Linux (quick)

```bash
chmod +x scripts/deploy-linux.sh
./scripts/deploy-linux.sh YOUR_SERVER_IP
# Dashboard: http://YOUR_SERVER_IP:3000
```


## Advanced Features

- MITRE ATT&CK mapping and matrix view
- Correlation engine with confidence scoring
- Attack timeline reconstruction
- Host threat scores and network topology
- Incident management, audit log, attack simulation
- Agent integrity monitoring (hash change detection)
- Windows event forwarder API, VirusTotal IOC lookup, bulk alert actions
- Redis job queue/worker, event partitioning, RS256 JWT, Playwright E2E

## AI Security Assistant

Securi includes a **local-first AI copilot** — no API key required for core features.

- **Floating assistant** (bottom-right) — explain alerts, suggest investigation steps, SIEM syntax help
- **Ask AI about this alert** — in the investigation pane, pre-fills alert context
- **Auto investigation summary** — `GET /api/v1/alerts/{id}/ai-summary`
- **Natural language search** — Search page converts plain English to SIEM queries
- **Offense AI brief** — plain-English narrative on the Offenses detail panel
- **Command palette** — `Ctrl+K` / `⌘K` for quick navigation and actions

### Configuration

```env
AI_ASSISTANT_ENABLED=true
AI_PROVIDER=local          # local | openai | anthropic
OPENAI_API_KEY=          # optional — richer answers when set
ANTHROPIC_API_KEY=       # optional alternative LLM
```

Without an API key, rule-based templates handle chat, NL search, and summaries. Set `AI_PROVIDER=openai` and `OPENAI_API_KEY` for LLM-enhanced responses (falls back to local on failure).

See [docs/AI_AND_UX_ROADMAP.md](docs/AI_AND_UX_ROADMAP.md) for the full feature plan.

## Dashboard Pages

Overview, Hosts, Events, Alerts, Metrics, MITRE, Timeline, Incidents, Network, Rules, Audit, Simulation, Reports, Search

## Database Migration

Schema is managed by **Alembic**. On startup the backend runs `alembic upgrade head` automatically.

```powershell
cd backend
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\alembic upgrade head
```

See `backend/alembic/README.md` for revision chain and stamping existing databases.
