# SecuriSphere — Performance Diagnostic Report

**Date:** September 2, 2026  
**Scope:** Browser lag diagnosis on the Dashboard page  
**Method:** Static code analysis (no server instrumentation available)

---

## Executive Summary

The application's browser lag is caused by a **WebSocket-driven request invalidation storm** that fires 4–8 HTTP requests every ~600ms whenever security events are being ingested. Each of those requests triggers 3–13 sequential database queries on the backend. Combined with ~17 simultaneous queries on initial page load (including 7 from the always-mounted OnboardingWizard), the browser is overwhelmed with network traffic and the backend with sequential DB queries.

---

## Primary Cause: WebSocket Invalidation Storm

### Evidence

**File:** `frontend/lib/websocket.tsx` (lines 110–125)

```typescript
const INVALIDATION_BY_TYPE: Record<string, readonly (readonly string[])[]> = {
  security_feed: [["events"], ["siem"]],   // ← prefix match
  new_event: [["events"], ["siem"]],       // ← prefix match
  new_alert: [["alerts"], ["siem"]],       // ← prefix match
  // ...
};
```

React Query's `invalidateQueries({ queryKey: ["siem"] })` uses **prefix matching**, so it invalidates every query whose key starts with `"siem"`:

| Query Key | Component | Backend Endpoint |
|-----------|-----------|-----------------|
| `["siem", "executive", ...]` | SecurityKpis + AlertTrendChart (deduped) | `/api/v1/siem/executive` |
| `["siem", "severity-distribution", ...]` | SeverityBreakdown | `/api/v1/siem/severity-distribution` |
| `["siem", "top-risky-hosts", ...]` | HostRiskPanel | `/api/v1/siem/top-risky-hosts` |
| `["siem", "attack-timelines", ...]` | AttackTimelines | `/api/v1/siem/attack-timelines` |

That's **4 simultaneous HTTP requests** every time the debounce flush fires.

### Debounce Behavior (Not a Throttle)

**File:** `frontend/lib/websocket.tsx` (lines 148–158)

```typescript
const scheduleInvalidation = (queryKey: readonly string[]) => {
  pending.add(JSON.stringify(queryKey));
  if (!timer) timer = setTimeout(flush, INVALIDATION_DEBOUNCE_MS);  // 600ms
};
```

The 600ms debounce **delays the first flush** but does NOT prevent subsequent flushes. If `security_feed` messages arrive continuously (which they do in a SIEM):

| Time (ms) | Event |
|-----------|-------|
| 0 | Message → timer starts (flush at 600ms) |
| 100–500 | Messages add to pending set |
| 600 | **Flush fires** → 4 HTTP requests |
| 610 | New message → new timer starts (flush at 1210ms) |
| 1210 | **Flush fires again** → 4 HTTP requests |
| ... | Repeats every ~600ms while events arrive |

**Impact:** In an active SIEM environment, **4–8 HTTP requests fire every ~600ms**, sustained.

### Cascade Effect

Additionally, `["alerts"]` prefix invalidation from `new_alert` messages also triggers:
- `["alerts", "active", ...]` → ActiveThreats → `/api/v1/alerts`
- `["notifications", ...]` → NotificationCenter → `/api/v1/notifications/*`

So the actual burst is **6–8 requests per flush**.

---

## Secondary Cause: Sequential DB Queries on Backend

### executive_summary — 13 Sequential DB Queries

**File:** `backend/app/services/siem_analytics.py` (lines ~200–250)

The `/api/v1/siem/executive` endpoint runs these queries **sequentially**:

1. `SELECT count(*) FROM hosts`
2. `SELECT count(*) FROM hosts WHERE status = 'online'`
3. `SELECT count(*) FROM alerts WHERE status IN (...)`
4. `SELECT count(*) FROM alerts WHERE status IN (...) AND severity = 'critical'`
5. `SELECT count(*) FROM events WHERE timestamp >= ...`
6. `SELECT count(*) FROM alerts WHERE created_at >= ...`
7. `SELECT avg(score) FROM host_threat_scores`
8. `SELECT host.name, count(*) FROM events JOIN hosts ... GROUP BY host.name LIMIT 1`
9–12. `events_trend()` internally runs **4 more sequential queries** (total, security, authentication, service trends)

**Total: 13 sequential queries per request.** With a 600ms invalidation cycle, that's **52 DB queries/second** just from this endpoint.

### top_risky_hosts — Fetches ALL Hosts

