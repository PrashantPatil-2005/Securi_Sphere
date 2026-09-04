# Member 2 — Frontend & Dashboard

> Next.js frontend, dashboard, alerts UI, hosts UI, events UI, analytics, MITRE visualization, offenses/incidents UI, settings, search, reports UI, general UI/UX.

---

## 1. What This Module Does

Member 2 owns the **entire frontend** of the Securi Sphere SIEM platform — a Next.js 14 single-page application that provides the SOC (Security Operations Center) analyst interface:

- **SOC Dashboard** — executive KPIs, active threats, severity breakdown, host risk, live feed
- **Alert Management** — list with triage actions, investigation pane, bulk operations
- **Offense/Incident Tracking** — grouping, timelines, promotion workflow
- **MITRE ATT&CK Heatmap** — visual matrix with click-to-drill-down
- **UEBA Viewer** — anomaly list with summary cards
- **Event Browser** — filtering, detail drawer, raw JSON view
- **Host Management** — status, risk scores, agent health
- **Attack Lab** — simulation runner, results, run history
- **Timeline** — attack timeline replay with play/pause/step controls
- **Search** — global search with saved searches
- **Reports** — compliance report generation
- **AI Assistant** — floating copilot panel for alert explanation
- **Real-time Updates** — WebSocket live feed of alerts and host status
- **Dark Mode** — optimized SOC aesthetic with glass panels

---

## 2. Main Files & Folders

### App Router Pages (`frontend/app/`)

| Route | File | Purpose |
|-------|------|---------|
| `/` | `(dashboard)/page.tsx` | Executive KPIs + security timeline |
| `/alerts` | `(dashboard)/alerts/page.tsx` | Alert list with triage |
| `/alerts/[id]` | `(dashboard)/alerts/[id]/page.tsx` | Alert detail |
| `/hosts` | `(dashboard)/hosts/page.tsx` | Host list with status |
| `/hosts/[id]` | `(dashboard)/hosts/[id]/page.tsx` | Host detail |
| `/events` | `(dashboard)/events/page.tsx` | Event browser |
| `/offenses` | `(dashboard)/offenses/page.tsx` | Offense list |
| `/incidents` | `(dashboard)/incidents/page.tsx` | Incident management |
| `/mitre` | `(dashboard)/mitre/page.tsx` | MITRE ATT&CK heatmap |
| `/ueba` | `(dashboard)/ueba/page.tsx` | UEBA anomaly viewer |
| `/analytics` | `(dashboard)/analytics/page.tsx` | Charts and metrics |
| `/timeline` | `(dashboard)/timeline/page.tsx` | Attack timeline |
| `/search` | `(dashboard)/search/page.tsx` | Global search |
| `/reports` | `(dashboard)/reports/page.tsx` | Report generation |
| `/settings` | `(dashboard)/settings/page.tsx` | Platform settings |
| `/simulation` | `(dashboard)/simulation/page.tsx` | Attack Lab |
| `/network` | `(dashboard)/network/page.tsx` | Network topology |
| `/threat-scores` | `(dashboard)/threat-scores/page.tsx` | Host threat scores |
| `/rules` | `(dashboard)/rules/page.tsx` | Correlation rules |
| `/audit` | `(dashboard)/audit/page.tsx` | Audit log viewer |
| `/metrics` | `(dashboard)/metrics/page.tsx` | Detailed metrics |
| `/maintenance` | `(dashboard)/maintenance/page.tsx` | Maintenance windows |
| `/notifications` | `(dashboard)/notifications/page.tsx` | Notification settings |
| `/intel` | `(dashboard)/intel/page.tsx` | Threat intelligence |
| `/investigation` | `(dashboard)/investigation/page.tsx` | Investigation workspace |
| `/profile` | `(dashboard)/profile/page.tsx` | User profile + MFA |
| `/login` | `(auth)/login/page.tsx` | Login page |
| `/register` | `(auth)/register/page.tsx` | Registration |

### Component Architecture (`frontend/components/`)

**130+ React components** organized by domain:

| Directory | Components | Purpose |
|-----------|-----------|---------|
| `components/alerts/` | 14 files | Alert list, detail, filters, triage, MITRE, offense links |
| `components/analytics/` | 4 files | Summary panel, host risk trends, threat scores, UEBA anomalies |
| `components/attack-lab/` | 12 files | Simulation runner, results, history, guided investigation |
| `components/charts/` | 5 files | Analytics charts, event trends, severity charts |
| `components/dashboard/` | 10 files | Dashboard sections (KPIs, live feed, severity, host risk) |
| `components/design-system/` | 18 files | Reusable primitives (Button, Card, DataTable, Badge, etc.) |
| `components/events/` | 8 files | Event list, detail drawer, filters, raw JSON |
| `components/hosts/` | 11 files | Host list, detail, enrollment, risk, agent health |
| `components/incidents/` | 7 files | Incident list, detail, create form, notes |
| `components/layout/` | 7 files | AppShell, Sidebar, TopNav, BrandLogo |
| `components/mitre/` | 3 files | MITRE matrix, drilldown, technique detail |
| `components/offenses/` | 10 files | Offense list, detail, actions, timeline |
| `components/timeline/` | 6 files | Timeline list, detail, replay player |
| `components/ueba/` | 3 files | UEBA anomaly list, summary cards |
| `components/ui/` | 20 files | Base UI components (Button, Dialog, Drawer, Toast, etc.) |
| `components/virtual-table/` | 2 files | Virtualized data table for performance |
| `components/profile/` | 1 file | MFA security panel |
| `components/rules/` | 2 files | Correlation rule editor, feedback insights |
| `components/search/` | 2 files | Saved searches panel, search results |
| `components/settings/` | 3 files | Notification rules, playbooks, team management |
| `components/guards/` | 2 files | Auth guard, route guard |
| `components/onboarding/` | 2 files | Onboarding wizard, activation coach |

### Library & Utilities (`frontend/lib/`)

| File/Dir | Purpose |
|----------|---------|
| `lib/api.ts` | API client with auth handling |
| `lib/api/endpoints.ts` | API endpoint definitions |
| `lib/hooks/` | 21 custom React hooks (useAlerts, useEvents, useHosts, etc.) |
| `lib/types/` | TypeScript type definitions (alert, event, host, offense, etc.) |
| `lib/websocket.tsx` | WebSocket connection management |
| `lib/queryClient.ts` | TanStack Query client setup |
| `lib/buildQuery.ts` | Query string builder |
| `lib/dashboardWidgets.ts` | Dashboard widget configuration |
| `lib/featureFlags.tsx` | Feature flag system |
| `lib/design/` | Chart theme, design tokens |
| `lib/theme/` | Theme provider, dark mode script |
| `lib/utils/cn.ts` | Tailwind class merging utility |

### State Management

- **TanStack Query** for server state (API data caching, refetching)
- **React Context** for global state (theme, auth, WebSocket)
- **URL state** for filters, pagination, search params

### Testing (`frontend/__tests__/` + `frontend/e2e/`)

| Directory | Tests | Purpose |
|-----------|-------|---------|
| `__tests__/` | 19 test files | Unit tests (Vitest + React Testing Library) |
| `e2e/` | 7 spec files | E2E tests (Playwright) |

---

## 3. Architecture / Design

### Next.js App Router

```
frontend/app/
├── (auth)/              # Auth route group (login, register, etc.)
│   └── layout.tsx       # Auth-specific layout (centered, no sidebar)
├── (dashboard)/         # Dashboard route group (protected)
│   ├── layout.tsx       # Dashboard layout (sidebar + topnav)
│   ├── page.tsx         # Home/dashboard page
│   ├── alerts/          # Alert pages
│   ├── hosts/           # Host pages
│   └── ...              # 24+ page routes
├── layout.tsx           # Root layout
├── globals.css          # Global styles
└── not-found.tsx        # 404 page
```

### Component Hierarchy

```
AppShell (layout/AppShell.tsx)
├── Sidebar (layout/Sidebar.tsx)
│   └── Navigation links
├── TopNav (layout/TopNav.tsx)
│   ├── SearchBar
│   ├── CommandPalette
│   └── User menu
├── DashboardProviders (layout/DashboardProviders.tsx)
│   ├── ThemeProvider
│   ├── QueryClientProvider
│   └── WebSocketProvider
└── Page Content
    └── Domain-specific components
```

### Design System

Reusable UI primitives in `components/design-system/` and `components/ui/`:

- **Primitives:** Button, Input, Select, Checkbox, Label
- **Containers:** Card, Panel, Sheet, Drawer, Dialog
- **Data:** DataTable, VirtualDataTable, Pagination, SortSelect
- **Feedback:** Toast, Badge, SeverityBadge, LoadingState, EmptyState, ErrorState
- **Navigation:** Tabs, FilterChip, SearchBar, TimeRangeBar

### Real-Time Updates

```
WebSocket Connection (lib/websocket.tsx)
    ↓
WebSocketProvider (React Context)
    ↓
useAlerts(), useHosts(), useEvents() hooks
    ↓
Components re-render on new data
```

---

## 4. Important Implementation Details

- **Virtualized lists** for alerts/events (TanStack Virtual) — handles 10k+ rows
- **CSP nonces** generated per-request in Next.js middleware
- **Dark mode** as default with toggle in settings
- **Glass panels** with backdrop-blur for SOC aesthetic
- **Keyboard navigation** throughout (arrow keys, Enter, Escape)
- **Command palette** (Cmd+K) for quick navigation
- **Cursor-based pagination** for large datasets
- **Optimistic updates** for mutation operations

---

## 5. Technologies Used

| Technology | Purpose |
|-----------|---------|
| Next.js 14 (App Router) | React framework with SSR |
| TypeScript | Type safety |
| TailwindCSS | Utility-first CSS |
| TanStack Query | Server state management |
| TanStack Virtual | Virtualized lists |
| React Hook Form | Form handling |
| Recharts | Charts and visualizations |
| Vitest | Unit testing |
| React Testing Library | Component testing |
| Playwright | E2E testing |
| ESLint | Code linting |
| PostCSS + autoprefixer | CSS processing |

---

## 6. Testing

### Running Tests

```bash
cd frontend

# Unit tests
npm run test:unit

# TypeScript type check
npx tsc --noEmit

# Lint
npm run lint

# Build (verifies all imports and types)
npm run build

# E2E tests (requires Playwright)
npx playwright install chromium
npx playwright test

# Specific E2E test
npx playwright test e2e/smoke.spec.ts
```

### Test Coverage Areas

- Dashboard rendering with mock data
- Alert list filtering and triage actions
- Host detail page with risk scores
- Event browser with detail drawer
- MITRE heatmap rendering
- UEBA anomaly list
- Offense/incident management
- Search functionality
- WebSocket reconnection
- Auth guard behavior
- Dark mode toggling
- Responsive layout

---

## 7. Screenshots / Diagrams for Report

Include these in the final report:

| Screenshot | Description |
|-----------|-------------|
| Dashboard overview | KPIs, active threats, severity breakdown, live feed |
| Alert investigation pane | Alert detail with related events, MITRE mapping, AI summary |
| MITRE ATT&CK heatmap | Full technique matrix with drill-down |
| Attack Lab simulation | Simulation runner with real-time progress |
| Timeline replay | Play/pause/step controls for attack reconstruction |
| Dark mode SOC aesthetic | Glass panels, ambient gradient, professional look |
| Command palette | Quick navigation overlay |
| Virtualized alerts table | Performance demonstration with 10k+ rows |

---

## 8. Possible Viva Questions

### Architecture
1. **Q: Why Next.js over a plain React SPA?**
   A: App Router provides file-based routing, middleware for CSP nonces, SSR capability, and optimized bundling. Built-in API routes for BFF pattern if needed.

2. **Q: How do you manage state across the dashboard?**
   A: TanStack Query for server state (automatic caching, refetching, optimistic updates). React Context for global state (theme, auth). URL state for filters and pagination.

### Performance
3. **Q: How do you handle rendering thousands of alerts?**
   A: TanStack Virtual for virtualized lists — only renders visible rows. Cursor-based pagination for API queries. Debounced search inputs.

4. **Q: How does the real-time WebSocket work?**
   A: WebSocket connection managed in `lib/websocket.tsx`. Events published via Redis pub/sub reach all frontend instances. Components subscribe via custom hooks.

### UI/UX
5. **Q: How is the design system structured?**
   A: Two layers: `design-system/` for app-specific primitives (KpiCard, DataTable) and `ui/` for generic components (Button, Dialog, Toast). Both follow consistent theming.

6. **Q: How do you handle authentication in the frontend?**
   A: HttpOnly cookies managed by backend. Frontend checks auth state via API calls. AuthGuard component wraps protected routes. Automatic redirect to login on 401.
