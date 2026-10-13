# Phase 7.2 — Reproducible Linux Validation Lab

**Objective**: Prepare a reproducible Linux validation lab for SecuriSphere end-to-end event-to-incident pipeline validation, documenting the shortest reliable path to enroll a disposable Linux host and trace real authentication/service events through ingestion → detection → alerting → correlation → incident investigation.

**Important**: Do not claim live validation until actual Linux telemetry has been observed. Current development host is Windows PowerShell; live Linux validation remains untested.

---

## 1. Known State

| Category | Status |
|----------|--------|
| Synthetic pipeline | 41/41 relevant tests pass (9 new scenario tests, 25 p0 regression tests, 7 integration simulation API tests) |
| Test infrastructure | PostgreSQL on 127.0.0.1:5433 (securi_test user/database), Redis on 127.0.0.1:6380 |
| Import blockages (correlation_engine.py) | Fixed: `is_host_in_maintenance` added to `host_notify.py`; `AlertRule` import added; logger added |
| Known test failure | `test_audit_integrity_valid` — `body["valid"]` is `False` despite single-entry chain; pre-existing environment limitation; cannot truncate audit records per instructions |
| Known TypeScript errors | ~70 pre-existing errors in other frontend pages; production build blocked; not caused by Phase 7.2 fixes |
| Network telemetry Scenario E | Flow collector not configured; `journald` explicitly documented as insufficient; `nc -z localhost 22-80` port scan sequence required |
| Production frontend build | Blocked by ~70 pre-existing TypeScript errors |
| Agent authentication | `X-Agent-Timestamp`, `X-Agent-Nonce`, `X-Agent-Signature` headers; HMAC-SHA256 signing; 300s clock skew tolerance; nonce replay via `AgentRequestNonce` table (24h retention) |
| Event ingestion | POST `/api/v1/agent/events`; batch size 1-100; deduplication via SHA-256 fingerprint; timestamps rejected if >5 min in future or >30 days old; backpressure semaphore (`MAX_CONCURRENT_INGESTION=20`) yielding 429 when exhausted |
| Agent health | `last_seen` tracked; heartbeats update `host.last_seen`; status field (`VARCHAR`) indicates `online`/`offline` |
| Supported detection rules | `brute-force` (5+ SSH failures), `service_failure`, MITRE ATT&CK mapping |
| Enrollment token model | `id` (UUID PK), `host_id` (FK to hosts.id), `token_hash` (SHA-256 hex, indexed), `expires_at`, `used_at`, `revoked_at`, `revoked_by` (FK to users.id), `label` (VARCHAR 100), `created_by` (FK to users.id), `created_at` (timezone-aware) |
| Demo Center UI | **Removed** — the `/demo` page was deleted (untracked, unlinked, and its run call omitted the required `host_id`, so every run returned 422). Attack Lab (`/simulation`) is the canonical guided-demo surface. |
| Phase 4 frontend | Incident list, detail page, provenance badges, filter bar verified |

---

## 2. Infrastructure

### 2.1 Test Stack (docker-compose.test.yml)

- **PostgreSQL**: `postgres:16-alpine`, container `securi-test-postgres`, `127.0.0.1:5433:5432`, user `securi_test`, password `testpass`, database `securi_test`
- **Redis**: `redis:7-alpine`, container `securi-test-redis`, `127.0.0.1:6380:6379`, command `redis-server --save "" --appendonly no`

### 2.2 Full Stack (docker-compose.yml)

- **Backend**: `securi-backend`, binds `${BACKEND_HOST_BIND:-127.0.0.1}:8000:8000`
- **PostgreSQL**: `postgres:16-alpine`, variable `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`
- **Redis**: `redis:7-alpine`, variable `REDIS_PASSWORD`, `securi-backend` network
- **Caddy**: reverse proxy
- **Frontend**: on `${FRONTEND_HOST_BIND:-0.0.0.0}:3000:3000`
- **Environment**: `.env` file generates `JWT_SECRET`, `PG_PASS`, `SERVER_URL=http://{HOST}:8000`, `FRONTEND_URL=http://{HOST}:3000`

**To start test stack**:
```bash
cd /path/to/securi
docker compose -f docker-compose.test.yml up -d
# Verify: psql -h 127.0.0.1 -U securi_test -d securi_test -c "SELECT 1;"
# Verify: redis-cli -a testpass -n 0 -s 127.0.0.1:6380 PING
```

