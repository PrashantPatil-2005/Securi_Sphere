# Request timeouts

Securi enforces maximum durations on **incoming API requests** and standardizes **outbound HTTP client** timeouts so slow work cannot exhaust workers or hang integrations indefinitely.

## Incoming requests

`RequestTimeoutMiddleware` wraps each HTTP request with `asyncio.wait_for`. Exceeded limits return **504** with `error.code: request_timeout`.

| Path pattern | Default timeout | Env var |
|--------------|-----------------|---------|
| `/health*` | Exempt | — |
| `/api/v1/agent/*` | 120s | `REQUEST_TIMEOUT_AGENT_SECONDS` |
| `*/export` | 300s | `REQUEST_TIMEOUT_EXPORT_SECONDS` |
| All other API routes | 60s | `REQUEST_TIMEOUT_SECONDS` |

WebSocket upgrades are exempt.

```env
REQUEST_TIMEOUT_ENABLED=true
REQUEST_TIMEOUT_SECONDS=60
REQUEST_TIMEOUT_AGENT_SECONDS=120
REQUEST_TIMEOUT_EXPORT_SECONDS=300
```

### Admin API

```
GET /api/v1/system/timeouts
```

Requires **admin** role. Returns configured values and example resolved timeouts per route class.

## Outbound HTTP

Outbound `httpx` clients use centralized helpers in `app/core/http_timeouts.py`:

| Profile | Default | Env var | Used by |
|---------|---------|---------|---------|
| Standard | 30s | `OUTBOUND_HTTP_TIMEOUT_SECONDS` | LLM providers |
| Short | 15s | `OUTBOUND_HTTP_TIMEOUT_SHORT_SECONDS` | OIDC, VirusTotal, playbooks, Slack/Telegram |

```env
OUTBOUND_HTTP_TIMEOUT_SECONDS=30
OUTBOUND_HTTP_TIMEOUT_SHORT_SECONDS=15
```

## Operations notes

- Set ingress / load balancer `proxy-read-timeout` **above** export timeout when serving large CSV/PDF exports.
- Agent ingest batches may need `REQUEST_TIMEOUT_AGENT_SECONDS` tuned for peak event volume.
- Pair with `docs/CIRCUIT_BREAKERS.md` — timeouts stop hung calls; breakers stop repeated failures.

## Related

- `docs/HEALTH_PROBES.md` — health routes are timeout-exempt
- `docs/GRACEFUL_SHUTDOWN.md` — in-flight requests drain on SIGTERM
- `docs/KUBERNETES_INGRESS.md` — proxy timeout annotations
