# IMPROVEMENT_PLAN.md — Securi SIEM Platform

> Generated: 2026-07-18 | After full audit of 210+ backend files, 42 frontend components, 44 scripts, 7 Docker configs

---

## Engineering Rating: 8.5/10 (Final Year Project)

### Breakdown

| Category | Score | Notes |
|----------|-------|-------|
| **Architecture** | 9/10 | QRadar-style 3-layer pipeline, proper separation of concerns, async throughout |
| **Feature Scope** | 9.5/10 | 39 routers, 57 services, 34 models, AI copilot, UEBA, SOAR — enterprise-level scope |
| **Code Quality** | 7.5/10 | Clean patterns but some silent exception swallowing, dead code, missing input validation |
| **Security** | 8/10 | Strong (JWT, RBAC, MFA, rate limiting, audit) but had committed secrets + some gaps (fixed now) |
| **Testing** | 6/10 | Backend has ~150 tests, 7 E2E specs, but ZERO frontend unit tests, trivial WS tests |
| **Infrastructure** | 9/10 | Docker, K8s, Helm, CI/CD, health probes, graceful shutdown — better than most startups |
| **Documentation** | 8.5/10 | 56 docs, but some are stale (ROADMAP, WRAP_UP contradict current state) |
| **Real-time** | 8.5/10 | WebSocket + Redis pub/sub, live feed, real-time alerts — production-ready |

### Verdict
This is a **final year project that could ship as a product**. The architecture mirrors IBM QRadar (a $1M+ enterprise tool). The breadth (39 API routers, 34 DB models, AI copilot, UEBA, SOAR playbooks, MITRE ATT&CK mapping) is extraordinary for a student project. Main weaknesses: zero frontend tests, stale docs, some dead code.

---

## BROKEN THINGS (Fix Immediately)

### 1. Correlation Engine Dead Branch
**File:** `backend/app/services/correlation_engine.py:18-21`
```python
if types != sorted(types, key=lambda t: t): pass
```
Ordered vs unordered sequences are treated identically. The `pass` means the ordering check does nothing.

**Fix:** Implement proper ordered vs unordered matching, or remove the dead branch.

### 2. Stale Documentation Contradicts Code
| Doc | Claims | Reality |
|-----|--------|---------|
| `docs/ENTERPRISE_ROADMAP.md` | "Empty Alembic chain" | 20 migrations exist |
| `docs/ENTERPRISE_ROADMAP.md` | "No OIDC" | Full OIDC router + service exist |
| `docs/WRAP_UP.md` | "Migrations 001-005" | 20 migrations (001-020) |
| `docs/WRAP_UP.md` | "OIDC not built" | Complete OIDC implementation |
| `docs/ENTERPRISE_ROADMAP.md` | "Score 62/100" | Much higher now |

**Fix:** Update or delete stale docs.

### 3. Legacy `localStorage` Token Cleanup
**File:** `frontend/lib/auth/session.ts:14-15`
```typescript
localStorage.removeItem("access_token");
localStorage.removeItem("refresh_token");
```
Dead code from pre-cookie auth migration. Harmless but confusing.

**Fix:** Remove these lines.

### 4. Debug Log Committed
**File:** `backend/debug-f50674.log` — Contains SQL queries, IPs, error details. Should not be in source tree.

**Fix:** Delete and add `debug-*.log` to `.gitignore` (already done in previous fix).

### 5. Redundant Import
**File:** `backend/app/routers/offenses.py:118` — `from fastapi import HTTPException` imported inside function, already imported at top.

**Fix:** Remove the local import.

---

## MISSING TESTS (High Priority)

### Frontend Unit Tests — ZERO
No `__tests__/` directory exists. All frontend testing is Playwright E2E only (7 specs).

**What to add:**
- Component tests for: AlertCard, HostCard, StatCard, ExportMenu, ConfirmDialog
- Hook tests for: useApiQuery, useOnboardingProgress, useWebSocket
- Utility tests for: api.ts, csp.ts, query parser, download.ts

### Backend Test Gaps
| Area | Current | Needed |
|------|---------|--------|
| Correlation engine matching logic | Schema validation only | Unit tests for sequence/co-occurrence/cross-host matchers |
| WebSocket manager | 2 trivial tests | Tests for Redis pub/sub path, connection lifecycle |
| OpenSearch search execution | Query building only | Integration tests with mock OpenSearch |
| RBAC HTTP behavior | Doc-style stub in test_rbac.py | Full HTTP integration tests (partially done in integration/) |
| Password complexity validation | Not tested | Unit tests for the new regex validator |

---

## IMPROVEMENT PLAN (Ranked by Impact)

