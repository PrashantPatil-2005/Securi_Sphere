# UI Improvement Plan — SecuriSphere

Last updated: July 2026

A phased plan to polish the dashboard, fix inconsistencies, and make the SOC workflow feel premium on desktop and mobile. Builds on the post-redesign foundation (`frontend/REDESIGN_AUDIT.md`) and recent AI/UX work (`docs/AI_AND_UX_ROADMAP.md`).

---

## Current state (honest snapshot)

### What already works
- Cohesive dark SOC aesthetic (glass panels, ambient gradient, Inter typography)
- Strong **dashboard** reference (`app/(dashboard)/page.tsx`) — KPIs, widgets, empty states with CTAs
- App shell with grouped sidebar, TopNav, command palette, AI assistant FAB
- TanStack Query patterns: skeletons, `QueryError`, refetch opacity
- Auth split-panel layout with motion
- Virtualized lists/tables for performance

### Main debt
| Area | Problem |
|------|---------|
| **Two styling systems** | Auth uses `Button`/`Input`; ~15 dashboard pages use raw `.btn-primary` / `.input-siem` |
| **Missing primitives** | No shared `Dialog`, `Drawer`, `Select`, `FilterBar`, `Tabs` |
| **Mobile alerts** | Split-pane investigation stacks below list; empty pane always visible |
| **Light mode** | Severity badges and glass hover tuned for dark only |
| **Search page** | Results look like debug output vs polished alert/event rows |
| **Accessibility** | Modals lack `role="dialog"`, focus trap, `aria-modal` |
| **Token drift** | Chart blue `#4c9aff` ≠ UI accent `#3b82f6` |

---

## Goals

1. **Feel like one product** — same components, spacing, and motion everywhere
2. **Analyst-first on any screen** — alerts investigation works on tablet/phone
3. **Accessible by default** — overlays, keyboard nav, reduced motion respected
4. **Fast to ship** — small PRs per sprint, dashboard as the quality bar

---

## Phase 1 — Foundation (1–2 weeks)

*Unblock everything else. Highest leverage.*

### 1.1 Shared overlay primitives
**New components:** `Dialog`, `Drawer`, `Sheet` in `components/ui/`

| Requirement | Detail |
|-------------|--------|
| ARIA | `role="dialog"`, `aria-modal`, `aria-labelledby` |
| Keyboard | Escape closes, focus trap, return focus on close |
| Motion | CSS slide/fade; respect `data-reduced-motion` |
| Migrate | Host enrollment modal, `HostRiskDrawer`, `CommandPalette`, `AIAssistantPanel` |

**Files:** `hosts/page.tsx`, `HostRiskDrawer.tsx`, `CommandPalette.tsx`, `AIAssistantPanel.tsx`

### 1.2 Form control system
**Extend:** `Button`, `Input` + **add** `Select`, `Checkbox`, `Label`

- Map existing `.btn-primary`, `.btn-ghost`, `.input-siem` to component variants
- One migration path: list pages first (alerts → hosts → events → search → rules)
- Stop adding raw class strings on new code

### 1.3 Design token cleanup
- Add `--accent-foreground` to `globals.css`
- Align `lib/design/chartTheme.ts` primary with `--accent`
- Fix `.glass-panel:hover` for light theme (use `var(--sidebar-hover)` not hardcoded white)
- Severity badges: CSS-variable-based (`.badge-critical` etc.) for dark + light

**Acceptance:** Toggle light/dark — badges, glass, charts look intentional in both.

---

## Phase 2 — Critical workflows (1–2 weeks)

*Where analysts spend time.*

### 2.1 Mobile alerts investigation
**Problem:** On `< lg`, selecting an alert shows investigation pane below a long list.

**Solution:**
- Desktop: keep side-by-side split (`lg:grid-cols-2`)
- Mobile/tablet: **bottom sheet drawer** when alert selected (reuse Drawer primitive)
- Hide empty “Select an alert” pane on mobile until selection

**Files:** `alerts/page.tsx`, `AlertInvestigationPane.tsx`

### 2.2 Search results redesign
**Target:** Match events/alerts visual language.

- `SeverityBadge` on each result row
- Deep links: alerts → `/alerts?selected=`, events → `/events`
- Group by type (Events / Alerts / Hosts) in `Panel` sections
- NL search result: show generated query + “Edit query” link to SIEM mode

**Files:** `search/page.tsx`

### 2.3 Collapsible filter bar
**Problem:** `TimeRangeBar` + filter row on every list page = vertical clutter.

**New:** `FilterBar` component
- Always visible: time range + primary filter
- “More filters” expands secondary fields
- Sticky on scroll (optional)

**Apply to:** events, alerts, hosts, offenses, audit, notifications

### 2.4 Reports page alignment
- Replace `text-2xl font-bold` / raw yellow with `PageHeader` + `StatCard`
- Use `chartTheme.ts` for all chart colors

