# Runtime Performance Verification Report (Real Frontend)

**Date:** September 3, 2026
**Method:** Headless Chromium driving the live dev frontend (`http://localhost:3000`, Next.js 14 dev/turbo) against the running backend (`http://127.0.0.1:8000`, proxied via Next.js rewrites). Measurement tool: `frontend/runtime-verify.mjs` (network, WebSocket, console, long-task instrumentation via CDP).
**No code changes were made.** Backend root `/` 404 was confirmed and intentionally left unfixed (per instruction — FastAPI has no root route, `/docs` was used only to confirm liveness).

---

## 1. Backend liveness (docs only)

| Endpoint | Result | Note |
|----------|--------|------|
| `/docs` | 200 in ~5ms | Backend alive |
| `/openapi.json` | 200 in ~8ms | Backend alive |
| `/` | 404 in ~6ms | Expected — no root route, **no fix applied** |

---

## 2. `/login` initial load

- **Navigation → load: ~1.18s** (TTFB 624ms, DOMContentLoaded 815ms, load 1180ms; dev-server warm-up included on first visit)
- **Total HTTP requests: 38** (dev-mode assets: JS chunks, CSS, fonts, logo)
- **API requests: 6** (3 unique endpoints, each ×2 due to React StrictMode double-effect in dev):
  - `GET /api/v1/settings/public` ×2 — avg 21ms
  - `GET /api/v1/auth/me` ×2 — avg 25ms (401, expected session probe)
  - `POST /api/v1/auth/refresh` ×2 — avg 16ms (401, expected — triggered by the 401 probe)

*Note: StrictMode doubles effect-driven requests in dev; production builds fire each once.*

---

## 3. Login flow timing

- **Submit → dashboard URL: 9.42s** (dominated by first-visit dev compilation of the `/` route; subsequent loads are far faster)
- **URL change → "Security Operations" rendered: 3.0s** (React Query initial fetch waterfall)
- **Settle (all initial queries complete): +3.5s**

---

## 4. Dashboard initial load (default state, wizard visible)

- **74 HTTP requests** (incl. 49 dev assets) / **25 API requests** since login submit
- **API inventory (avg):**

| Endpoint | Count | Avg / min / max |
|----------|-------|-----------------|
| POST /api/v1/telemetry/events | 9 | 830ms / 506ms / 1163ms |
| GET /api/v1/auth/me | 2 | 151ms |
| GET /api/v1/alerts?status=open&status=investigating&page_size=10&sort=-created_at | 2 | 195ms — **422** |
| POST /api/v1/ws/token | 2 | 316ms |
| GET /api/v1/siem/executive?preset=24h | 2 | 371ms — **500** |
| GET /api/v1/overview | 2 | 372ms — **500** |
| GET /api/v1/notifications/unread-count | 1 | 294ms |
| GET /api/v1/notifications/history | 1 | 351ms |
| GET /api/v1/siem/top-risky-hosts | 1 | 520ms |
| GET /api/v1/siem/severity-distribution | 1 | 594ms |
| GET /api/v1/alerts?status=resolved&page_size=1 | 1 | 667ms (onboarding) |
| GET /api/v1/simulation/runs?page_size=1 | 1 | 683ms (onboarding) |
| GET /api/v1/alerts?status=investigating&page_size=1 | 1 | 686ms (onboarding) |
| GET /api/v1/offenses?page_size=5 | 1 | 691ms |
| GET /api/v1/offenses?page_size=1 | 1 | 695ms (onboarding) |
| GET /api/v1/siem/attack-timelines | 1 | 701ms |
| GET /api/v1/incidents?page_size=1 | 1 | 707ms (onboarding) |
| GET /api/v1/system/health | 1 | 733ms |
| POST /api/v1/auth/login | 1 | 899ms |
| GET /api/v1/notifications/settings | 1 | 1074ms (onboarding) |

### Onboarding requests (default, wizard shown)
**8 hits across 7 unique keys** — `/api/v1/overview` ×2 (500 + retry), `simulation/runs`, `alerts?status=investigating`, `alerts?status=resolved`, `offenses?page_size=1`, `incidents?page_size=1`, `notifications/settings`. All 7 fire as designed in the default state (StrictMode dedupes the three onboarding consumers onto one shared React Query cache).

---

## 5. Onboarding after dismissal — **GATING IS INCOMPLETE (finding)**

Setting `securi_onboarding_wizard_done=1` and reloading still produced **all 7 onboarding requests** (same 8 hits, incl. `overview` ×2).

**Root cause:** three components consume `useOnboardingProgress()`:
- `OnboardingWizard` — gated by `enabled: !isOnboardingWizardDismissed()` (key `securi_onboarding_wizard_done`) ✅
- `OnboardingChecklist` — gated by its own key `securi_onboarding_done` (a **different** localStorage key)
- `ActivationCoach` — gated only by feature flag `ux_activation_coach_enabled`

Dismissing the wizard does not dismiss the checklist or the coach, so all 7 queries still fire on every dashboard load. The performance fix report's "7 → 0 when dismissed" only holds when **all three** surfaces are dismissed/disabled. Also, `/api/v1/overview` returns 500 (see §12), so the "Add a host" step can never register completion.