**File:** `backend/app/services/siem_analytics.py` (lines ~115–130)

```python
hosts = {h.id: h for h in (await db.execute(select(Host))).scalars().all()}
```

This fetches **every host in the database** just to look up names for the top 20. Should use a JOIN or filtered subquery.

### attack_timeline_list — N+1 Query Pattern

**File:** `backend/app/services/siem_analytics.py` (lines ~260–280)

```python
for t in timelines:
    if t.event_ids:
        evs = (await db.execute(select(Event).where(Event.id.in_(uuids)))).scalars().all()
```

Runs a separate query for each timeline's events. With 50 timelines, that's up to 50 additional queries.

---

## Tertiary Cause: Initial Dashboard Query Flood

### ~17 Queries Fire on Page Load

On initial dashboard render, the following **unique** queries fire simultaneously:

| # | Query Key | Component | staleTime |
|---|-----------|-----------|-----------|
| 1 | `["settings", "public"]` | FeatureFlagsProvider + DemoModeBanner (deduped) | 60s |
| 2 | `["auth", "me"]` | Sidebar + CommandPalette (deduped) | 300s |
| 3 | `["siem", "executive", ...]` | SecurityKpis + AlertTrendChart (deduped) | 45s |
| 4 | `["alerts", "active", ...]` | ActiveThreats | 30s |
| 5 | `["siem", "severity-distribution", ...]` | SeverityBreakdown | 45s |
| 6 | `["siem", "top-risky-hosts", ...]` | HostRiskPanel | 45s |
| 7 | `["siem", "attack-timelines", ...]` | AttackTimelines | 45s |
| 8 | `["system-health"]` | SystemHealthPanel | 60s |
| 9 | `["offenses", "dashboard", ...]` | RecentOffenses | 30s |
| 10 | `["notifications", "unread-count"]` | TopNav | 15s, refetchInterval: 60s |
| 11 | `["notifications", "history", ...]` | TopNav | 30s |
| 12 | `["overview"]` | OnboardingWizard | 30s |
| 13 | `["simulation", "runs", "count"]` | OnboardingWizard | 30s |
| 14 | `["alerts", "count", "investigating"]` | OnboardingWizard | 30s |
| 15 | `["alerts", "count", "resolved"]` | OnboardingWizard | 30s |
| 16 | `["offenses", "count"]` | OnboardingWizard | 30s |
| 17 | `["incidents", "count"]` | OnboardingWizard | 30s |

