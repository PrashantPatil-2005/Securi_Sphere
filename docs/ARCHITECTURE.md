# Architecture — Securi SIEM Pipeline

## Data Flow Diagram

```
                           THE SIEM PIPELINE
                           ==================

  ┌─────────────────────────────────────────────────────────────────┐
  │                        COLLECTION LAYER                         │
  │                                                                 │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
  │  │ Server 1 │  │ Server 2 │  │ Server 3 │  │ Server N │       │
  │  │  (agent) │  │  (agent) │  │  (agent) │  │  (agent) │       │
  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
  │       │              │              │              │             │
  │       │   ┌──────────┴──────────────┴──────────────┘            │
  │       │   │  Each agent:                                        │
  │       │   │  • Tails /var/log/auth.log, syslog, journald        │
  │       │   │  • Collects CPU/memory/disk metrics (psutil)        │
  │       │   │  • Batches events every 10s                         │
  │       │   │  • Signs requests with HMAC-SHA256                  │
  │       │   │  • Buffers to SQLite if network is down             │
  │       │   │  • Exponential backoff on failures                  │
  │       │   │                                                     │
  │       v   v                                                     │
  │  ┌──────────────┐                                               │
  │  │ Offline Buffer│  SQLite DB at /var/lib/securi/buffer.db      │
  │  │ (buffer.py)   │  Auto-replay on reconnect                    │
  │  └──────┬───────┘                                               │
  │         │                                                       │
  └─────────┼───────────────────────────────────────────────────────┘
            │
            v
  ┌─────────────────────────────────────────────────────────────────┐
  │                        GATEKEEPER                               │
  │                                                                 │
  │  POST /api/v1/agent/events                                      │
  │                                                                 │
  │  1. Verify HMAC-SHA256 signature (constant-time comparison)     │
  │  2. Check nonce (single-use, stored in DB, pruned after 5min)   │
  │  3. Validate timestamp (reject if >5 minutes skew)              │
  │  4. Resolve host by API key hash                                │
  │                                                                 │
  │  Code: backend/app/services/agent_auth.py                       │
  │        backend/app/dependencies_agent.py                        │
  └─────────┬───────────────────────────────────────────────────────┘
            │
            v
  ┌─────────────────────────────────────────────────────────────────┐
  │                     INGESTION PIPELINE                          │
  │                                                                 │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │ Step 1: Validate                                         │   │
  │  │ • Batch size: 1-100 events                               │   │
  │  │ • Timestamp: not future, not >30 days old                │   │
  │  │ • Fields: max 8192 chars for strings                     │   │
  │  │ Code: pipeline/validator.py                               │   │
  │  └─────────────────────┬───────────────────────────────────┘   │
  │                        │                                        │
  │  ┌─────────────────────v───────────────────────────────────┐   │
  │  │ Step 2: Normalize                                        │   │
  │  │ • Map variant names → canonical types                    │   │
  │  │ • "failed_login" → "ssh_login_failure"                   │   │
  │  │ • Extract source_ip, username, category                  │   │
  │  │ Code: pipeline/normalizer.py                              │   │
  │  └─────────────────────┬───────────────────────────────────┘   │
  │                        │                                        │
  │  ┌─────────────────────v───────────────────────────────────┐   │
  │  │ Step 3: Deduplicate                                      │   │
  │  │ • SHA-256 fingerprint (host + timestamp + type + log)    │   │
  │  │ • Redis SETEX first (fast path)                          │   │
  │  │ • PostgreSQL fallback                                    │   │
  │  │ Code: services/ingest_dedup.py                            │   │
  │  └─────────────────────┬───────────────────────────────────┘   │
  │                        │                                        │
  │  ┌─────────────────────v───────────────────────────────────┐   │
  │  │ Step 4: Enrich + Store                                   │   │
  │  │ • MITRE ATT&CK technique mapping                         │   │
  │  │ • IOC matching (VirusTotal reference sets)                │   │
  │  │ • Store to PostgreSQL (17-column Event model)             │   │
  │  │ • Index to OpenSearch (if enabled)                        │   │
  │  │ Code: pipeline/ingestion.py                               │   │
  │  └─────────────────────┬───────────────────────────────────┘   │
  │                        │                                        │
  └────────────────────────┼────────────────────────────────────────┘
                           │
                           v
  ┌─────────────────────────────────────────────────────────────────┐
  │                     DETECTION ENGINE                            │
  │                                                                 │
  │  Extensible rule registry (ABC + @register_checker):            │
  │                                                                 │
  │  ┌─────────────────────┐  ┌─────────────────────┐              │
  │  │ FailedLoginsChecker │  │ BruteForceChecker   │              │
  │  │ 5+ failures / 5min  │  │ 10+ failures        │              │
  │  └──────────┬──────────┘  └──────────┬──────────┘              │
  │             │                         │                         │
  │  ┌──────────┴──────────┐  ┌──────────┴──────────┐              │
  │  │ HighCpuChecker      │  │ HighMemoryChecker   │              │
  │  │ HighDiskChecker     │  │ ServiceFailure      │              │
  │  │ AgentOfflineChecker │  │                     │              │
  │  └──────────┬──────────┘  └──────────┬──────────┘              │
  │             │                         │                         │
  │             └────────────┬────────────┘                         │
  │                          │                                      │
  │                          v                                      │
  │                 ┌─────────────────┐                             │
  │                 │ create_alert()  │                             │
  │                 │ • Dedup by rule │                             │
  │                 │ • Index event   │                             │
  │                 │ • Link offense  │                             │
  │                 │ • WS broadcast  │                             │
  │                 └────────┬────────┘                             │
  │                          │                                      │
  │  Code: services/detection.py                                    │
  └──────────────────────────┼──────────────────────────────────────┘
                             │
                             v
  ┌─────────────────────────────────────────────────────────────────┐
  │                    CORRELATION ENGINE                           │
  │                                                                 │
  │  Three matcher algorithms:                                      │
  │                                                                 │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │ 1. SEQUENCE MATCHER                                      │   │
  │  │    Ordered events within time window                     │   │
  │  │    Example: failed → success → sudo = brute force        │   │
  │  │    Scoring: +15% privilege escalation, +10% high-volume  │   │
  │  └─────────────────────────────────────────────────────────┘   │
  │                                                                 │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │ 2. CO-OCCURRENCE MATCHER                                 │   │
  │  │    Order-independent set-subset check                    │   │
  │  │    Example: service_stop + agent_disconnect               │   │
  │  └─────────────────────────────────────────────────────────┘   │
  │                                                                 │
  │  ┌─────────────────────────────────────────────────────────┐   │
  │  │ 3. CROSS-HOST MATCHER                                    │   │
  │  │    Same attacker across multiple hosts                   │   │
  │  │    Grouped by source_ip or username                       │   │
  │  │    Example: same IP fails SSH on 3 servers               │   │
  │  └─────────────────────────────────────────────────────────┘   │
  │                                                                 │
  │  Code: services/correlation/framework.py                        │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                             v
  ┌─────────────────────────────────────────────────────────────────┐
  │                    OFFENSE ENGINE                               │
  │                                                                 │
  │  Groups related alerts into QRadar-style offenses:              │
  │  • 30-minute clustering window                                  │
  │  • Sequential offense numbers                                   │
  │  • Related hosts, users, events                                 │
  │  • Attack timeline reconstruction                               │
  │  • Risk level: low → medium → high → critical                   │
  │                                                                 │
  │  Code: services/offense_engine.py                               │
  └──────────────────────────┬──────────────────────────────────────┘
                             │
                             v
  ┌─────────────────────────────────────────────────────────────────┐
  │                 REAL-TIME BROADCAST                             │
  │                                                                 │
  │  ┌──────────────────┐     ┌──────────────────┐                 │
  │  │ Redis Pub/Sub    │ ──> │ WebSocket Manager│                 │
  │  │ securi:ws:bcast  │     │ ConnectionManager│                 │
  │  └──────────────────┘     └────────┬─────────┘                 │
  │                                    │                            │
  │  Multi-instance:                    │                            │
  │  • Redis relays between processes   │                            │
  │  • Each process broadcasts to its   │                            │
  │    connected WebSocket clients      │                            │
  │                                    │                            │
  │  Code: websocket/redis_pubsub.py   │                            │
  │        websocket/manager.py         │                            │
  └────────────────────────────────────┼────────────────────────────┘
                                       │
                                       v
  ┌─────────────────────────────────────────────────────────────────┐
  │                      DASHBOARD                                  │
  │                                                                 │
  │  24 pages:                                                      │
  │  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐            │
  │  │ Alerts  │ │ Offenses │ │Timeline │ │ Events   │            │
  │  ├─────────┤ ├──────────┤ ├─────────┤ ├──────────┤            │
  │  │ Hosts   │ │ MITRE    │ │ Network │ │ Metrics  │            │
  │  ├─────────┤ ├──────────┤ ├─────────┤ ├──────────┤            │
  │  │Search   │ │ Incidents│ │ Rules   │ │ Audit    │            │
  │  ├─────────┤ ├──────────┤ ├─────────┤ ├──────────┤            │
  │  │Reports  │ │ Intel    │ │ System  │ │ Settings │            │
  │  └─────────┘ └──────────┘ └─────────┘ └──────────┘            │
  │                                                                 │
  │  Real-time: WebSocket auto-reconnect, live feed                 │
  │  Investigation: Alert → Host → Timeline → Related Events        │
  │  AI: Copilot panel, alert summaries, NL search                  │
  │                                                                 │
  │  Code: frontend/app/(dashboard)/                                │
  │        frontend/components/                                     │
  └─────────────────────────────────────────────────────────────────┘
                                       │
                                       v
  ┌─────────────────────────────────────────────────────────────────┐
  │                     AUDIT TRAIL                                 │
  │                                                                 │
  │  Tamper-evident SHA-256 hash chain:                             │
  │                                                                 │
  │  Entry 1 ──hash──> Entry 2 ──hash──> Entry 3                   │
  │  (prev=null)        (prev=hash1)      (prev=hash2)             │
  │                                                                 │
  │  • Advisory lock prevents race conditions                       │
  │  • Chain verification detects any tampering                     │
  │  • Records: who, what, when, where, result                      │
  │                                                                 │
  │  Code: services/audit.py                                        │
  │        services/audit_chain.py                                  │
  │        models/audit.py                                          │
  └─────────────────────────────────────────────────────────────────┘
```

