# Securi Refactoring Migration Plan

## Current State
- **Frontend**: 195 source files (42 pages, 96 components, 39 lib)
- **Backend**: 188 source files (37 routers, 65 services, 32 models, 19 schemas)
- **Key Issues**: Duplicated patterns, god files, inline schemas, no shared hooks, deep provider nesting

---

## Phase 1: Backend Cleanup (Do First — Low Risk)

### 1.1 Extract `main.py` into components
**Why**: `main.py` is 345 lines mixing scheduler jobs, health endpoints, WebSocket, agent bundles, and 37 router mounts.

| Move | From | To | Explanation |
|------|------|----|-------------|
| Scheduler jobs (8 functions) | `main.py:67-119` | `app/scheduler.py` | Jobs are pure functions, no coupling to app |
| Health endpoints | `main.py:251-272` | `app/routers/health.py` | Standard router, already has `core/health.py` |
| WebSocket endpoints | `main.py:299-334` | `app/routers/ws.py` | Auth logic + WS token, belongs in router |
| Agent bundle endpoints | `main.py:337-345` | `app/routers/agent.py` | Already partially there |
| App factory | `main.py` remaining | `app/app.py` | `create_app()` function for clean startup |
| Lifespan | `main.py:122-176` | `app/app.py` | Lifespan is app-level, not in main |

### 1.2 Move inline schemas to `schemas/`
**Why**: 15+ routers define Pydantic models inline. This scatters API contracts.

| Router | Inline Models | Move To |
|--------|---------------|---------|
| `incidents.py` | `IncidentCreate`, `NoteCreate`, `IncidentResponse`, `IncidentDetailResponse` | `schemas/incident.py` |
| `maintenance.py` | `MaintenanceCreate`, `MaintenanceResponse` | `schemas/maintenance.py` |
| `hosts.py` | `TokenListItem`, `RiskFactorItem`, `RiskHistoryItem`, `HostRiskResponse` | `schemas/host.py` |
| `threat_scores.py` | `ScoreResponse` | `schemas/threat_score.py` |
| `mitre.py` | `TechniqueResponse` | `schemas/mitre.py` |
| `correlation_rules.py` | 5 inline models | `schemas/correlation_rule.py` |
| `alert_rules.py` | `RuleCreate`, `RuleUpdate`, `RuleResponse` | `schemas/alert_rule.py` |
| `notifications.py` | 6 inline models | `schemas/notification.py` |
| `offenses.py` | `OffenseStatusUpdate` | `schemas/offense.py` |
| `backups.py` | 3 inline models | `schemas/backup.py` |
| `telemetry.py` | `TelemetryEventIn` | `schemas/telemetry.py` |
| `timeline.py` | Duplicate `EventResponse` | Use `schemas/event.py` |

### 1.3 Clean up dead structure
- Delete empty `app/security/` directory
- Add `__init__.py` to `app/schemas/`
- Add `__init__.py` to `app/schemas/` for proper package imports

---

## Phase 2: Frontend Structural (Medium Risk)

### 2.1 Reorganize `components/` root (22 flat files)
**Why**: 22 files at root level with mixed concerns.

| Move | From | To | Explanation |
|------|------|----|-------------|
| PaginationBar, CursorPaginationBar | `components/` | `components/pagination/` | Pagination is a cohesive feature |
| VirtualDataTable, VirtualList | `components/` | `components/virtual-table/` | Virtualization components |
| AuthGuard, RouteGuard | `components/` | `components/guards/` | Auth/route protection |
| ExportMenu | `components/` | `components/export/` | Export functionality |
| SortSelect | `components/` | `components/pagination/` | Sort is pagination-adjacent |
| TimeRangeBar | `components/` | `components/filters/` | Time range is a filter |
| CommandPalette | `components/` | `components/command/` | Command palette is standalone |
| ThemeScript | `components/` | `lib/theme/` | Theme is lib concern, not component |

### 2.2 Consolidate provider nesting
**Why**: 7 levels of providers in dashboard layout. Each adds re-render overhead.

Current: `ThemeProvider > AppProviders > ToastProvider > TimeRangeProvider > AssistantProvider > AppShell > AuthGuard > RouteGuard > ErrorBoundary`