**To start full stack**:
```bash
cd /path/to/securi
cp .env.example .env  # or adjust existing .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 3. Linux Agent Enrollment

### 3.1 Prerequisites (from AGENT_INSTALL.md)

| Requirement | Details |
|-------------|---------|
| Securi server | Backend API reachable from target host (port 8000 or HTTPS via reverse proxy) |
| Target host | Ubuntu 20.04+ or Debian (apt-based) |
| Dashboard access | Admin or Analyst role to create hosts and enrollment tokens |
| Network | Target host can reach `SERVER_URL` outbound (HTTP/HTTPS) |

**Set `SERVER_URL` in server `.env`** to the URL agents use to connect — not `localhost` if agents run on other machines:

```env
SERVER_URL=http://YOUR_SERVER_IP:8000
FRONTEND_URL=http://YOUR_SERVER_IP:3000
```

For HTTPS with Caddy/nginx:

```env
SERVER_URL=https://securi.yourdomain.com
FRONTEND_URL=https://securi.yourdomain.com
```

### 3.2 Windows LAN Pilot Note

Bind the API to all interfaces (`0.0.0.0:8000`) so other machines on the LAN can reach it. Set `SERVER_URL` / `FRONTEND_URL` from the **current** Windows LAN IPv4 (DHCP changes). Do not hardcode an IP in application code.

```powershell
.\scripts\sync-lan-urls.ps1
.\scripts\validate-server-url.ps1
.\scripts\dev-windows.ps1
# or: .\scripts\deploy-windows-lan.ps1
# or: .\scripts\deploy-windows-lan.ps1 -LanIp <current-ipv4>
```

On the Linux target, use the same host as `SERVER_URL` (copy the dashboard enroll command):

```bash
curl -fsSL "$SERVER_URL/health/live"
curl -fsSL "$SERVER_URL/install.sh" | sudo bash -s -- \
  --token ENROLL_TOKEN --server "$SERVER_URL"
```

Allow inbound TCP 8000 on Windows (once) if the host firewall blocks it:

```powershell
New-NetFirewallRule -DisplayName "Securi API 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

### 3.3 Enrollment Token Workflow

1. **Add a host in the dashboard** → Host created with status **offline** and agent **Pending** (normal — no agent installed yet)
2. **Generate enrollment token** → In the hosts table, click **Enroll** → modal shows install command and token (valid 24 hours)
3. **Token properties** → Single-use, expires in 24 hours, revoked after use

### 3.4 Install Command (from dashboard)

```bash
curl -fsSL http://YOUR_SERVER:8000/install.sh | sudo bash -s -- \
  --token enroll_xxxxxxxx \
  --server http://YOUR_SERVER:8000
```

### 3.5 What the Installer Does (install.sh)

1. Installs Python 3 and dependencies via `apt-get` (python3, python3-pip, python3-venv, curl, ca-certificates, tar)
2. Downloads the agent bundle from `{SERVER}/agent-bundle.tar.gz`
3. Creates a virtualenv at `/opt/securi-agent`
4. Calls `POST /api/v1/agent/register` with the enrollment token → receives API key
5. Saves API key to `/etc/securi/config.json` (mode 600)
6. Installs and starts `securi-agent` systemd service (`Type=simple`, `ExecStart=/opt/securi-agent/venv/bin/python3 -m agent.main`, `Restart=always`)
7. Creates `/var/lib/securi` data directory

### 3.6 Manual Verification (on the host)

```bash
# Can reach API?
curl -fsSL http://YOUR_SERVER:8000/health

# Agent config
sudo cat /etc/securi/config.json

# Agent logs
sudo journalctl -u securi-agent -n 100 --no-pager
```

### 3.7 Confirm in Dashboard

Within ~30 seconds:

| Column | Expected value |
|--------|----------------|
| Agent | **Enrolled** |
| Hostname | Real hostname from the VM |
| Status | **online** |
| Last seen | Recent timestamp |

Data will appear in **Events**, **Metrics**, and the main **Dashboard**.

### 3.8 Uninstall Agent

```bash
sudo systemctl stop securi-agent
sudo systemctl disable securi-agent
sudo rm -f /etc/systemd/system/securi-agent.service
sudo rm -rf /opt/securi-agent /etc/securi /var/lib/securi
sudo systemctl daemon-reload
```

Delete the host from the dashboard if no longer needed.

### 3.9 Security Notes

