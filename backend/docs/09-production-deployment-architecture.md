# 9. Production Deployment Architecture

## Target Environment

- **Platform:** Kubernetes (EKS/GKE/AKS) or Docker Compose (staging)
- **Scale:** 500 hosts, 10M events/day
- **SLA:** 99.9% uptime

---

## Service Topology

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Cloudflare │
                    │  / WAF      │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Ingress    │
                    │  (nginx)    │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
  │ securi-api  │   │ securi-api  │   │ securi-api  │
  │ (3 replicas)│   │             │   │             │
  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
  │ securi-     │   │   Redis     │   │ PostgreSQL  │
  │ worker (2)  │   │  (jobs+pub) │   │  (primary)  │
  └──────┬──────┘   └─────────────┘   └──────┬──────┘
         │                                    │
         └────────────────┬───────────────────┘
                          │
                   ┌──────▼──────┐
                   │ PG Replica  │
                   │ (read-only) │
                   └─────────────┘
```

---

## Pod Specifications

### API Deployment
```yaml
replicas: 3
resources:
  requests: { cpu: 500m, memory: 512Mi }
  limits: { cpu: 2, memory: 2Gi }
probes:
  liveness: GET /health/live
  readiness: GET /health/ready
env:
  ASYNC_EVENT_PIPELINE: "true"
  DATABASE_URL: from secret
  JWT_SECRET: from secret
```

### Worker Deployment
```yaml
replicas: 2
command: ["python", "-m", "app.jobs.worker"]
resources:
  requests: { cpu: 1, memory: 1Gi }
```

---

## Data Stores

| Store | Purpose | Sizing (500 hosts) |
|-------|---------|-------------------|
| PostgreSQL | Primary data | 500GB SSD, db.r6g.xlarge |
| Redis | Jobs + WS pub/sub | 2GB cache |
| OpenSearch | Search (Phase 3) | 3-node cluster, 100GB each |

---

## Networking

| Zone | Services |
|------|----------|
| Public | Ingress, WAF |
| App | API pods, workers |
| Data | PostgreSQL, Redis |
| Agent | Agent VLAN → API ingest only |

Agents should NOT reach dashboard APIs directly.

---

## Monitoring Stack

```
Securi API → Prometheus metrics → Grafana dashboards
                 → Structured JSON logs → Loki/ELK
                 → Traces (Phase 2) → Jaeger
```

### Key Metrics
- `http_request_duration_seconds` (histogram, by endpoint)
- `db_query_duration_seconds`
- `job_queue_depth`
- `events_ingested_total`
- `alerts_created_total`
- `correlation_matches_total`
- `agent_heartbeats_total`

---

## Backup & DR

| Component | RPO | RTO | Method |
|-----------|-----|-----|--------|
| PostgreSQL | 1h (pg_dump) / ≤15m (PITR) | 4h | WAL archiving + base backup — `docs/PITR_RUNBOOK.md` |
| Redis | N/A | 5m | Recreatable job queue |
| Config/Secrets | 0 | 1h | Git + Vault |

---

## CI/CD Pipeline

```
Push → Lint + Test → Build Docker → Scan (Trivy) → Deploy staging → Integration tests → Deploy prod
```

---

## Environment Variables (Production)

```env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET=<from-vault>
ASYNC_EVENT_PIPELINE=true
AGENT_REQUEST_SIGNING=true
ACCOUNT_LOCKOUT_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=15
RETENTION_DAYS=90
FRONTEND_URL=https://securi.example.com
```

See diagram: [architecture.mmd](./diagrams/architecture.mmd)