---

## 6. WebSocket — idle baseline (10s, no traffic)

- **WS frames received: 0, sent: 0**
- **API requests: 0**
- ✅ The dashboard makes **zero polling requests when idle**; LiveFeed is push-only via WS.

---

## 7. WS-triggered HTTP requests over ~30s (simulation-driven)

Two real scenario runs against `sim-analyst-host`: `brute_force_attack` at t=0, `host_health_crisis` at t=15s.

### WS traffic
- **50 frames received**: `security_feed` ×40, `new_alert` ×10 — plus 1 frame sent (auth)
- Both scenarios flowed through the real ingestion → detection → correlation → WS pipeline

### HTTP requests triggered
- **38 API GETs in 30s, in 3 invalidation flush cycles** (2s throttle working: 32 WS frames in the 0–5s bucket collapsed into 2 flush cycles)

| Flush | Requests | Paths refetched |
|-------|----------|-----------------|
| t=376ms | 23 | executive, alerts list, severity-distribution, alerts counts ×2, notifications unread-count + history |
| t=3767ms | 2 | alerts list, executive |
| t=15.1s | 13 | executive, alerts list, severity-distribution, alerts counts ×2, notifications unread-count + history |

### Verified: targeted invalidation works as designed
- `security_feed` → **only** `siem/executive` refetched
- `new_alert` → alerts + executive + severity-distribution refetched; **`top-risky-hosts` and `attack-timelines` were NOT refetched** (no storm)
- LiveFeed messages never produced `/events` HTTP requests (store-only path) ✅

### Observed inefficiencies
1. **Burst sizes inflated by error retries** — the 23-request burst is mostly React Query's default 3 retries on the failing `executive` (500) and `alerts` (422) queries.
2. **Notification bell refetches per `new_alert`, unthrottled** — `TopNav` `NotificationCenter` subscribes to every `new_alert` WS message and invalidates `["notifications"]`, causing `unread-count` + `history` refetch **10× in 30s** — and these are the two slowest endpoints (~1.4–1.5s avg each, see §8). This bypasses the 2s invalidation throttle.

---

## 8. API timings (whole session)

| Endpoint | Count | Avg | Min | Max |
|----------|-------|-----|-----|-----|
| GET /api/v1/notifications/unread-count | 10 | **1396ms** | 346ms | **2823ms** |
| GET /api/v1/notifications/history | 10 | **1487ms** | 369ms | **2856ms** |
| POST /api/v1/simulation/run/brute_force_attack | 1 | 1030ms | — | — |
| GET /api/v1/siem/executive | 8 | 303ms | 79ms | 494ms | *(all 500)* |
| GET /api/v1/alerts (dashboard list) | 4 | 298ms | 144ms | 374ms | *(all 422)* |
| GET /api/v1/siem/top-risky-hosts | 1 | 520ms | — | — |
| GET /api/v1/siem/severity-distribution | 2 | 424ms | 386ms | 462ms |
| GET /api/v1/siem/attack-timelines | 1 | 701ms | — | — |
| GET /api/v1/system/health | 1 | 733ms | — | — |
| POST /api/v1/auth/login | 1 | 899ms | — | — |
| POST /api/v1/telemetry/events | 9 | 830ms | 506ms | 1163ms |

**Slowest by far: the two notifications endpoints (~1.4–1.5s avg, up to 2.8s)** — made worse by being refetched on every `new_alert`. `telemetry/events` (avg 830ms) is also slow, and 20 of its posts were aborted mid-flight by navigation (see §11).

---

## 9. UI responsiveness

- **Long tasks (>50ms main-thread blocks): 0** across the entire session — no jank observed, even during the 32-message WS burst and flush cycles
- **Paints:** first-paint / first-contentful-paint @ 1244ms on `/login`
- **Live feed:** "Live feed: Connected" (WS established with auth)
- Recharts emitted a warning that a chart container measured -1×-1 (width/height not yet laid out when mounted) — cosmetic, dev-mode only

---

## 10. Console / runtime errors

- **Uncaught page errors: 0**
- **Console errors/warnings: 32**
  - 16× `Failed to load resource: 500` → `siem/executive` (and events-trend)
  - 8× `Failed to load resource: 422` → `alerts?sort=-created_at`
  - 4× `Failed to load resource: 401` (expected pre-login session probes)
  - 2× React hydration `nonce` prop mismatch warnings (`ThemeScript` — pre-existing dev warning)
  - 2× Recharts width/height warning
- **Failed/aborted requests: 20** — 18× `POST /api/v1/telemetry/events` aborted (`ERR_ABORTED`, killed by page navigation during the reload test) + 2 RSC prefetch aborts

---

## 11. Real-data verification

