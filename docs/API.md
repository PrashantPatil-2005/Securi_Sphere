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

Static: `GET /install.sh` — agent installer script
