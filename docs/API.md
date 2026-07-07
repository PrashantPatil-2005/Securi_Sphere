# API Reference

Base URL: `http://localhost:8000/api/v1`

## Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login (returns access + refresh tokens) |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/forgot-password` | Request password reset |
| POST | `/auth/reset-password` | Reset password with token |
| GET | `/auth/me` | Current user (JWT required) |

## Hosts

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/hosts` | admin, analyst | Create host |
| GET | `/hosts` | all | List hosts |
| GET | `/hosts/{id}` | all | Get host |
| GET | `/hosts/{id}/risk` | all | Explainable threat score with factors and history |
| DELETE | `/hosts/{id}` | admin | Delete host |
| POST | `/hosts/{id}/enrollment-token` | admin, analyst | Generate enrollment token |

## Agent

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/agent/register` | Enrollment token | Register agent, get API key |
| POST | `/agent/heartbeat` | X-API-Key | Heartbeat |
| POST | `/agent/events` | X-API-Key | Ingest events batch |
| POST | `/agent/metrics` | X-API-Key | Ingest metrics batch |

## Events & Metrics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/events` | Query events (filters: host_id, severity, event_type, from, to, q) |
| GET | `/metrics` | Query metrics (host_id, from, to) |

## Alerts

| Method | Path | Description |
|--------|------|-------------|
| GET | `/alerts` | List alerts |
| GET | `/alerts/{id}` | Get alert |
| PATCH | `/alerts/{id}/resolve` | Resolve alert |

## Other

| Method | Path | Description |
|--------|------|-------------|
| GET | `/search?q=` | Global search |
| GET | `/overview` | Dashboard KPIs |
| WS | `/ws?token=JWT` | Real-time updates |

Static: `GET /install.sh` â€” agent installer script


## Advanced endpoints

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/audit` | admin | Audit log entries |
| GET | `/audit/export` | admin | Export audit log (csv/json/pdf) |
| GET | `/audit/integrity` | admin | Verify audit hash chain |
| GET | `/backups` | admin | List Postgres backups |
| POST | `/backups/run` | admin | Trigger manual backup |
| GET | `/mitre/matrix` | all | MITRE ATT&CK matrix from events |
| GET | `/mitre/techniques` | all | Seeded MITRE techniques |
| GET/POST/PATCH/DELETE | `/alert-rules` | admin/analyst | Detection rule CRUD |
| GET | `/timelines` | all | Attack timelines |
| GET | `/timelines/{id}/events` | all | Events in a timeline |
| GET/POST | `/incidents` | analyst+ | Incident management |
| GET | `/simulation/scenarios` | admin | List simulation scenarios |
| POST | `/simulation/run/{scenario}` | admin | Inject synthetic attack chain |
| GET | `/reports/summary` | all | Summary report (json/csv) |
| GET | `/network/topology` | all | Host network map |
| GET | `/threat-scores` | all | Ranked host threat scores |
| GET | `/correlation-rules` | all | Read-only correlation rules |
| GET/POST/DELETE | `/maintenance-windows` | analyst+ | Host maintenance windows (suppress routine alerts) |
| GET | `/hosts/{id}/enrollment-tokens` | admin/analyst | List enrollment tokens |
| DELETE | `/enrollment-tokens/{id}` | admin/analyst | Revoke token |

Agent heartbeat accepts optional JSON: `{ "agent_hash", "agent_version" }`.