Target: Create `app/(dashboard)/providers.tsx` that composes all providers into one wrapper. Keep AppShell + guards separate.

---

## Phase 3: Frontend Shared Hooks (High Impact)

### 3.1 Create entity-specific hooks
**Why**: 8+ pages duplicate `useQuery` + `api()` for the same entities.

| New Hook | Entities | Replaces |
|----------|----------|----------|
| `lib/hooks/useAlerts.ts` | alerts | Inline queries in alerts/page.tsx + mutations |
| `lib/hooks/useOffenses.ts` | offenses | Inline queries in offenses/page.tsx |
| `lib/hooks/useIncidents.ts` | incidents | Inline queries in incidents/page.tsx |
| `lib/hooks/useRules.ts` | alert_rules, correlation_rules | Inline queries in rules/page.tsx |
| `lib/hooks/useHosts.ts` | hosts | Extend existing `useHostsList` |
| `lib/hooks/useMetrics.ts` | metrics | Inline queries in metrics/page.tsx |
| `lib/hooks/useSimulation.ts` | simulation | Inline queries in simulation/page.tsx |
| `lib/hooks/useSearch.ts` | search | Inline queries in search/page.tsx |
| `lib/hooks/useAudit.ts` | audit | Inline queries in audit/page.tsx |
| `lib/hooks/useTimeline.ts` | timeline | Inline queries in timeline/page.tsx |

### 3.2 Create shared mutation hook
**Why**: 25+ locations duplicate `useMutation` + `toast()` + `invalidateQueries()`.

New hook: `lib/hooks/useEntityMutation.ts`
```ts
function useEntityMutation<TBody, TResponse>(options: {
  endpoint: string;
  method: "POST" | "PATCH" | "PUT" | "DELETE";
  invalidates: QueryKey[];
  successMessage: string;
}): { mutate: ..., isPending: ... }
```

### 3.3 Split oversized `useApiQuery.ts`
**Why**: 222-line file with 7 unrelated hooks.

| Current | Move To |
|---------|---------|
| `usePaginatedResource`, `useCursorPaginatedResource` | `lib/hooks/usePaginatedQuery.ts` |
| `useSiemQuery` | `lib/hooks/useSiemQuery.ts` |
| `useAlertStatusMutation`, `useAlertBulkMutation` | `lib/hooks/useAlerts.ts` |
| `useHostsList`, `useMaintenanceWindows` | `lib/hooks/useHosts.ts` |
| `useTimeQueryKey` | `lib/hooks/usePaginatedQuery.ts` |

---

## Phase 4: Frontend API Centralization

### 4.1 Create API endpoint constants
**Why**: API paths are scattered as string literals across 40+ files.

New file: `lib/api/endpoints.ts`
```ts
export const API = {
  AUTH: { LOGIN: "/api/v1/auth/login", ME: "/api/v1/auth/me", ... },
  ALERTS: { LIST: "/api/v1/alerts", ... },
  HOSTS: { LIST: "/api/v1/hosts", ... },
  ...
} as const;
```

### 4.2 Consolidate download logic
**Why**: `lib/download.ts` and `ExportMenu.tsx` duplicate blob download logic.

Keep `lib/download.ts` as the canonical implementation. Update `ExportMenu` to use it.

---

## Phase 5: Backend Service Layer (Higher Risk)

### 5.1 Create export factory
**Why**: 3 routers duplicate the same export pattern (format validation, query, build rows, call export function).

New: `app/services/export.py` with `ExportService.export(query, format, filename, row_builder)`

### 5.2 Create `ListQueryParams` dependency
**Why**: Every list endpoint repeats the same parameter declarations.

New: `app/schemas/common.py` with `ListQueryParams` model, used as `Depends()`.

---

## Execution Strategy

1. **Phase 1 first** — Backend changes are safer, no UI breakage possible
2. **Phase 2 next** — File moves only, no logic changes
3. **Phase 3 after** — New hooks are additive, existing code stays until migrated
4. **Phase 4 anytime** — String constant extraction is mechanical
5. **Phase 5 last** — Service layer changes need careful testing

Each phase will be a separate commit. Each file move will update all imports automatically.
