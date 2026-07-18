# PROJECT_CONTEXT.md — Securi SIEM Platform

> **What this is:** A full-stack SIEM (Security Information and Event Management) platform — a mini IBM QRadar/Wazuh for learning and small Linux fleets.

---

## How It Works (Architecture Overview)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SECURI PLATFORM                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    HTTPS/JSON     ┌──────────────┐    WebSocket     │
│  │  Linux    │ ──────────────▶  │   FastAPI     │ ◀────────────▶  │
│  │  Agent    │  (HMAC-signed)   │   Backend     │   (real-time)   │
│  │  (Python) │                  │   (Python)    │                 │
│  └──────────┘                  └──────┬───────┘                 │
│       │                               │                          │
│       │  heartbeat (30s)              │  SQL (async)             │
│       │  metrics (30s)                ▼                          │
│       │  logs (10s)            ┌──────────────┐                  │
│       │                        │  PostgreSQL   │                  │
│       ▼                        │  (primary +   │                  │
│  ┌──────────┐                  │   replica)    │                  │
│  │  SQLite   │                 └──────────────┘                  │
│  │  (offline │                        │                          │
│  │  buffer)  │                 ┌──────┴───────┐                 │
│  └──────────┘                  │    Redis      │                 │
│                                │  (queue +     │                 │
│                                │   pub/sub)    │                 │
│                                └──────────────┘                 │
│                                       │                          │
│                                       ▼                          │
│                                ┌──────────────┐                 │
│                                │   Next.js     │                 │
│                                │   Frontend    │  ◀── Browser    │
│                                │   (React)     │                 │
│                                └──────────────┘                 │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  3-Layer SIEM Pipeline (QRadar-style)                      │   │
│  │                                                             │   │
│  │  Layer 1: COLLECTION    → Agent logs, metrics, flows       │   │
│  │  Layer 2: PROCESSING    → Detection rules, correlation,    │   │
│  │                           offense grouping, UEBA, MITRE    │   │
│  │  Layer 3: SEARCH        → SIEM query parser, global search,│   │
│  │                           OpenSearch (optional)            │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend** | FastAPI + SQLAlchemy (async) + PostgreSQL | High-performance async Python, real ORM |
| **Frontend** | Next.js 14 + TypeScript + TailwindCSS | Modern React, SSR, type safety |
| **Agent** | Python + requests + SQLite | Lightweight, runs anywhere on Linux |
| **Cache/Queue** | Redis | Job queue + WebSocket pub/sub |
| **Search** | OpenSearch (optional) | Full-text search at scale |
| **Infra** | Docker Compose + Kubernetes + Helm | Production-grade deployment |
| **CI/CD** | GitHub Actions + Playwright + k6 | Automated testing + release |

---

## Database (34 Tables)

```
Users & Auth:
  users, roles, refresh_tokens, password_reset_tokens,
  user_invites, user_sessions

Core SIEM:
  hosts, enrollment_tokens, events, metrics,
  alert_rules, alerts, mitre_techniques, mitre_mappings

Detection & Response:
  correlation_rules, correlation_results,
  attack_timelines, host_threat_scores, host_risk_scores,
  offenses, offense_events, incidents, incident_alerts, incident_notes

Investigation:
  reference_sets, reference_set_entries, building_blocks,
  saved_searches, generated_reports, ueba_anomalies

Operations:
  audit_logs, notification_settings, notification_rules,
  in_app_notifications, playbooks, playbook_runs,
  analytics_daily_stat, dashboard_layouts, simulation_runs,
  telemetry_events, ingest_dedup, agent_nonces
```

---

## API Routes (39 Routers)

