# Mini SIEM (Securi)

A lightweight security monitoring platform inspired by Wazuh, built for small Linux environments (4-5 systems).

## Stack

- Frontend: Next.js 14, TypeScript, TailwindCSS
- Backend: FastAPI, Python 3.10+
- Database: PostgreSQL 16
- Agent: Python (systemd service)
- Real-time: WebSockets

## Quick Start

### 1. Start PostgreSQL

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

- docs/API.md - API reference
- docs/SCHEMA.md - Database schema
- docs/DEPLOYMENT.md - **Linux hosting, HTTPS, agents, and demo walkthrough**
- docs/SIEM_PIPELINE_ARCHITECTURE.md - **QRadar-style 3-layer pipeline map**
- docs/SOC_LAB_SCENARIO.md - **Multi-stage attack lab for portfolio**
- docs/PRODUCTION_SECURITY.md - **Production env checklist**
- docs/AGENT_INSTALL.md - **Add hosts, install agents, how monitoring works**
- docs/AGENT_MTLS.md - **Agent mTLS enrollment and cert fingerprints**
- docs/WRAP_UP.md - **Implementation complete — feature checklist and demo script**
- docs/ROADMAP_STATUS.md - **100% in-scope completion scorecard**

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

SecuriSphere includes a **local-first AI copilot** — no API key required for core features.

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