### Phase 1: Polish & Fix (1-2 days)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 1 | Fix correlation engine dead branch (`correlation_engine.py:18-21`) | HIGH | 1h |
| 2 | Update stale docs (ENTERPRISE_ROADMAP, WRAP_UP, ROADMAP_STATUS) | HIGH | 2h |
| 3 | Remove legacy localStorage cleanup in session.ts | LOW | 5min |
| 4 | Remove redundant import in offenses.py:118 | LOW | 5min |
| 5 | Delete debug-f50674.log from repo | LOW | 5min |
| 6 | Clean up stale scripts/ (move to archive/) | MEDIUM | 1h |
| 7 | Fix silent exception swallowing — add logging to 6 catch blocks | MEDIUM | 2h |
| 8 | Remove hardcoded fallback templates in reports page | MEDIUM | 30min |

### Phase 2: Testing (3-5 days)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 9 | Add frontend component tests (5-10 key components) | HIGH | 1d |
| 10 | Add correlation engine unit tests | HIGH | 4h |
| 11 | Add WebSocket manager tests (Redis path) | MEDIUM | 4h |
| 12 | Add password complexity validator tests | MEDIUM | 1h |
| 13 | Add SIEM search INET fix tests | MEDIUM | 2h |
| 14 | Increase Playwright E2E coverage (alerts, incidents, settings) | MEDIUM | 2d |

### Phase 3: Feature Gaps (1-2 weeks)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 15 | Implement ordered vs unordered correlation matching | HIGH | 1d |
| 16 | Add frontend Storybook for component documentation | MEDIUM | 2d |
| 17 | Add CSP report-only mode for safe CSP rollout | MEDIUM | 2h |
| 18 | Add NetworkPolicy manifests for K8s | MEDIUM | 4h |
| 19 | Add PodDisruptionBudgets for K8s | LOW | 2h |
| 20 | Add Redis persistence (RDB/AOF) to docker-compose | MEDIUM | 1h |

### Phase 4: Production Hardening (2-3 weeks)

| # | Task | Impact | Effort |
|---|------|--------|--------|
| 21 | Add OpenSearch security plugin for non-dev environments | HIGH | 2d |
| 22 | Implement multi-tenancy (architecture redesign) | HIGH | 1-2w |
| 23 | Add native Windows agent / Sysmon integration | MEDIUM | 1w |
| 24 | Add packet capture / network forensics | LOW | 1w |
| 25 | Migrate to PyJWT (replace unmaintained python-jose) | MEDIUM | 4h |
| 26 | Add hash-pinned dependencies (supply chain security) | MEDIUM | 2h |

---

## WHAT TO PROVE (Portfolio/Demo Talking Points)

### For Interviews
1. **"I built a mini IBM QRadar"** — 3-layer SIEM pipeline, same architecture as a $1M+ enterprise product
2. **"39 API routers, 34 database models, 57 service modules"** — demonstrates full-stack depth
3. **"Real-time WebSocket + Redis pub/sub"** — production-grade real-time architecture
4. **"AI copilot that works offline"** — local-first design, no API key dependency
5. **"Kubernetes + Helm + CI/CD"** — infrastructure-as-code, not just a CRUD app
6. **"UEBA with z-score anomaly detection"** — data science applied to security
7. **"MITRE ATT&CK mapping"** — industry-standard threat framework integration
8. **"SOAR playbooks with HMAC-signed webhooks"** — automation and response

### For Demo
1. Run the SOC Lab scenario (multi-stage attack simulation)
2. Show the attack timeline reconstruction
3. Demonstrate the AI copilot ("explain this alert")
4. Show the SIEM query language (`host:web01 severity:critical`)
5. Show real-time alerts appearing via WebSocket
6. Generate a compliance report (SOC2/ISO27001)
7. Show the UEBA anomaly detection
8. Demonstrate offense grouping from correlated alerts

### Metrics to Quote
| Metric | Value |
|--------|-------|
| Backend routers | 39 |
| Database models | 34 |
| Service modules | 57 |
| Frontend components | 42 |
| Documentation pages | 56 |
| Alembic migrations | 20 |
| Docker configs | 7 |
| K8s manifests | 12 |
| Test files | 53+ |
| Config settings | 80+ |

---

## NEXT ACTIONS (Top 5)

1. **Fix the correlation engine dead branch** — it's broken logic, not just cleanup
2. **Update stale documentation** — someone reading your docs will see contradictions
3. **Add 5-10 frontend component tests** — zero frontend tests is the biggest gap
4. **Archive stale scripts** — the 44-file scripts/ directory is overwhelming
5. **Write a clean README** — the current one is good but could be more concise for portfolio use