| Router | Purpose |
|--------|---------|
| `auth` | Login, register, logout, password reset, MFA |
| `oidc` | OIDC/SSO callback, provisioning |
| `users` | User management (admin) |
| `hosts` | Host enrollment, status, metrics |
| `agent` | Agent enrollment, heartbeat, event ingestion |
| `events` | Event CRUD, export |
| `alerts` | Alert list, detail, bulk actions, feedback |
| `alert_rules` | Detection rule management |
| `siem` | SIEM query execution |
| `search` | Global search |
| `analytics` | Dashboard stats, charts |
| `audit` | Audit log viewer |
| `offenses` | Offense grouping, timelines |
| `incidents` | Incident management |
| `correlation_rules` | Correlation rule CRUD |
| `network` | Network topology, host risk |
| `mitre` | MITRE ATT&CK technique browser |
| `threat_scores` | Host threat score history |
| `ueba` | UEBA anomaly viewer |
| `notifications` | Notification settings, rules |
| `assistant` | AI copilot endpoints |
| `reports` | Compliance report generation |
| `backups` | Backup management |
| `reference_sets` | Reference set CRUD |
| `building_blocks` | Reusable SIEM queries |
| `playbooks` | SOAR playbook management |
| `saved_searches` | Saved search + alert scheduling |
| `timeline` | Attack timeline reconstruction |
| `investigation` | Investigation workspace |
| `simulation` | Attack simulation engine |
| `settings` | Platform settings |
| `system` | System health, status |
| `maintenance` | Window management |
| `ioc` | IOC lookup (VirusTotal) |
| `telemetry` | Platform telemetry |
| `dashboard` | Dashboard layout persistence |
| `metrics` | Detailed metrics |
| `maintenance` | Maintenance windows |

---

## Frontend Pages (28 Dashboard + Auth)

```
Auth:
  /login, /register, /forgot-password, /reset-password, /accept-invite

Dashboard:
  /               — Executive KPIs + security timeline + live feed
  /alerts         — Alert list with triage actions
  /hosts          — Host list with status, risk scores
  /events         — Event browser with filtering
  /siem           — SIEM query builder
  /search         — Global search
  /analytics      — Charts and metrics
  /offenses       — Offense grouping
  /incidents      — Incident management
  /network        — Network topology map
  /mitre          — ATT&CK technique browser
  /ueba           — UEBA anomaly viewer
  /reports        — Compliance report generator
  /simulation     — Attack Lab (brute force, multi-stage)
  /timeline       — Attack timeline reconstruction
  /settings       — User/notification/system settings
  /reference-sets — Reference set management
  /playbooks      — SOAR playbook editor
  /saved-searches — Saved search management
  /assistant      — AI copilot (also floating panel)
  /onboarding     — Setup checklist
```

---

## Detection Pipeline Flow

```
Agent collects logs/metrics
    │
    ▼
POST /api/v1/agent/events  (HMAC-signed batch)
    │
    ▼
Event Ingestion Pipeline:
  1. Validate HMAC signature
  2. Deduplicate (ingest_dedup table)
  3. Normalize fields (pipeline/normalizer.py)
  4. Validate schema (pipeline/validator.py)
  5. Store in PostgreSQL (+ optional OpenSearch)
    │
    ▼
Detection Rules Engine:
  - 7 rule types (failed_login, brute_force, high_cpu, high_memory, etc.)
  - Threshold-based matching
  - Generates alerts with severity + MITRE mapping
    │
    ▼
Correlation Engine:
  - Sequence matcher (ordered events)
  - Co-occurrence matcher (related events)
  - Cross-host matcher (lateral movement)
  - Confidence scoring
    │
    ▼
Offense Engine:
  - Groups related alerts/events into offenses
  - QRadar-style offense timelines
  - Attack chain reconstruction
    │
    ▼
UEBA (User & Entity Behavior Analytics):
  - Baseline per user/entity
  - Z-score anomaly detection
  - Configurable thresholds
    │
    ▼
Notifications:
  - Email (SMTP)
  - Telegram bot
  - Slack webhook
  - In-app notifications
```

---

## SOC Analyst Workflow

```
1. COLLECT    → Agent reports events from Linux hosts
2. DETECT     → Rules engine fires alerts (brute force, malware, etc.)
3. CORRELATE  → Engine groups related alerts into offenses
4. INVESTIGATE → Analyst opens alert → sees related events, host info, AI summary
5. TRIAGE     → Analyst changes status (open → investigating → resolved)
6. RESPOND    → Playbook triggers webhook, or analyst promotes to incident
7. REPORT     → Compliance report generated (SOC2, ISO27001, HIPAA)
```

---

## Key Design Decisions

1. **Local-first AI** — Works without API keys using rule-based templates; optional LLM enrichment
2. **Cookie-primary auth** — JWT in HttpOnly cookie (XSS-safe), not localStorage
3. **QRadar-style pipeline** — 3-layer architecture mirrors enterprise SIEM
4. **Offline-capable agent** — SQLite buffer when network is down, auto-flush on reconnect
5. **Event-driven realtime** — WebSocket + Redis pub/sub for live updates
6. **Infrastructure-as-code** — Docker Compose, K8s manifests, Helm chart all in repo
7. **Defense in depth** — Rate limiting, security headers, RBAC, audit logging, MFA
