# Health probes

Liveness, readiness, and startup probes for Docker Compose, Kubernetes, and load balancers.

## Backend API

| Endpoint | Probe | HTTP | Purpose |
|----------|-------|------|---------|
| `GET /health/live` | Liveness | 200 | Process alive — no dependency checks |
| `GET /health/startup` | Startup | 200 / 503 | Database reachable (boot / migrations) |
| `GET /health/ready` | Readiness | 200 / 503 | DB + Redis job broker / WS pubsub (+ OpenSearch if enabled) |

Readiness returns **503** when `status` is `degraded` so orchestrators remove the pod from service.

### Readiness checks

| Check | When |
|-------|------|
| `database` | Always |
| `job_broker` | `JOB_QUEUE_BACKEND=redis` |
| `ws_pubsub` | `WS_PUBSUB_BACKEND=redis` |
| `opensearch` | `SEARCH_BACKEND=opensearch` |

## Frontend

| Endpoint | Purpose |
|----------|---------|
| `GET /healthz` | Lightweight JSON `{"status":"ok"}` — avoids ingress `/api` → backend conflict |

## Job worker

| Check | Command |
|-------|---------|
| Liveness | `python -m app.worker_health` (Redis ping) |

## Docker Compose

`docker-compose.yml` healthchecks:

| Service | Test |
|---------|------|
| postgres | `pg_isready` |
| redis | `redis-cli ping` |
| backend | `GET /health/ready` → HTTP 200 |
| worker | `python -m app.worker_health` |
| frontend | `GET /healthz` |
| opensearch | `/_cluster/health` |

`frontend` waits for `backend` `service_healthy`.

## Kubernetes / Helm

| Workload | startup | readiness | liveness |
|----------|---------|-----------|----------|
| backend | `/health/startup` | `/health/ready` | `/health/live` |
| frontend | — | `/healthz` | `/healthz` |
| worker | — | — | `worker_health` exec |
| postgres | `pg_isready` | `pg_isready` | `pg_isready` |
| redis | `redis-cli ping` | `redis-cli ping` | `redis-cli ping` |

Ingress may expose `GET /health/ready` on the public host for external monitoring (`docs/KUBERNETES_INGRESS.md`).

## Verify

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/ready
curl -s http://localhost:3000/healthz
docker compose ps   # healthy column
kubectl -n securi describe pod -l app.kubernetes.io/component=api
```

## CI

`docker-compose.ci.yml` waits on backend `/health/ready`. GitHub Actions compose smoke uses the same check.

## Related

- `docs/HEALTH_PROBES.md` — readiness drops during shutdown (`shutting_down`)
- `docs/GRACEFUL_SHUTDOWN.md` — SIGTERM drain sequence
- `backend/app/core/health.py` — probe logic
