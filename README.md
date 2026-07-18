# Securi — A SIEM That Tells a Story

A lightweight Security Information and Event Management platform for small Linux fleets. Built as a final year engineering project, inspired by IBM QRadar's architecture.

---

## The Story: A Day in the Life of an Attack

A company runs **20 Linux servers**. Securi is monitoring all of them. Nothing unusual — until now.

### Chapter 1 — The Agent Wakes Up

On every server, a lightweight Python agent is running. It collects system logs, authentication logs, CPU usage, memory usage, running processes, and network connections.

```
Jul 18 10:01:21 sshd: Failed password for root from 185.23.x.x
```

**Code:** `agent/agent/collector/events.py` — parses SSH failures, sudo usage, service events
**Code:** `agent/agent/collector/metrics.py` — collects CPU/memory/disk via psutil

### Chapter 2 — The Network Dies

The internet connection drops. Most projects lose the logs. The agent stores everything in a local SQLite database. Hours later, when the network returns, it uploads everything in order. Nothing is lost.

**Code:** `agent/agent/buffer.py` — SQLite offline buffer with `enqueue()`, `dequeue_all()`, `purge_stale()`

### Chapter 3 — Sending Securely

The agent signs every request with HMAC-SHA256. The signature covers the timestamp, a nonce, and the request body. If an attacker replays yesterday's packet, the server rejects it.

```
POST /api/v1/agent/events
Headers:
  X-Agent-Timestamp: 1689676881
  X-Agent-Nonce: a1b2c3d4
  X-Agent-Signature: sha256=...
```

**Code:** `agent/agent/sender.py` — `_sign()` computes HMAC, `Sender._post()` attaches headers

### Chapter 4 — The Gatekeeper

FastAPI receives the request. Before looking at events, it verifies the HMAC signature using constant-time comparison (prevents timing attacks). Checks the nonce (single-use, stored in DB). Validates the timestamp (rejects if >5 minutes old).

Only genuine, fresh requests pass.

**Code:** `backend/app/services/agent_auth.py` — `verify_agent_signature()`, `validate_agent_request()`
**Code:** `backend/app/dependencies_agent.py` — `get_authenticated_agent()` FastAPI dependency

### Chapter 5 — The Cleaner

Events enter the ingestion pipeline. The first question: "Have I seen this before?" A SHA-256 fingerprint is computed from host + timestamp + event type + raw log. Redis checks first (fast path), then PostgreSQL. Duplicates are discarded.

**Code:** `backend/app/services/ingest_dedup.py` — `event_fingerprint()`, `is_duplicate()`

### Chapter 6 — The Translator

Linux logs are messy. Ubuntu writes "Failed password". Another distro writes "Authentication failure". The normalizer converts them into a common format:

```json
{
  "host": "web-01",
  "user": "root",
  "type": "ssh_login_failure",
  "ip": "185.23.x.x",
  "severity": "high",
  "category": "authentication"
}
```

**Code:** `backend/app/pipeline/normalizer.py` — `normalize_event_type()`, `build_normalized_event()`
**Code:** `backend/app/pipeline/validator.py` — batch size, timestamp, field length validation

### Chapter 7 — Into the Database

The normalized event is stored in PostgreSQL. The Event model has 17 columns: UUID primary key, host foreign key, event type, severity, category, MITRE technique ID, source IP (INET), username, raw log, normalized event (JSONB), metadata (JSONB), and indexed timestamp.

**Code:** `backend/app/models/event.py` — `class Event(Base)` with all columns

### Chapter 8 — The Detective Arrives

The detection engine wakes up. It iterates every enabled rule, queries the database for matching conditions, and creates alerts when thresholds are exceeded.

Built-in rules:
- **Failed logins** — 5+ SSH failures in 5 minutes
- **Brute force** — 10+ SSH failures (supersedes failed logins)
- **High CPU/Memory/Disk** — metric threshold alerts
- **Service failure** — systemd service crash detection
- **Agent offline** — heartbeat staleness

**Code:** `backend/app/services/detection.py` — `RuleChecker` ABC + `@register_checker` registry pattern

### Chapter 9 — One Alert Isn't Enough

The correlation engine asks: "Is this related to anything else?" Three algorithms detect attack patterns:

1. **Sequence matching** — ordered events within a time window (e.g., failed login → success → sudo = brute force with privilege escalation)
2. **Co-occurrence** — related events appearing together regardless of order (e.g., service stop + agent disconnect = host compromise)
3. **Cross-host** — same attacker across multiple hosts (e.g., same IP fails SSH on 3 servers = lateral movement)

Each match gets a confidence score based on heuristics: base score + privilege escalation bonus + high-volume bonus + compressed timeline bonus.

**Code:** `backend/app/services/correlation/framework.py` — `SequenceMatcher`, `CoOccurrenceMatcher`, `CrossHostMatcher`
**Code:** `backend/app/services/correlation_engine.py` — engine loop evaluating rules against events

### Chapter 10 — Creating an Offense

Instead of flooding analysts with alerts, the system groups related activity into offenses. A 30-minute window clusters alerts from the same host or attack chain. Each offense gets a sequential number, related hosts, related users, and a timeline.