**Files:** `reports/page.tsx`, legacy chart components

---

## Phase 3 — Polish & consistency (1 week)

### 3.1 Empty state system
**Standardize** `EmptyState` usage on all list pages:

| Page | Icon | CTA |
|------|------|-----|
| Alerts | `Bell` | “Run simulation” |
| Hosts | `Server` | “Add host” |
| Events | `Activity` | “Adjust time range” |
| Search | `Search` | “Try natural language” |
| Offenses | `ShieldAlert` | “View alerts” |

Dashboard already does this well — replicate pattern.

### 3.2 AuthGuard layout flash
- Render `AppShell` chrome immediately; skeleton only inside `main`
- Eliminates sidebar pop-in after auth check

**Files:** `AuthGuard.tsx`, `AppShell.tsx`

### 3.3 Responsive tables
**`< md`:** card layout fallback for `VirtualDataTable`
- Host row → card with name, status badge, last seen, actions
- Fewer fixed column widths on narrow screens

**Files:** `VirtualDataTable.tsx`, `hosts/page.tsx`

### 3.4 Navigation cleanup
- Collapsed sidebar: show icon-only Settings + Profile
- Remove duplicate theme toggle (keep in user menu OR sidebar, not both)
- Active nav: highlight parent for nested routes where applicable

---

## Phase 4 — Delight & power-user (optional)

| Item | Effort | Impact |
|------|--------|--------|
| Subtle page fade on route change (respect reduced motion) | Low | Medium |
| Sidebar width persist in `localStorage` | Low | Low |
| HelpTooltip click-to-toggle on touch | Low | Medium |
| Command palette `listbox` + `aria-activedescendant` | Medium | Medium |
| Global offline / WS reconnect banner in TopNav | Medium | High |
| Toast position avoids AI FAB overlap | Low | Low |
| Rules page `Panel` layout + form components | Medium | Medium |

---

## Page-by-page priority matrix

| Page | Priority | Main work |
|------|----------|-----------|
| **Alerts** | P0 | Mobile drawer, filter bar, form components |
| **Search** | P0 | Result redesign, NL UX |
| **Hosts** | P1 | Dialog migration, responsive table cards |
| **Dashboard** | — | Reference — minor chart token fix only |
| **Simulation** | — | Already strong — help tooltips done |
| **Events / Offenses** | P1 | Filter bar, empty states |
| **Reports** | P1 | StatCard + chart tokens |
| **Rules** | P2 | Panel structure, dense form cleanup |
| **System** | P2 | Pipeline cards polish |
| **Settings / Profile** | P2 | Form components |

---

## Accessibility checklist (per PR)

- [ ] Overlays: dialog role, focus trap, Escape
- [ ] Forms: labels tied to inputs (`htmlFor` / `id`)
- [ ] Status: not color-only (badge text + icon where needed)
- [ ] Motion: Framer Motion checks `reducedMotion` from `ThemeProvider`
- [ ] Keyboard: command palette, sidebar, tables navigable
- [ ] Touch: tooltips toggle on tap

---

## Suggested sprint order

```
Sprint UI-1  →  Dialog/Drawer + token cleanup + Select component
Sprint UI-2  →  Alerts mobile drawer + FilterBar
Sprint UI-3  →  Search redesign + form migration (alerts, hosts)
Sprint UI-4  →  Empty states + responsive tables + reports
Sprint UI-5  →  Nav polish + a11y pass + optional motion
Sprint UI-6  →  Phase 4 delight (command palette a11y, connection banner, sidebar persist, toast offset, rules Panel)
Sprint UI-7  →  Settings/Profile forms, System pipeline polish, incidents + simulation form migration
Sprint UI-8  →  Maintenance cleanup: alerts/events/hosts filter inputs + search mode toggles → Input/Button
```

Each sprint: one PR, screenshot before/after in description, `npx tsc --noEmit` + spot-check light/dark.

---

## Out of scope (separate projects)

- Full design rebrand / new logo system
- Custom illustration library
- Mobile-native app
- Drag-and-drop dashboard builder
- White-label theming for multi-tenant

---

## Success metrics (qualitative)

After Phase 2, a new user should be able to:

1. Triage an alert on a phone without endless scrolling
2. Search in plain English and understand results at a glance
3. Switch light/dark without broken badges or glass
4. Open any modal with keyboard only

After Phase 3, every list page should feel as polished as the dashboard overview.

---

## Quick wins you can do today (< 1 hour each)

1. Fix `text-accent-foreground` undefined in `AIAssistantPanel.tsx` → use `text-foreground`
2. Add “View alerts” link on simulation step 3 (done) — extend to offenses empty state
3. Align one chart on dashboard to `chartTheme.ts` as proof
4. Add `aria-label` to sidebar theme toggle

