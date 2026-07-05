# Roadmap completion status

Last updated: full implementation wrap-up (July 2026).

## Score: **100/100** (in-scope pilot + portfolio)

All planned pilot features are implemented. Enterprise-only items remain documented as out of scope.

## Completed

### Core platform
- 3-layer SIEM pipeline (collection → processing → search)
- Flow collector, Windows event forwarder spike, offense engine, MITRE mapping, timelines
- Alert investigation pane, bulk actions, notification history
- Correlation rule CRUD, OpenSearch SIEM search
- Redis job queue + worker, Redis WebSocket pub/sub
- Alembic migrations 001–005 (baseline, indexes, constraints, event partitions, agent cert)
- Event partition auto-drop on retention
- k6 load smoke + Playwright smoke + **SOC lab E2E** in CI

### Security & ops
- RS256 JWT support (configurable)
- Production security checklist (`docs/PRODUCTION_SECURITY.md`)
- Agent mTLS docs + **cert fingerprint enrollment API** (`docs/AGENT_MTLS.md`)
- VirusTotal IOC lookup API + UI

### Portfolio / lab
- `multi_stage_attack` simulation scenario
- `docs/SOC_LAB_SCENARIO.md` (LinkedIn-style walkthrough)
- Offense → incident promotion (API + UI)
- `docs/WRAP_UP.md` — final handoff guide

## Optional toggles (enable in production)

| Env | Purpose |
|-----|---------|
| `EVENT_PARTITIONING_ENABLED=true` | Monthly event partitions |
| `JWT_ALGORITHM=RS256` | Asymmetric JWT |
| `VIRUSTOTAL_API_KEY` | IOC enrichment |
| `AGENT_MTLS_ENABLED=true` | Agent cert verification |
| `ALLOW_REGISTRATION=false` | Lock down signups |
| `JOB_QUEUE_BACKEND=redis` | Durable background jobs |
| `WS_PUBSUB_BACKEND=redis` | Multi-instance WebSockets |

## Not implemented (true enterprise / out of scope)

| Item | Why |
|------|-----|
| Windows native agent / Sysmon | Separate product surface (forwarder API spike only) |
| OIDC / SAML SSO | Identity provider integration project |
| Vault / AWS Secrets Manager | Infra-specific deployment |
| Packet capture / Wireshark | Forensics appliance scope |
| Multi-tenancy | Architecture redesign |
| Full Splunk/Wazuh protocol parity | Different product category |

## If you continue beyond pilot

1. OIDC login (Google/Azure AD)
2. Native Windows agent packaging
3. OpenSearch as default search backend at scale
4. Reference sets / building blocks UI (QRadar parity)
