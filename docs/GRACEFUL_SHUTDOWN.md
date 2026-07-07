# Graceful shutdown

Drain in-flight requests and background work before the process exits on `SIGTERM` (Kubernetes pod deletion, `docker compose stop`, deploy rollouts).

## Shutdown sequence

1. **Signal** — Uvicorn receives `SIGTERM`
2. **Readiness** — `shutdown_state` flips → `GET /health/ready` returns **503** (`shutting_down`)
3. **Scheduler** — APScheduler stops scheduling new jobs
4. **WebSockets** — clients closed with code `1001` (going away)
5. **Job queue** — in-flight handlers finish within grace window
6. **Database** — SQLAlchemy engine disposed

## Configuration

```env
SHUTDOWN_GRACE_SECONDS=30
```

| Layer | Setting |
|-------|---------|
| Uvicorn | `--timeout-graceful-shutdown 30` (backend `Dockerfile`) |
| App | `SHUTDOWN_GRACE_SECONDS` — job queue drain |
| Kubernetes | `terminationGracePeriodSeconds: 45` |
| Kubernetes | `preStop: sleep 5` — allow ingress endpoint removal |

Helm values:

```yaml
gracefulShutdown:
  terminationGracePeriodSeconds: 45
  preStopSleepSeconds: 5
```

`terminationGracePeriodSeconds` should exceed `SHUTDOWN_GRACE_SECONDS` + `preStopSleepSeconds`.

## Worker process

`python -m app.jobs.worker` handles `SIGINT`/`SIGTERM`, drains the Redis job queue with the same grace setting, then exits.

## Verify

```bash
# Terminal 1
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — while handling traffic
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health/ready
kill -TERM $(pgrep -f "uvicorn app.main")

# Readiness should flip to 503 during teardown
```

Kubernetes:

```bash
kubectl -n securi delete pod -l app.kubernetes.io/component=backend
kubectl -n securi logs -f deploy/securi-backend   # "graceful shutdown started/complete"
```

## Related

- `docs/HEALTH_PROBES.md` — readiness drops on shutdown
- `backend/app/core/lifecycle.py` — orchestration
- `backend/app/core/shutdown.py` — shutdown flag