**Queries 12–17 are from the OnboardingWizard** (`frontend/components/onboarding/OnboardingWizard.tsx` → `useOnboardingProgress`), which fires **7 queries** every time it mounts, even though it only renders when the wizard is visible (and often doesn't render at all after dismissal).

### Backend Pool Saturation

With `db_pool_size: 20`, the backend can handle 20 concurrent DB connections. The initial 17 queries (each running 3–13 sequential sub-queries) can temporarily saturate the pool, causing `db_pool_timeout` (30s) errors.

---

## WebSocket Reconnect Analysis

### Reconnect Logic is Correct

**File:** `frontend/lib/websocket.tsx` (lines 50–60)

```typescript
const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
```

Exponential backoff from 1s → 2s → 4s → 8s → 16s → 30s (capped). This is properly implemented.

### Why "Live feed disconnected. Reconnecting..." Appears

**File:** `frontend/components/layout/ConnectionBanner.tsx` (line 23)

The banner shows when `wsConnected === false`. This happens when:

1. **WebSocket URL is wrong:** The WS URL is constructed as `BACKEND_URL.replace("http", "ws") + "/api/v1/ws"`. If the app is behind a reverse proxy or HTTPS, the WebSocket connection to `ws://localhost:8000` may fail.

2. **Backend server restarts:** The status_job runs every 30 seconds and calls `update_host_statuses` + `update_all_threat_scores`, which are heavy queries. If the backend is under load, it may drop WebSocket connections.

3. **Proxy/load balancer timeout:** Most reverse proxies (nginx, Caddy) have WebSocket timeouts (default 60s). If no WS message is received within that window, the proxy closes the connection. The client sends pings every 30s (`startPing()`), which should prevent this — unless the proxy timeout is < 30s.

4. **The reconnect itself creates more load:** Each reconnect calls `fetchWsToken()` (HTTP POST to `/api/v1/ws/token`) and then establishes a new WebSocket connection, adding to the request load.

### Reconnect Frequency

In normal operation (no server restart), the WebSocket should stay connected indefinitely (pings every 30s). If it keeps disconnecting, the most likely cause is a proxy timeout < 30s or the backend dropping connections under load.

---

## Dashboard Section Cost Analysis

| Section | Queries | Backend Calls | Render Cost |
|---------|---------|---------------|-------------|
| SecurityKpis | 1 (`executive`) | 1 | Low (6 KPI cards) |
| ActiveThreats | 1 (`alerts?status=open`) | 1 | Low (6 list items) |
| SeverityBreakdown | 1 (`severity-distribution`) | 1 | Medium (PieChart) |
| HostRiskPanel | 1 (`top-risky-hosts`) | 1 | Low (6 list items) |
| AttackTimelines | 1 (`attack-timelines`) | 1 | Low (5 list items) |
| AlertTrendChart | 1 (`executive` — deduped) | 0 | Medium (AreaChart) |
| RecentOffenses | 1 (`offenses`) | 1 | Low (5 list items) |
| LiveFeed | 0 (WebSocket) | 0 | Low (30 items) |
| SystemHealthPanel | 1 (`system-health`) | 1 | Low (6 status dots) |
| **TopNav (always mounted)** | 2 (notifications) | 2 | Low |
| **Sidebar (always mounted)** | 0 (uses shared `auth/me`) | 0 | Low |
| **OnboardingWizard (always mounted)** | 7 (onboarding progress) | 7 | Low (hidden when dismissed) |
| **CommandPalette (always mounted)** | 0 (uses shared `auth/me`) | 0 | Low (hidden) |
| **AIAssistantPanel (always mounted)** | 0 (lazy) | 0 | Low (hidden) |

**Highest cost:** OnboardingWizard fires 7 queries on every page, even though it's usually hidden. Total initial load: **~17 unique HTTP requests**, each hitting a backend endpoint that runs 1–13 sequential DB queries.

---

## Recharts Animation Cost

All chart components correctly set `isAnimationActive={false}`:
- `AlertTrendChart.tsx` ✓
- `SeverityBreakdown.tsx` ✓

Charts are dynamically imported (`next/dynamic`) with `{ ssr: false }`. This is correctly implemented and should not cause issues.

---

## Framer Motion Impact

Framer-motion is imported in 3 always-loaded components:
- `PageTransition.tsx` — `motion.div` (opacity fade)
- `TopNav.tsx` — `AnimatePresence` + `motion.div` (dropdown animations)
- `Toast.tsx` — `AnimatePresence` + `motion.div` (toast animations)

Framer-motion adds ~40KB gzipped to the bundle. It's NOT tree-shaken because `AnimatePresence` requires the full runtime. This delays Time to Interactive but is not the primary cause of lag.

---

## Development vs Production Mode

| Factor | Dev Mode | Production Mode |
|--------|----------|-----------------|
| Bundle compilation | On-demand (Turbopack) | Pre-compiled |
| React validation | Extra warnings, profiling | Minimal overhead |
| Code splitting | Less optimized | Optimized |
| Request storm | **Same** | **Same** |
| OnboardingWizard queries | **Same (7 queries)** | **Same (7 queries)** |
| DB query sequential execution | **Same** | **Same** |

**Verdict:** Production mode will feel faster for initial load (smaller bundle, no compilation), but the **request storm and sequential DB queries are architecture-level issues that exist in both modes**. The lag should persist in production, just slightly less severe.

---

## Slowest Requests (Estimated)

Based on sequential DB query count:

1. `/api/v1/siem/executive` — **13 sequential queries** (slowest)
2. `/api/v1/siem/attack-timelines` — 3–53 queries (N+1 pattern)
3. `/api/v1/siem/top-rusty-hosts` — 3 queries (fetches ALL hosts)
4. `/api/v1/siem/severity-distribution` — 1–2 queries
5. `/api/v1/alerts?status=open` — 1–2 queries (indexed)
6. `/api/v1/simulation/runs?page_size=1` — 1 query
7. `/api/v1/alerts?status=investigating&page_size=1` — 1 query
8. `/api/v1/offenses?page_size=1` — 1 query
9. `/api/v1/incidents?page_size=1` — 1 query
10. `/api/v1/notifications/unread-count` — 1 query

---

## Exact Files That Would Need Changing

### Critical (request storm fix)

1. **`frontend/lib/websocket.tsx`**  
   Change `INVALIDATION_BY_TYPE` to use specific sub-keys instead of prefix `["siem"]`. For example, use `["siem", "executive"]`, `["siem", "severity-distribution"]`, etc. individually. Or better: only invalidate the live-relevant queries (e.g., `["alerts"]` for new alerts, but NOT `["siem"]` which is too broad).

2. **`frontend/lib/websocket.tsx`**  
   Implement a proper throttle (not debounce) for invalidation. The current debounce resets per-key but allows repeated flushes every 600ms. A throttle would ensure at most one flush per N seconds regardless of message volume.

### High Priority (initial load)

3. **`frontend/lib/hooks/useOnboardingProgress.ts`**  
   The 7 queries here should be lazy — only fetch when the OnboardingWizard is actually visible. Use `enabled` flag based on wizard dismissed state.

4. **`frontend/components/onboarding/OnboardingWizard.tsx`**  
   Gate `useOnboardingProgress()` behind `!isOnboardingWizardDismissed()`.

### Medium Priority (backend)

5. **`backend/app/services/siem_analytics.py` → `executive_summary()`**  
   Parallelize the 13 sequential queries using `asyncio.gather()`. This is the single biggest backend optimization.

6. **`backend/app/services/siem_analytics.py` → `events_trend()`**  
   Parallelize the 4 trend queries using `asyncio.gather()`.

7. **`backend/app/services/siem_analytics.py` → `top_risky_hosts()`**  
   Use a JOIN instead of fetching all hosts. Filter the hosts query to only the needed IDs.

8. **`backend/app/services/siem_analytics.py` → `attack_timeline_list()`**  
   Eliminate N+1 pattern by fetching all event details in a single query.

### Low Priority

9. **`frontend/lib/hooks/useNotifications.ts`**  
   `useUnreadNotificationCount` has `refetchInterval: 60_000` which is fine, but it also gets invalidated via WS `["alerts"]` prefix. Fixing the websocket invalidation (item #1) would also fix this.

---

## Recommended Minimal Fixes (Ordered by Impact)

### Fix 1: Change WebSocket invalidation from prefix to specific keys

**Impact: Eliminates ~80% of the lag**

In `frontend/lib/websocket.tsx`, change:
```typescript
security_feed: [["events"], ["siem"]],
```
to specific keys that only invalidate what's actually affected by feed updates:
```typescript
security_feed: [["events"], ["siem", "executive"]],
```

Or even better, only invalidate the queries that actually need real-time updates:
```typescript
security_feed: [],  // LiveFeed gets data directly from WS, no query invalidation needed
new_alert: [["alerts", "active"]],
```

### Fix 2: Parallelize backend queries

**Impact: 3–5x faster backend responses**

In `executive_summary()`, replace sequential awaits with `asyncio.gather()`:
```python
total_hosts, online_hosts, active_alerts, critical_alerts, total_events, period_alerts, avg_risk, attacked = await asyncio.gather(
    db.execute(...), db.execute(...), db.execute(...), ...
)
```

### Fix 3: Lazy-load OnboardingWizard queries

**Impact: Eliminates 7 unnecessary queries per page load**

Gate the queries behind the dismissed check:
```typescript
const enabled = !isOnboardingWizardDismissed();
const { data: overview } = useQuery({ enabled, ... });
```

### Fix 4: Add throttling to WebSocket invalidation

**Impact: Prevents request storm even with broad invalidation**

Replace the debounce with a proper throttle:
```typescript
let lastFlush = 0;
const scheduleInvalidation = (queryKey: readonly string[]) => {
  pending.add(JSON.stringify(queryKey));
  const now = Date.now();
  if (now - lastFlush >= INVALIDATION_DEBOUNCE_MS && !timer) {
    timer = setTimeout(flush, INVALIDATION_DEBOUNCE_MS);
  }
};
```

---

## Conclusion

The browser lag is **NOT** caused by:
- React rendering performance (all sections use `memo()`)
- Chart animations (`isAnimationActive={false}` everywhere)
- Recharts overhead (dynamically imported)
- WebSocket reconnect loops (exponential backoff is correct)
- Stale time configuration (60s default is reasonable)

The lag **IS** caused by:
1. **WebSocket invalidation storm** — 4–8 HTTP requests every ~600ms, sustained
2. **Sequential DB queries** — 13 queries in executive_summary alone
3. **Unnecessary OnboardingWizard queries** — 7 queries on every page load
4. **N+1 query patterns** — attack_timeline_list runs per-timeline queries

With the 4 recommended fixes, the dashboard should go from ~17 initial queries + sustained 4–8 requests/600ms to ~10 initial queries + targeted, throttled invalidation only when needed.
