# Securi — Security Monitoring Platform

A lightweight SIEM (Security Information and Event Management) system for small Linux fleets. Built as a final year engineering project.

## What This Actually Is

This is a **backend-focused security monitoring platform** that:

1. **Collects** events from Linux agents (logs, metrics, network flows)
2. **Detects** threats using an extensible rule engine
3. **Correlates** events across hosts to find attack patterns
4. **Presents** a real-time SOC dashboard for investigation

It's inspired by IBM QRadar's 3-layer pipeline architecture. It's not QRadar — it's a learning project that implements the same concepts.

## Core Features (What Actually Works)

### Ingestion Pipeline
- Event batching (up to 100 events per request)
- HMAC-SHA256 request signing (prevents replay attacks)
- Nonce tracking (each request is single-use)
- Timestamp validation (rejects future/ancient events)
- Event normalization (canonical field extraction)
- Deduplication (fingerprint-based)
- SQLite offline buffer (agent retries when server is down)

### Detection Engine
Extensible rule registry — add new rule types by writing one class:
- Failed logins (threshold-based)
- Brute force (high-volume SSH failures)
- High CPU/Memory/Disk (metric threshold)
- Service failure (systemd events)
- Agent offline (heartbeat staleness)

### Correlation Engine
Three algorithms for detecting attack patterns:
- **Sequence matcher**: Ordered events (failed_login → success = brute force)
- **Co-occurrence matcher**: Related events in same window (service_stop + agent_disconnect)
- **Cross-host matcher**: Same attacker across multiple hosts (lateral movement)
- Confidence scoring with heuristics

### Agent
- Python systemd service
- Heartbeat every 30 seconds
- Log tailing with state tracking
- CPU/memory/disk metrics collection
- HMAC-signed requests
- SQLite offline buffer with exponential backoff
- One-line installer script

### Dashboard
- Real-time WebSocket feed
- Alert investigation pane (alert → related events → host → timeline)
- Bulk alert actions (investigate, resolve, close)
- SIEM query language (`host:web01 severity:critical`)
- Keyboard navigation (j/k/Enter/Space)
- Host status monitoring

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + SQLAlchemy (async) + PostgreSQL |
| Frontend | Next.js 14 + TypeScript + TailwindCSS |
| Agent | Python + requests + SQLite |
| Real-time | WebSocket + Redis pub/sub |
| Cache | Redis (job queue + session state) |

## Quick Start

```bash
# 1. Start PostgreSQL + Redis
docker compose up -d

# 2. Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Frontend
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:3000
API docs: http://localhost:8000/docs

## Project Structure

```
backend/
  app/
    pipeline/         # Ingestion pipeline (validation, normalization, dedup)
    services/
      detection.py    # Extensible rule engine (registry pattern)
      correlation/    # Three correlation algorithms
      offense_engine.py  # Alert grouping into offenses
      timeline.py     # Attack chain reconstruction
    models/           # 34 SQLAlchemy models
    routers/          # 39 FastAPI routers
    middleware/        # Rate limiting, security headers, timeouts
  tests/              # Backend test suite

frontend/
  app/(dashboard)/    # 28 dashboard pages
  components/         # 42 React components
  lib/                # API client, hooks, WebSocket

agent/
  agent/              # Python agent (sender, buffer, collectors)
  install.sh          # One-line installer
```

## How the Agent Works

1. Agent starts, loads config from `/etc/securi/config.json`
2. Sends heartbeat every 30s with agent hash (integrity check)
3. Tails syslog/auth.log for security events
4. Collects CPU/memory/disk metrics every 30s
5. Signs each request with HMAC-SHA256 (timestamp + nonce + body)
6. If server is unreachable, buffers to SQLite with exponential backoff
7. On reconnect, flushes buffer automatically

## How Detection Works

1. Events arrive via `POST /api/v1/agent/events`
2. Pipeline validates (timestamp, batch size, field lengths)
3. Normalizes event types (aliases → canonical names)
4. Deduplicates via fingerprint (host + timestamp + type + raw_log)
5. Runs detection rules against the host
6. If threshold exceeded, creates alert + broadcasts via WebSocket
7. Correlation engine evaluates event sequences across hosts

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# E2E tests
cd frontend
npx playwright test

# Load test
k6 run loadtests/smoke.js
```

## What I'd Improve Next

- [ ] User-defined correlation rules (UI editor)
- [ ] Event normalization for more log formats (syslog, journald, Windows Event Log)
- [ ] Performance benchmarking (events/second metrics)
- [ ] Network flow analysis (connection graph)
- [ ] Agent auto-update mechanism

## License

MIT