---

## Related docs

- `frontend/REDESIGN_AUDIT.md` — what changed in the first redesign
- `docs/AI_AND_UX_ROADMAP.md` — AI assistant + command palette (shipped)
- `docs/WRAP_UP.md` — overall product status

**Next step:** ~~Sprint UI-5~~ ~~Sprint UI-6~~ ~~Sprint UI-7~~ ~~Sprint UI-8~~ **UI improvement plan complete.** All dashboard list pages now use shared `Input`/`Button` components for filter rows and primary actions. Remaining raw `.btn-ghost` on pagination, ExportMenu, simulation nav links, and notifications "Mark all read" is intentional low-traffic markup — no further sprints planned.

### Sprint UI-8 changelog (shipped)
- **Alerts** — FilterBar rule/search fields → `Input`; bulk action bar → `Button variant="ghost" size="sm"`
- **Events** — FilterBar event type and keyword fields → `Input`
- **Hosts** — add-host form and hostname filter → `Input`/`Button`; table Enroll/Re-enroll and copy actions → `Button variant="ghost" size="sm"`
- **Search** — main query field → `Input` (with search icon); mode toggles, example/saved chips, and "Edit query" → `Button variant="ghost"`

### Sprint UI-7 changelog (shipped)
- **Settings** — search field and theme picker migrated to `Input`/`Select`; notifications tab already used shared form components
- **Profile** — explicit field ids; `Button` loading states on save/password actions
- **System** — pipeline layer cards use `glass-panel` layout; `StatCard` row for fleet metrics; Readiness/Configuration panels aligned with rules/reports typography
- **Incidents** — create form wrapped in `Panel` with `Input`/`Button`; investigation note form and status actions migrated
- **Simulation** — host `Select` and wizard `Button` controls migrated (step-3 nav links remain anchor-styled)

### Sprint UI-6 changelog (shipped)
- **CommandPalette** — `listbox` + `aria-activedescendant` combobox pattern; Home/End navigation; active option scroll-into-view; options without nested buttons
- **ConnectionBanner** — global offline / WebSocket reconnect notice in TopNav; dismissible; auto-clears on reconnect (`useOnline` + `useWsConnected`)
- **Sidebar** — collapsed state and width persisted to `localStorage` (`securisphere-sidebar-collapsed`, `securisphere-sidebar-width`)
- **Toast** — repositioned to `bottom-24 right-6` so toasts clear the AI assistant FAB
- **Rules** — detection tab wrapped in `Panel` sections (create form + rules list); correlation form uses Panel body layout

### Sprint UI-5 changelog (shipped)
- **Sidebar** — icon-only Settings + Profile when collapsed; nested-route active highlighting (`isNavActive`); `aria-current="page"` on nav links; `aria-label` on sign out; duplicate theme toggle removed (theme lives in TopNav user menu)
- **HelpTooltip** — click-to-toggle on coarse-pointer devices with outside-dismiss
- **EmptyState** — icon container styling, `role="status"`, optional `onAction` callback; search no-results CTA scrolls to natural-language panel
- **PageTransition** — subtle route-change fade in `AppShell` (skipped when reduced motion is enabled)

### Sprint UI-4 changelog (shipped)
- **`VirtualDataTable`** — `renderMobileCard`, rich empty props (`emptyTitle`, `emptyIcon`, `emptyAction`), mobile card layout via `useMediaQuery`
- **Auth layout** — `AppShell` wraps `AuthGuard` (chrome visible during auth load)
- **Reports** — `StatCard`, `Select`, icons, "What's included" panel
- **Empty states** — icons + CTAs on alerts, events, hosts, offenses, timeline, audit, network, metrics, incidents, notifications
- **Mobile cards** — hosts + events tables

### Sprint UI-3 changelog (shipped)
- **Search** — polished result rows with `SeverityBadge`, deep links, grouped `Panel` sections
- NL search — `Input`/`Button`, generated query card with "Edit query"
- **Analytics, Audit, Notifications** — `FilterBar` + `Input`/`Select`
- **Rules** — forms migrated to `Input`/`Select`/`Button`, `SeverityBadge` on rules

### Sprint UI-1 changelog (shipped)
- `Dialog`, `Drawer`, `Select` components with focus trap + Escape
- Theme-aware severity badges + `--accent-foreground`
- Chart colors aligned to UI accent
- Migrated: host enrollment modal, host risk drawer, command palette a11y, AI assistant panel a11y

### Sprint UI-2 changelog (shipped)
- `FilterBar` — collapsible primary/more filters with active count badge
- `TimeRangeBar` — inline variant (slimmer on list pages)
- **Alerts** — bottom-sheet investigation drawer on mobile/tablet (`< lg`)
- **Events, Hosts** — migrated to FilterBar + Select