- Enrollment tokens are single-use and expire in 24 hours
- API keys are stored hashed on the server; only shown once at registration
- Agent config at `/etc/securi/config.json` is readable only by root
- For production, set `ALLOW_REGISTRATION=false` and use HTTPS
- Optional: enable `AGENT_REQUEST_SIGNING=true` on server and `signing_enabled: true` in agent config for HMAC request signing (`X-Agent-Timestamp`, `X-Agent-Nonce`, `X-Agent-Signature` headers)

---

## 4. Event Ingestion (Post-Enrollment)

### 4.1 Agent → Server Endpoints

| Endpoint | Interval | Purpose |
|----------|----------|---------|
| `POST /api/v1/agent/heartbeat` | 30s | Keep-alive, integrity hash, online status |
| `POST /api/v1/agent/metrics` | 30s | CPU, memory, disk, network, load |
| `POST /api/v1/agent/events` | 10s | SSH logins, sudo, service failures |

### 4.2 Event Payload (v3)

Each event object:

```json
{
  "event_type": "ssh_login_failure",
  "severity": "medium",
  "description": "Agent v3.0.0 test: ssh_login_failure",
  "source": "auth.log",
  "raw_log": "Sep 6 12:00:00 kali sshd[1]: Failed password for root from 10.0.0.8 port 22 ssh2",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 4.3 Supported Event Types

- `ssh_login_failure` — SSH failed login
- `ssh_login_success` — SSH successful login
- `sudo_usage` — sudo command execution
- `service_failure` — Service check failure
- `service_start` — Service started

### 4.4 Ingestion Rules (from `ingestion.py`)

- Batch size 1-100 events per request
- Deduplication via SHA-256 fingerprint
- Timestamps rejected if `>5 min` in future or `>30 days` old
- Backpressure semaphore (`MAX_CONCURRENT_INGESTION=20`) → 429 when exhausted
- Events parsed, deduplicated, MITRE-enriched, stored in PostgreSQL

### 4.5 Detection Rules (supported)

- `brute-force` — 5+ SSH failures within a window
- `service_failure` — Service check failure
- MITRE ATT&CK mapping applied per event

### 4.6 Scenario E (network_reconnaissance)

**Requires** flow collector configured. Live instructions use `nc -z localhost 22-80` port scan sequence.

> **Note**: `journald` is explicitly documented as insufficient for Scenario E; a flow collector/pcap is required.

---

## 5. Simulation Runner (for test validation)

### 5.1 Available Scenarios (from `simulation_scenarios.py`)

| Scenario ID | Description |
|-------------|-------------|
| `auth_anomaly` | Brute-force detection + MITRE ATT&CK mapping |
| `multi_stage` | Correlation engine: auth failures → service start → sudo usage → incident timeline |
| `agent_resilience` | Agent buffer: `enqueue`, `flush`, `dequeue_all`, `purge_stale` via controlled test harness |
| + 12 original scenarios | (full list available via `GET /api/v1/simulation/scenarios`) |

### 5.2 Execution

```bash
# List scenarios
GET /api/v1/simulation/scenarios

# List allowed event types  
GET /api/v1/simulation/event-types

# Run a scenario (requires admin/analyst role)
POST /api/v1/simulation/run/{scenario_id}
```

**Reproduction script** (`backend/scripts/repro_agent_events_500.py`):

```bash
REPRO_BASE_URL=http://127.0.0.1:8000
REPRO_EMAIL=admin@test.local
DEV_USER_PASSWORD=<password>

