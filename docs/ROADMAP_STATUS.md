# Roadmap completion status

Last updated: end-to-end completeness pass (July 2026).

## Score: **Pilot complete** — core SOC flows end-to-end; enterprise items out of scope

The platform supports register/invite → Attack Lab → offenses → investigation → incident without external docs. Optional integrations (OpenSearch at scale, native Windows agent, multi-tenancy) remain toggles or future work.

## Completed

### Core platform
- 3-layer SIEM pipeline (collection → processing → search)
- Flow collector, Windows event forwarder (lab preview), offense engine, MITRE mapping, timelines
- Alert investigation pane, bulk actions, notification history
- Correlation rule CRUD, OpenSearch SIEM search with live host indexing
- Reference sets in **search and real-time detection**
- Redis job queue + worker, Redis WebSocket pub/sub
- Alembic migrations **001–013** (OIDC, invites, UEBA, playbooks, notification rules, dashboard layouts, simulation runs, reference intel)
- Event partition auto-drop on retention
- k6 load smoke + Playwright smoke + **SOC lab E2E** (invite, offense promotion, maintenance, intel CRUD) in CI
- Compose smoke job (`docker-compose.ci.yml`) + release workflow publishing images on `v*` tags
- Unified **Securi** product branding in UI and user-facing API strings

### Security & ops
- RS256 JWT support (configurable)
- **OIDC SSO** (`docs/OIDC_SSO.md`) — Google/Azure AD style IdP login
- User invites and provisioning (`docs/USER_PROVISIONING.md`)
- Production security checklist (`docs/PRODUCTION_SECURITY.md`)
- Agent mTLS docs + cert fingerprint enrollment API (`docs/AGENT_MTLS.md`)
- VirusTotal IOC lookup API + UI (with disabled-state messaging)

### Portfolio / lab
- `multi_stage_attack` simulation scenario
- `docs/SOC_LAB_SCENARIO.md` — portfolio walkthrough
- `docs/GUIDE_DEMO.md` — 5-minute demo including **simulation-only** path (no VM)
- Offense → incident promotion (API + UI)
- `scripts/demo-setup.sh` and `scripts/demo-setup.ps1`
- `docker-compose.dev.yml` — Postgres + Redis only for native dev

### AI & UX (local-first copilot)
- AI Security Assistant with **local mode** indicator in UI
- Smart Investigation Copilot, NL search, offense AI brief
- Command palette, expanded onboarding checklist
- Threat Intel full CRUD UI, notification channel status in Settings
- Dedicated `/threat-scores` page with factor breakdown and host risk drawer
- Global error/404 pages, `/accept-invite` public route fix
- System page OpenSearch index stats (doc counts, ISM retention, oldest event index)
- Search NL panel shows local-mode chip and disabled state when AI is off

## Optional toggles (enable in production)

| Env | Purpose |
|-----|---------|
| `EVENT_PARTITIONING_ENABLED=true` | Monthly event partitions |
| `JWT_ALGORITHM=RS256` | Asymmetric JWT |
| `MAIL_HOST` + `MAIL_USER` + `MAIL_PASSWORD` | SMTP alert delivery |
| `VIRUSTOTAL_API_KEY` | IOC enrichment |
| `AGENT_MTLS_ENABLED=true` | Agent cert verification |
| `ALLOW_REGISTRATION=false` | Lock down signups |
| `JOB_QUEUE_BACKEND=redis` | Durable background jobs |
| `WS_PUBSUB_BACKEND=redis` | Multi-instance WebSockets |
| `SEARCH_BACKEND=opensearch` + `OPENSEARCH_URL` | Scale search |
| `UEBA_ENABLED=true` | Anomaly detection scans |
| `AI_PROVIDER=openai` + `OPENAI_API_KEY` | LLM-enriched chat and NL search |

## Not implemented (true enterprise / out of scope)

| Item | Why |
|------|-----|
| Windows native agent / Sysmon | Separate product surface (forwarder API spike only) |
| Vault / AWS Secrets Manager | Infra-specific deployment |
| Packet capture / Wireshark | Forensics appliance scope |
| Multi-tenancy | Architecture redesign |
| Full Splunk/Wazuh protocol parity | Different product category |
| Kubernetes / Helm | Single-server pilot scope |

## If you continue beyond pilot

1. Native Windows agent packaging
2. OpenSearch as default search backend at scale
3. CD pipeline (image publish on tag) — **done** via `.github/workflows/release.yml`; enable GHCR permissions for your org
4. Multi-tenant architecture