| Source | Status | Data |
|--------|--------|------|
| `/api/v1/siem/executive` | ❌ **500** | — (KPI row shows "Failed to load metrics") |
| `/api/v1/siem/events-trend` | ❌ **500** | — |
| `/api/v1/overview` | ❌ **500** | — |
| `/api/v1/alerts?sort=-created_at` | ❌ **422** | — ("Unable to load threats") |
| `/api/v1/siem/severity-distribution` | ✅ real | total 279: critical 179 (64.2%), high 100 (35.8%) |
| `/api/v1/siem/top-risky-hosts` | ✅ real | e.g. `sim-analyst-host` risk 100, 5 active alerts, detailed factors |
| `/api/v1/system/health` | ✅ real | ready; database ok, job queue ok, ws_pubsub memory, redis not configured |

**Dashboard DOM error states present:** "Failed to load metrics" (SecurityKpis) and "Unable to load threats" (ActiveThreats) — both caused by the two API bugs below, **not** by the performance work's intent. The KPI grid renders empty because its data source 500s.

---

## 12. Runtime bugs discovered (root causes, evidence-backed)

### BUG A — `executive_summary` 500 (dashboard KPI row + trend chart broken) — **regression from perf fix**
`backend/app/services/siem_analytics.py:455`
```python
Event.severity.in_("high", "critical"),
```
`ColumnOperators.in_()` takes **one iterable**; two positional args raise `TypeError: ColumnOperators.in_() takes 2 positional arguments but 3 were given` (reproduced in the venv). The optimized inline trend query in `executive_summary` never worked. Fix shape: `Event.severity.in_(["high", "critical"])`.

### BUG B — `events_trend` 500 — **same regression, same file, line 110**
Identical `Event.severity.in_("high", "critical")` inside `events_trend`'s conditional aggregation → same TypeError. Breaks the analytics page's trend view.

### BUG C — `/api/v1/overview` 500 (onboarding "Add a host" step can never complete)
`backend/app/routers/ws.py` `overview()` runs `asyncio.gather` with **5 concurrent `db.execute()` calls on a single `AsyncSession`** → `sqlalchemy.exc.InvalidRequestError: This session is provisioning a new connection; concurrent operations are not permitted`. Pre-existing, unrelated to the perf fix. Needs 5 sequential queries or separate sessions.

### BUG D — ActiveThreats 422 (dashboard "Active Threats" panel broken)
`frontend/components/dashboard/sections/ActiveThreats.tsx` sends `sort=-created_at`, but the alerts endpoint's `SortOrder` enum (`backend/app/utils/query.py:23-29`) only allows `newest | oldest | severity | risk_score | host_name | alert_count` → 422. Default (`newest`) already sorts `created_at DESC`, so the fix shape is to drop the param or send `sort=newest`.

### BUG E — Onboarding gating incomplete (see §5)
Dismissing only the wizard leaves checklist + coach enabled → all 7 onboarding queries still fire per page load.

### BUG F — Notification bell refetch-per-alert (unthrottled)
`frontend/components/layout/TopNav.tsx` `NotificationCenter` → `useWsMessages(["new_alert"], refresh)` invalidates `["notifications"]` on **every** `new_alert`. With the two slowest endpoints (~1.4s avg each), 10 alerts cost ~28s of client request time in 30s. This bypasses the 2s throttle that gates the rest of the dashboard.

---

## 13. Verdict on the performance work (runtime-measured)

**Working as intended:**
- ✅ Targeted WS invalidation (no `top-risky-hosts`/`attack-timelines` storm on `new_alert`; `security_feed` → executive only)
- ✅ 2s flush throttle (32 WS frames in 5s → 2 flush cycles; 38 refetches/30s incl. retry noise)
- ✅ Idle dashboard makes zero HTTP requests (no polling)
- ✅ LiveFeed push-only (no HTTP per feed message)
- ✅ Zero long tasks / no main-thread jank during traffic bursts
- ✅ Onboarding request dedupe across consumers via shared React Query keys

**Undone by bugs at runtime:**
- ❌ KPI row, trend chart, and Active Threats panel all show error states (Bugs A, B, D)
- ❌ Onboarding savings (7 → 0) do not materialize (Bug E)
- ❌ Per-alert notification refetches add ~2 slow requests per alert (Bug F)
- ❌ Error retries (default 3) amplify every failing refetch, inflating burst sizes

**Net:** the *mechanism* of the fix is correct and measurable, but the runtime experience is currently worse than the report claims because the executive/trend optimization introduced a crash (Bugs A/B) and pre-existing contract mismatches (C/D) surface on the same dashboard.

---

## 14. Notes / cleanup

- **No code changed; nothing committed or pushed.** The root-404 was confirmed and left as-is.
- The measurement script lives at `frontend/runtime-verify.mjs` (re-runnable: `node frontend/runtime-verify.mjs`).
- The two scenario runs created simulated events/alerts on `sim-analyst-host` (source=simulation, excluded from dashboard via `EXCLUDE_SIMULATED_FROM_DASHBOARD=true`). They can be removed with `DELETE /api/v1/simulation/purge` (admin) if desired.
- Dev-mode caveats: React StrictMode doubles effect-driven requests; turbo dev compiles routes on first visit (login 9.4s was first-compile dominated). A production build (`next build && next start`) would report lower, steadier numbers.