python backend/scripts/repro_agent_events_500.py
```

The script:
1. Health check `GET /health/live`
2. Login `POST /api/v1/auth/login`
3. Create host `POST /api/v1/hosts`
4. Generate enrollment token `POST /api/v1/hosts/{host_id}/enrollment-token`
5. Register agent `POST /api/v1/agent/register`
6. Send heartbeat `POST /api/v1/agent/heartbeat`
7. Send mixed events `POST /api/v1/agent/events`
8. Send 43 SSH failure events (batch test) `POST /api/v1/agent/events`
9. Send metrics `POST /api/v1/agent/metrics`

---

## 6. Live-Validation Checklist (NOT TESTED — requires actual Linux host)

| Step | Status | Notes |
|------|--------|-------|
| Start test stack: `docker compose -f docker-compose.test.yml up -d` | NOT TESTED | Requires Docker + Docker Compose |
| Start full stack: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` | NOT TESTED | Requires Docker + Docker Compose |
| Set `SERVER_URL` in `.env` to actual server IP | NOT TESTED | Must be reachable from Linux target |
| Add a host in the dashboard | NOT TESTED | Web UI access required |
| Generate enrollment token for the host | NOT TESTED | Token valid 24 hours, single-use |
| Run `install.sh` on a Linux target host | NOT TESTED | Requires Ubuntu 20.04+ or Debian, root access |
| Verify agent appears as **Enrolled** / **online** in dashboard | NOT TESTED | Within ~30 seconds of install |
| Post a SSH login failure event from the agent | NOT TESTED | `POST /api/v1/agent/events` with `ssh_login_failure` |
| Observe event ingestion and detection (brute-force) | NOT TESTED | Check alerts/offenses in dashboard |
| Run simulation scenario `auth_anomaly` | NOT TESTED | `POST /api/v1/simulation/run/auth_anomaly` |
| Run simulation scenario `multi_stage` | NOT TESTED | Exercises correlation engine |
| Run simulation scenario `agent_resilience` | NOT TESTED | Exercises agent buffer operations |
| Verify `test_audit_integrity_valid` behavior | PRE-EXISTING FAIL | `body["valid"]` is `False`; isolated; cannot truncate audit records |
| Verify network telemetry Scenario E with flow collector | NOT TESTED | Requires flow collector config; `journald` insufficient per scenario notes |
| Production frontend build validation | NOT TESTED | Blocked by ~70 pre-existing TS errors |

---

## 7. Preserved Baselines

- **41/41 relevant tests pass** — synthetic pipeline baseline unchanged
- **`test_audit_integrity_valid`** — known failure documented and isolated; `body["valid"]` is `False` despite single-entry chain; per instructions cannot truncate audit records
- **~70 TypeScript errors** in other frontend pages — pre-existing; production build blocked; not caused by Phase 7.2 fixes
- **Import blockages in `correlation_engine.py`** — already fixed (`is_host_in_maintenance`, `AlertRule`, `logger`)
- **PostgreSQL test infrastructure** — restored via `docker compose -f docker-compose.test.yml up -d`
- **Enrollment token model** — `id` (UUID PK), `host_id` (FK to hosts.id), `token_hash` (SHA-256 hex, indexed), `expires_at`, `used_at`, `revoked_at`, `revoked_by` (FK to users.id), `label` (VARCHAR 100), `created_by` (FK to users.id), `created_at` (timezone-aware)
- **Agent authentication** — `X-Agent-Timestamp`, `X-Agent-Nonce`, `X-Agent-Signature` headers; HMAC-SHA256 signing; 300s clock skew tolerance; nonce replay via `AgentRequestNonce` table (24h retention)
- **Event ingestion** — POST `/api/v1/agent/events`; batch size 1-100; deduplication via SHA-256 fingerprint; timestamps rejected if >5 min in future or >30 days old; backpressure semaphore (`MAX_CONCURRENT_INGESTION=20`) yielding 429 when exhausted
- **Scenario E (network_reconnaissance)** — requires flow collector; `journald` explicitly documented as insufficient; `nc -z localhost 22-80` port scan sequence

---

## 8. Next Steps (to Enable Live Validation)

1. **Obtain a disposable Linux host** (Ubuntu 20.04+ VM or WSL2 instance)
2. **Install Docker and Docker Compose** on the host
3. **Start the test or full stack** (see Section 2)
4. **Configure `SERVER_URL`** in the server `.env` to the host's actual IP (not `127.0.0.1` unless using port forwarding)
5. **Add a host in the dashboard** and generate an enrollment token
6. **Run `install.sh`** on the Linux target as root
7. **Verify agent appears online** in the dashboard
8. **Post test events** (`ssh_login_failure`, `ssh_login_success`, `sudo_usage`, `service_failure`, `service_start`) from the agent
9. **Observe event → detection → alert → correlation → incident** workflow end-to-end
10. **Run simulation scenarios** (`auth_anomaly`, `multi_stage`, `agent_resilience`) via `POST /api/v1/simulation/run/{scenario_id}`
11. **Document findings** — what telemetry was observed, what detection rules fired, what incidents were created

**Do not claim live validation complete until actual Linux telemetry has been observed and traced through the full pipeline.**

--- 

*Document generated for Phase 7.2 — Linux validation lab preparation. Preserves existing 41-test baseline and known issues unchanged.*