**Code:** `backend/app/services/offense_engine.py` — `find_or_create_offense()`, `link_alert_to_offense()`

### Chapter 11 — The Timeline

The offense page doesn't show random logs. It reconstructs the attack chain:

```
10:01  Failed Login
10:03  Failed Login
10:04  Successful Login
10:05  sudo executed
10:06  New user created
10:08  SSH outbound connection
```

A SHA-256 fingerprint deduplicates timelines. Confidence scoring uses: base 30 + failures × 5 + success bonus + privilege escalation bonus + compressed timeline bonus (max 100).

**Code:** `backend/app/services/timeline.py` — `build_timelines()`, `_chain_confidence()`

### Chapter 12 — The Dashboard Comes Alive

As soon as the offense is created, Redis publishes a message. WebSocket receives it. Every browser updates instantly — without refreshing. The SOC analyst sees the critical offense in real time.

**Code:** `backend/app/websocket/redis_pubsub.py` — `publish_ws_message()` via `securi:ws:broadcast` channel
**Code:** `backend/app/websocket/manager.py` — `ConnectionManager` with Redis pub/sub for multi-instance broadcast
**Code:** `frontend/lib/websocket.tsx` — client-side auto-reconnect, typed message handlers

### Chapter 13 — The Analyst

The analyst clicks the alert. They don't just see "CPU: 90%". They see:

- Host details and previous alerts
- Attack timeline reconstruction
- MITRE ATT&CK technique mapping
- Related events across the timeline
- IOC lookup panel (VirusTotal integration)
- AI assistant summary
- Risk score and investigation notes

**Code:** `frontend/app/(dashboard)/alerts/page.tsx` — alerts dashboard with virtual scrolling
**Code:** `frontend/components/AlertInvestigationPane.tsx` — full investigation drawer

### Chapter 14 — Resolution and Audit Trail

The analyst marks the offense as "True Positive" and resolves it. The platform stores who resolved it, when, why — and everything is recorded in a tamper-evident audit log with SHA-256 hash chaining (each entry's hash includes the previous entry's hash).

**Code:** `backend/app/models/audit.py` — `AuditLog` with chain_seq, prev_hash, entry_hash
**Code:** `backend/app/services/audit.py` — `log_audit()` with advisory lock + hash chain
**Code:** `backend/app/services/audit_chain.py` — `verify_audit_chain()` for integrity verification

---

## The Complete Pipeline

```
Linux Server
    |
    v
Agent (collector/events.py + metrics.py)
    |
    v
Offline Buffer (buffer.py)  <--- if network is down
    |
    v
HMAC Signing (sender.py)
    |
    v
Gatekeeper (agent_auth.py)  <--- verify HMAC, nonce, timestamp
    |
    v
Ingestion Pipeline (pipeline/ingestion.py)
    |
    +---> Deduplication (ingest_dedup.py)
    +---> Normalization (normalizer.py)
    +---> Storage (models/event.py)
    |
    v
Detection Engine (services/detection.py)
    |
    v
Correlation Engine (services/correlation/framework.py)
    |
    v
Offense Engine (services/offense_engine.py)
    |
    v
Timeline Reconstruction (services/timeline.py)
    |
    +---> Redis Pub/Sub (websocket/redis_pubsub.py)
    +---> WebSocket (websocket/manager.py)
    |
    v
Dashboard (frontend/)
    |
    v
Analyst Investigation (components/AlertInvestigationPane.tsx)
    |
    v
Resolution + Audit Trail (services/audit.py + audit_chain.py)
```

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

Dashboard: http://localhost:3000 | API docs: http://localhost:8000/docs

## Testing

```bash
# Backend (193+ unit tests)
cd backend && pytest tests/ -v

# Frontend unit tests
cd frontend && npm run test:unit

# Frontend E2E
cd frontend && npx playwright test
```

## Project Structure

```
backend/
  app/
    pipeline/          # Ingestion: validation, normalization, dedup
    services/
      detection.py     # Extensible rule engine (registry pattern)
      correlation/     # Sequence, co-occurrence, cross-host matchers
      offense_engine.py # Alert grouping into offenses
      timeline.py      # Attack chain reconstruction
      agent_auth.py    # HMAC verification + nonce/timestamp validation
      audit.py         # Tamper-evident hash chain audit log
    models/            # 34 SQLAlchemy models
    routers/           # 37 API routers (183 endpoints)
    middleware/         # Rate limiting, security headers, timeouts
  tests/               # 222 unit + integration tests

frontend/
  app/(dashboard)/     # 24 pages (alerts, offenses, MITRE, timeline, ...)
  components/          # 42 React components
  lib/                 # API client, hooks, WebSocket

agent/
  agent/               # Python agent (collector, sender, buffer)
  install.sh           # One-line installer
```

## Key Metrics

| Metric | Value |
|--------|-------|
| Backend routers | 37 |
| API endpoints | 183 |
| Database models | 34 |
| Frontend pages | 24 |
| UI components | 22 |
| Backend tests | 222 |
| Config settings | 123 |
| Alembic migrations | 20 |

## License

MIT
