# Load tests (k6)

Smoke tests for CI and quick local API health checks.

## Prerequisites

- [k6](https://k6.io/docs/get-started/installation/) installed locally
- Backend running on port 8000 with PostgreSQL (and Redis recommended)

## Run smoke test locally

```bash
# Terminal 1 — start dependencies + API
docker compose up -d postgres redis
cd backend
# activate venv, set DATABASE_URL / JWT_SECRET in .env
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — run smoke
k6 run loadtests/smoke.js
```

Optional env overrides:

```bash
BASE_URL=http://localhost:8000 \
LOADTEST_EMAIL=admin@test.local \
LOADTEST_PASSWORD=testpass123 \
k6 run loadtests/smoke.js
```

## CI

The `load-smoke` job in `.github/workflows/ci.yml` starts the API against the CI Postgres service and runs this script on every push/PR.

## Thresholds (smoke)

| Metric | Gate |
|--------|------|
| `http_req_failed` | < 5% |
| `http_req_duration` p95 | < 800 ms |
| `checks` pass rate | > 95% |

These are relaxed for shared GitHub runners — tighten in staging when benchmarking real capacity.
