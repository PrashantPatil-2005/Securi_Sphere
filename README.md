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
- docs/AGENT_INSTALL.md - **Add hosts, install agents, how monitoring works**

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

## Dashboard Pages

Overview, Hosts, Events, Alerts, Metrics, MITRE, Timeline, Incidents, Network, Rules, Audit, Simulation, Reports, Search

## Database Migration

If upgrading from an earlier version, run:

```powershell
cd backend
.\venv\Scripts\python -m app.services.migrate
```

Or restart the backend — migrations run automatically on startup.
