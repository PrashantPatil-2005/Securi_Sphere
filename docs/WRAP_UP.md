# SecuriSphere — implementation wrap-up

**Status: in-scope pilot complete (100%)**  
Last updated: July 2026

This document summarizes what was built, how to run it, and what remains intentionally out of scope.

---

## What you have

SecuriSphere is a **mini-SIEM** for small Linux fleets (4–10 hosts): collection, detection, correlation, offenses, investigation, and a modern SOC dashboard.

### Architecture (QRadar-style 3 layers)

| Layer | Capability |
|-------|------------|
| **1 — Collection** | Linux agent events, network flows, Windows event forwarder spike, host metrics |
| **2 — Processing** | Detection rules, correlation engine, offense grouping, Redis job queue + worker, WebSocket pub/sub |
| **3 — Search** | SIEM query language, global search, optional OpenSearch backend |
| **Console** | Next.js dashboard: alerts, offenses, MITRE, timeline, incidents, rules, reports, simulation |

See [SIEM_PIPELINE_ARCHITECTURE.md](SIEM_PIPELINE_ARCHITECTURE.md) for the full pipeline map.

---

## Feature checklist (completed)

### Platform core
- [x] FastAPI backend + PostgreSQL + optional Redis/OpenSearch
- [x] Next.js 14 dashboard with real-time WebSockets
- [x] Python Linux agent (enrollment, heartbeat, log collection)
- [x] Alembic migrations `001` → `005` (baseline, indexes, constraints, event partitions, agent cert)
- [x] Docker Compose (Postgres, Redis, backend, worker, frontend)

### Detection & response
- [x] Alert investigation pane with IOC lookup (VirusTotal)
- [x] Bulk alert actions (status, assignee)
- [x] Correlation rule CRUD
- [x] Offense engine + **offense → incident promotion** (API + UI)
- [x] MITRE mapping, attack timelines, host threat scores
- [x] In-app notification history

### Operations & scale
- [x] Redis job queue + background worker
- [x] Redis WebSocket pub/sub (multi-instance ready)
- [x] Event table partitioning (optional `EVENT_PARTITIONING_ENABLED`)
- [x] Partition auto-drop on retention cleanup
- [x] RS256 JWT support (`JWT_ALGORITHM=RS256`)
- [x] Agent mTLS docs + cert fingerprint enrollment API

### Portfolio / lab
- [x] Multi-stage attack simulation (`multi_stage_attack`)
- [x] SOC lab walkthrough — [SOC_LAB_SCENARIO.md](SOC_LAB_SCENARIO.md)
- [x] Windows event forwarder spike (`POST /api/v1/agent/windows-events`)

### Quality gates (CI)
- [x] Backend pytest (unit + integration with Postgres)
- [x] Frontend lint, TypeScript, build
- [x] Playwright smoke (login/register pages)
- [x] Playwright SOC lab flow (register → host → simulation → alerts)
- [x] k6 API load smoke

---

## Quick start (local)

```powershell
# 1. Infrastructure
docker compose up -d

# 2. Backend
cd backend
copy ..\.env.example .env
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd ..\frontend
npm install
npm run dev
```

1. Register at http://localhost:3000/register (first user = admin)
2. Add a host → enroll agent — [AGENT_INSTALL.md](AGENT_INSTALL.md)
3. Run **Attack Simulation** for a demo offense chain — [SOC_LAB_SCENARIO.md](SOC_LAB_SCENARIO.md)

---

## Production toggles

| Variable | Default | Enable for |
|----------|---------|------------|
| `EVENT_PARTITIONING_ENABLED` | `false` | Large event volume / retention |
| `JWT_ALGORITHM` | `HS256` | `RS256` + key pair for prod |
| `JOB_QUEUE_BACKEND` | `memory` | `redis` + worker service |
| `WS_PUBSUB_BACKEND` | `memory` | `redis` for horizontal scale |
| `VIRUSTOTAL_API_KEY` | empty | IOC enrichment in investigation |
| `AGENT_MTLS_ENABLED` | `false` | Agent TLS cert verification |
| `ALLOW_REGISTRATION` | `true` | Set `false` after bootstrap |

Full checklist: [PRODUCTION_SECURITY.md](PRODUCTION_SECURITY.md)

---

## Testing

```powershell
# Backend (needs Postgres — use docker compose)
cd backend
pytest tests/ -v

# Frontend E2E smoke (frontend only)
cd frontend
npm run test:e2e

# Full SOC lab E2E (backend + Postgres + frontend)
# Terminal 1: docker compose + uvicorn
# Terminal 2:
cd frontend
$env:E2E_FULL_STACK="1"
npx playwright test e2e/lab-flow.spec.ts
```

---

## Intentionally not built (enterprise / separate projects)

| Item | Reason |
|------|--------|
| Native Windows agent / Sysmon on endpoint | Separate product surface |
| OIDC / SAML SSO | Identity-provider integration project |
| HashiCorp Vault / AWS Secrets Manager | Deployment-specific infra |
| Packet capture / Wireshark integration | Forensics appliance scope |
| Multi-tenancy | Architecture redesign |
| Full Splunk/QRadar/Wazuh protocol parity | Different product category |

---

## Suggested demo narrative (LinkedIn / portfolio)

1. **Collect** — enroll a Linux VM; show live events
2. **Detect** — run `brute_force` or `multi_stage_attack` simulation
3. **Correlate** — open offense, promote to incident
4. **Investigate** — alert pane, timeline, VirusTotal IOC (if key set)
5. **Operate** — System Health pipeline view, bulk alert triage, notification history

---

## Key documentation index

| Doc | Purpose |
|-----|---------|
| [README.md](../README.md) | Quick start |
| [API.md](API.md) | REST reference |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Linux hosting + HTTPS |
| [AGENT_INSTALL.md](AGENT_INSTALL.md) | Agent enrollment |
| [AGENT_MTLS.md](AGENT_MTLS.md) | mTLS agent hardening |
| [SOC_LAB_SCENARIO.md](SOC_LAB_SCENARIO.md) | Attack lab script |
| [ROADMAP_STATUS.md](ROADMAP_STATUS.md) | Completion scorecard |

---

**You are done with the in-scope pilot.** Enable production toggles, deploy with Docker or `deploy-linux.sh`, and use the SOC lab scenario for demos.
