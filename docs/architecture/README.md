# Architecture Overview

This directory contains cross-cutting architecture documentation for the Securi Sphere SIEM platform.

---

## System Architecture

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
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
Linux Agent
    ↓
Secure Event Ingestion (HMAC-SHA256 signed)
    ↓
Detection Engine (7 rule types, threshold matching)
    ↓
Correlation Engine (sequence, co-occurrence, cross-host)
    ↓
Offense / Risk / UEBA (grouping, scoring, anomaly detection)
    ↓
Frontend SOC Dashboard (Next.js, real-time WebSocket)
```

---

## Team Member Responsibilities

| Member | Area | Key Directory |
|--------|------|---------------|
| **Member 1** | Core SIEM / Backend / Security Engine | `backend/` |
| **Member 2** | Frontend & Dashboard | `frontend/` |
| **Member 3** | Linux Agent & Telemetry | `agent/` |
| **Member 4** | Deployment, Testing & Documentation | `deploy/`, `helm/`, `k8s/`, `loadtests/` |

---

## Key Architecture Documents

| Document | Description |
|----------|-------------|
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | End-to-end pipeline data flow |
| [../SIEM_PIPELINE_ARCHITECTURE.md](../SIEM_PIPELINE_ARCHITECTURE.md) | QRadar-style 3-layer SIEM model |
| [../SCHEMA.md](../SCHEMA.md) | PostgreSQL database schema reference |
| [../API.md](../API.md) | REST API reference |
| [../HEALTH_PROBES.md](../HEALTH_PROBES.md) | Liveness, readiness, startup probes |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | FastAPI + SQLAlchemy (async) + PostgreSQL | High-performance async Python |
| Frontend | Next.js 14 + TypeScript + TailwindCSS | Modern React with SSR |
| Agent | Python + requests + SQLite | Lightweight Linux daemon |
| Cache/Queue | Redis | Job queue + WebSocket pub/sub |
| Search | PostgreSQL + OpenSearch (optional) | Full-text search at scale |
| Auth | JWT (HS256/RS256) + HttpOnly cookies + MFA | Defense in depth |
| Infra | Docker Compose + Kubernetes + Helm | Production deployment |
| CI/CD | GitHub Actions + Playwright + k6 | Automated testing + release |
