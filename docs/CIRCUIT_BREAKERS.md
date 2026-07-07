# Circuit breakers

Securi protects outbound calls to flaky external dependencies with named circuit breakers. When failures exceed a threshold, the circuit **opens** and calls fail fast until a recovery window elapses, then a single **half-open** trial is allowed.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CIRCUIT_BREAKERS_ENABLED` | `true` | Master switch; when `false`, breakers never block requests |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Consecutive failures before opening |
| `CIRCUIT_BREAKER_RECOVERY_SECONDS` | `30` | Seconds before half-open trial |

## Protected dependencies

| Circuit name | Integration |
|--------------|-------------|
| `opensearch` | OpenSearch index, bulk, search, cluster health |
| `virustotal` | IOC enrichment (`ioc_lookup`) |
| `playbook_webhook` | Playbook outbound webhooks |
| `oidc` | Reserved for OIDC token/userinfo calls |
| `llm` | Reserved for LLM provider calls |

OpenSearch uses `run_thread` and returns fallbacks (`None` / `0`) when the circuit is open. VirusTotal and playbooks surface `circuit_open` in responses or run logs.

## Operations

### Admin API

```
GET /api/v1/system/circuits
```

Requires **admin** role. Returns enabled flag, thresholds, and per-circuit snapshots (`state`, `failures`, `opened_seconds_ago`).

### Health

Readiness includes OpenSearch status. When the `opensearch` circuit is open, readiness reports `opensearch: circuit_open` (degraded).

## States

```
closed ──(N failures)──► open ──(recovery timeout)──► half_open
   ▲                         │                            │
   └──── success ────────────┴──── success ───────────────┘
                              failure re-opens
```

## Implementation

- `backend/app/core/circuit_breaker.py` — breaker registry and state machine
- `backend/app/core/circuit_guard.py` — `run_async` / `run_thread` helpers

## Related

- `docs/HEALTH_PROBES.md` — readiness reflects open circuits
- `docs/GRACEFUL_SHUTDOWN.md` — in-flight drain on shutdown