## Component Map

| Layer | Component | Code Location |
|-------|-----------|---------------|
| **Collection** | Agent collectors | `agent/agent/collector/` |
| **Collection** | Offline buffer | `agent/agent/buffer.py` |
| **Collection** | HMAC signing | `agent/agent/sender.py` |
| **Gatekeeper** | Signature verification | `backend/app/services/agent_auth.py` |
| **Gatekeeper** | Nonce/timestamp validation | `backend/app/services/agent_auth.py` |
| **Ingestion** | Payload validation | `backend/app/pipeline/validator.py` |
| **Ingestion** | Event normalization | `backend/app/pipeline/normalizer.py` |
| **Ingestion** | Deduplication | `backend/app/services/ingest_dedup.py` |
| **Ingestion** | MITRE enrichment | `backend/app/services/mitre.py` |
| **Storage** | Event model | `backend/app/models/event.py` |
| **Detection** | Rule engine | `backend/app/services/detection.py` |
| **Correlation** | Sequence matcher | `backend/app/services/correlation/framework.py` |
| **Correlation** | Co-occurrence matcher | `backend/app/services/correlation/framework.py` |
| **Correlation** | Cross-host matcher | `backend/app/services/correlation/framework.py` |
| **Offense** | Offense grouping | `backend/app/services/offense_engine.py` |
| **Timeline** | Attack reconstruction | `backend/app/services/timeline.py` |
| **Real-time** | Redis pub/sub | `backend/app/websocket/redis_pubsub.py` |
| **Real-time** | WebSocket manager | `backend/app/websocket/manager.py` |
| **Dashboard** | Alerts page | `frontend/app/(dashboard)/alerts/page.tsx` |
| **Dashboard** | Investigation pane | `frontend/components/AlertInvestigationPane.tsx` |
| **Audit** | Hash chain audit log | `backend/app/services/audit.py` |
| **Audit** | Chain verification | `backend/app/services/audit_chain.py` |

## Security Layers

```
Request → CORS → Rate Limit → Timeout → Security Headers → Auth
    │                                              │
    │    Agent requests:                           │
    │    HMAC verify → Nonce check → Timestamp → DB
    │                                              │
    │    User requests:                            │
    │    JWT verify → RBAC check → Route guard     │
```
