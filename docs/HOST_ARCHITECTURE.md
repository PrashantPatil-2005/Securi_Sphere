# Host Onboarding & Monitoring Architecture

This document defines how hosts move from **registration** → **enrollment** → **agent connection** → **live monitoring** on the dashboard.

## Lifecycle states

| Status | Meaning | Condition |
|--------|---------|-----------|
| `inactive` | Registered in SIEM, no agent yet | `api_key_hash` is null |
| `online` | Agent enrolled, heartbeat fresh (<90s), no high alerts | Enrolled + `last_seen` recent |
| `warning` | Enrolled, heartbeat OK, open medium/high alerts | |
| `critical` | Enrolled, open critical alerts OR severe condition | |
| `offline` | Enrolled but agent stopped heartbeating (>90s) | `api_key_hash` set + stale `last_seen` |

## End-to-end flow

```
Dashboard (analyst)
  │ POST /hosts {name}
  ▼
Host record (status=inactive, no api_key)
  │ POST /hosts/{id}/enrollment-token
  ▼
EnrollmentToken (hashed, 24h TTL) + install_command
  │ curl install.sh on Linux VM
  ▼
POST /agent/register {enrollment_token, hostname, ip, os}
  │ validates token → sets api_key_hash, status=online, last_seen=now
  ▼
Agent loops: heartbeat (30s), metrics (30s), events (10s)
  │ X-API-Key header on all calls
  ▼
Backend updates last_seen, ingests data, runs detection
  │ status_job every 30s reconciles online/offline/warning/critical
  ▼
WebSocket host_status / host_enrolled → frontend invalidates hosts + siem queries
  ▼
Dashboard shows real counts from GET /siem/executive and GET /hosts
```

## 1. Host registration

- **Who:** Analyst/admin via dashboard or `POST /api/v1/hosts`
- **Creates:** `hosts` row with `name`, `status=inactive`, `created_by`
- **Does not:** Install agent or generate API key

## 2. Enrollment tokens

- **Generate:** `POST /api/v1/hosts/{id}/enrollment-token`
- **Storage:** Plain token returned once; DB stores SHA-256 hash
- **Validation at register:** unused, not revoked, not expired, matches `host_id`
- **Single-use:** `used_at` set on successful registration

## 3. Agent connection

- **Register:** `POST /api/v1/agent/register` (no API key yet)
- **Returns:** `api_key` (`sk_live_*`) — agent stores in `/etc/securi/config.json`
- **All subsequent calls:** `X-API-Key` header, validated via `get_authenticated_agent`

## 4. Heartbeats

- **Interval:** 30s (`agent/main.py`)
- **Endpoint:** `POST /api/v1/agent/heartbeat`
- **Effect:** Updates `last_seen`; flips `offline`/`warning`/`critical` → `online` when agent returns

## 5. Status determination

- **Background job:** `update_host_statuses()` every 30s (`main.py` scheduler)
- **Unenrolled:** forced `inactive` (no false offline alerts)
- **Enrolled + stale >90s:** `offline` + optional "Agent Offline" alert
- **Enrolled + critical alerts:** `critical`
- **Enrolled + high/medium alerts:** `warning`
- **Else:** `online`

## 6. Events & metrics

- **Events:** `POST /api/v1/agent/events` → ingestion pipeline → detection, correlation, offenses, WS `security_feed`
- **Metrics:** `POST /api/v1/agent/metrics` → `metrics` table → detection rules (CPU/memory/disk) → threat scores

## 7. Real-time dashboard

- **WebSocket:** JWT ticket via `POST /api/v1/ws/token`, connect `/api/v1/ws`
- **Invalidation map:** `host_status`, `host_enrolled` → `["hosts"]`, `["siem"]`
- **Executive KPIs:** `GET /api/v1/siem/executive` — all counts from DB, no mock data

## 8. Database schema (existing)

| Table | Purpose |
|-------|---------|
| `hosts` | Identity, `api_key_hash`, `status`, `last_seen`, network metadata |
| `enrollment_tokens` | One-time install tokens |
| `events` | Security events per host |
| `metrics` | Resource metrics per host |
| `host_threat_scores` | Current risk score |
| `alerts` | Detection output |

No schema migration required for Phase 1; status value `inactive` is a convention on existing `status` column.

## 9. API endpoints

| Method | Path | Role |
|--------|------|------|
| POST | `/hosts` | Create host (inactive) |
| GET | `/hosts` | List all hosts (inventory — no time-range filter) |
| GET | `/hosts/{id}` | Host detail + alert count |
| DELETE | `/hosts/{id}` | Remove host |
| POST | `/hosts/{id}/enrollment-token` | Generate install token |
| GET | `/hosts/{id}/enrollment-tokens` | List tokens |
| DELETE | `/enrollment-tokens/{id}` | Revoke token |
| POST | `/agent/register` | Agent enrollment |
| POST | `/agent/heartbeat` | Liveness |
| POST | `/agent/events` | Event batch |
| POST | `/agent/metrics` | Metric batch |
| GET | `/siem/executive` | Dashboard KPIs |

## 10. Frontend workflows

1. **Hosts page** — add host → enroll → copy install command → wait for WS/refetch → see `inactive` → `online`
2. **Overview** — executive KPIs from SIEM API; risky hosts clickable → risk drawer
3. **Auth** — login required; `AuthGuard` validates `/me` before rendering dashboard

## Authentication (Phase 1)

- Middleware checks `ss_auth` cookie (fast gate)
- `AuthGuard` calls `GET /auth/me` before dashboard render
- Login sets `ss_auth` only after successful `/me`
- Stale cookies cleared on 401; redirect to `/login`

## Non-goals (Phase 2+)

- Windows/macOS agents
- Multi-tenant host groups
- Automatic LAN discovery
