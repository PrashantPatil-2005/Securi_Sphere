# Securi — Production Readiness Audit

> **Reviewed:** 2026-08-05
> **Scope:** Full-stack (backend services, frontend UX, database, WebSocket, event pipeline)
> **Perspective:** SIEM deployment readiness (Defender XDR / CrowdStrike equivalent)

---

## Scores

| Category | Score |
|----------|-------|
| **Architecture** | **7.5 / 10** |
| **Code Quality** | **6.5 / 10** |
| **Performance** | **7.0 / 10** |
| **Security** | **6.0 / 10** |
| **Maintainability** | **6.0 / 10** |

---

## Critical Issues

### C1. Live API Keys and Secrets Committed in `.env` Files
**Files:** `.env:24`, `backend/.env:23`
**Category:** Security

A live HuggingFace API key and the JWT signing secret exist in `.env` files in the working directory. While `.gitignore` lists `.env`, these files may have been committed previously. The JWT secret, if compromised, allows forging arbitrary authentication tokens.

**Action:** Rotate all exposed keys immediately. Run `git log --all --full-history -- .env backend/.env` to verify commit history. Use `git filter-branch` or BFG Repo-Cleaner if secrets were committed.

---

### C2. Hardcoded Dev/Demo Passwords in Source Code
**File:** `backend/app/routers/auth.py:76-84`
**Category:** Security

```python
DEV_USER_PASSWORD = "testpass123"
DEMO_USER_PASSWORD = "Demo1234!"
```

These are seeded on startup when `environment == "development"` or `demo_mode == True`. If accidentally enabled in production, these are trivially guessable credentials for admin-level accounts. Passwords should be loaded from environment variables, not hardcoded.

---

### C3. Runtime Logs and Debug Files Committed to Repository
**Files:** `backend_run.txt` (248 lines), `frontend_run.txt` (72 lines), `backend/login.json`, `backend/reg.json`
**Category:** Broken Structure

Runtime output files and debug JSON payloads exist at the repository root and in `backend/`. These contain stack traces, connection warnings, and potentially sensitive request/response data. They are not caught by `.gitignore` patterns.

**Action:** Delete these files and add `*_run.txt`, `*.log`, `login.json`, `reg.json` to `.gitignore`.

---

### C4. Duplicate Auth Route Folders (Dead Code)
**Files:** `frontend/app/login/`, `frontend/app/register/`, `frontend/app/forgot-password/`, `frontend/app/reset-password/`
**Category:** Dead Code / Broken Structure

Root-level auth route folders exist alongside `(auth)` route group versions. While the root-level folders are empty (no `page.tsx`), they create confusion and route ambiguity in Next.js App Router. All page routes are correctly inside `(auth)/` but the empty folders should be removed.

**Action:** Delete the empty root-level auth folders.

---

## High Issues

### H1. `auth.py` Router is 457 Lines — Too Many Responsibilities
**File:** `backend/app/routers/auth.py`
**Category:** Large Component / Too Many Responsibilities

Handles: registration, login, MFA (5 endpoints), token refresh, logout, forgot/reset password, profile update, password change. This should be split into `auth.py`, `mfa.py`, `password.py`, and `profile.py`.

---

### H2. `siem_analytics.py` is a God Module (428 Lines)
**File:** `backend/app/services/siem_analytics.py`
**Category:** Large Component / Missing Abstraction

Contains all SIEM analytics queries: event trends, failed logins, severity distribution, MITRE stats, host health, executive summary, historical analytics, attack timelines. Each should be a separate service or method in a domain-specific module.

---

### H3. `detection.py` Mixes Engine and Rule Definitions (393 Lines)
**File:** `backend/app/services/detection.py`
**Category:** Large Component

Contains the detection engine loop AND all individual rule checker classes (SSH brute force, high CPU/memory/disk, service failures, agent offline). Rule classes should be in separate files under `services/detection/`.

---

### H4. Frontend Components Exceeding 300 Lines
**Files:**
- `components/rules/CorrelationRuleEditor.tsx` (483 lines)
- `components/intel/IntelPanels.tsx` (487 lines — two unrelated panels)
- `app/(dashboard)/alerts/page.tsx` (458 lines)
- `components/investigation/InvestigationWorkspacePane.tsx` (~350 lines)
- `components/layout/Sidebar.tsx` (~326 lines)

`IntelPanels.tsx` contains `ReferenceSetsPanel` (~345 lines) and `BuildingBlocksPanel` (~165 lines) — two completely independent components that share no state or logic.

---

### H5. Duplicate CRUD Boilerplate Across Routers
**Files:** `alert_rules.py`, `correlation_rules.py`, `building_blocks.py`, `playbooks.py`, `reference_sets.py`, `maintenance.py`, `saved_searches.py`
**Category:** Duplicate Code

Nearly every router repeats `select → scalar_one_or_none → 404` for GET/PATCH/DELETE. A generic CRUD helper or base router pattern would eliminate ~500 lines of duplication.

---

### H6. Duplicate Export Endpoint Pattern
**Files:** `alerts.py:86-121`, `events.py:68-106`, `hosts.py:88-104`, `audit.py:97-131`
**Category:** Duplicate Code

Four routers implement near-identical CSV/JSON/PDF export logic: query → format rows → call `export_csv`/`export_json`/`export_pdf`. A generic export endpoint factory would consolidate this.

---

### H7. Redundant `db.commit()` Calls in Routers
**Files:** `maintenance.py:79,102`, `saved_searches.py:57,84,103`, `offenses.py:204`, `reports.py:99,138,164`, `audit.py:125`, `backups.py:84`, `telemetry.py:81`, `system.py:245`
**Category:** Code Smell / Potential Bug

`get_db()` already commits on success. Explicit `await db.commit()` in 14+ locations causes double-commit. While usually a no-op on an already-committed session, it obscures transaction boundaries and can cause confusion during debugging.

---

### H8. Large Unbounded Queries (N+1 Pattern)
**Files:** `offenses.py:63`, `network.py:19`, `reports.py:67`, `threat_scores.py:25`, `mitre.py:59`
**Category:** Performance Bottleneck

```python
hosts = {h.id: h.name for h in (await db.execute(select(Host).limit(5000))).scalars().all()}
```

Loads all hosts (up to 5000) into memory to build a name lookup map on every request. Should use JOINs or targeted queries.

---

### H9. No Rate Limiting on Registration Endpoint
**File:** `backend/app/middleware/rate_limit.py:45-48`
**Category:** Security

Rate limiting only covers `/api/v1/auth` and `/api/v1/agent`. The `/api/v1/auth/register` endpoint has no dedicated rate limiting, allowing mass account creation when `ALLOW_REGISTRATION=true`.

---

### H10. Stale Documentation Contradicts Code
**Files:** `docs/ENTERPRISE_ROADMAP.md`, `docs/WRAP_UP.md`
**Category:** Dead Code

Documentation claims "Empty Alembic chain" (21 migrations exist), "No OIDC" (full implementation exists), "Migrations 001-005" (21 exist). These documents are misleading for new contributors.

---

### H11. Duplicate Navigation Definitions
**Files:** `frontend/components/layout/Sidebar.tsx:64-112`, `frontend/components/CommandPalette.tsx:68-95`
**Category:** Duplicate Code

Both define the same routes with different data structures. Changes to navigation must be synchronized manually, risking inconsistency.

---

### H12. Business Logic in Page Components
**Files:** `alerts/page.tsx` (458 lines), `simulation/page.tsx` (~254 lines), `CorrelationRuleEditor.tsx` (483 lines)
**Category:** Tight Coupling / Missing Abstraction

Bulk alert operations, role-based permission checks, keyboard navigation integration, search param parsing, filter synchronization, and cross-query invalidation orchestration all live inside page components instead of custom hooks.

---

## Medium Issues

### M1. Empty `backend/app/security/` Directory
**File:** `backend/app/security/` (empty directory)
**Category:** Broken Structure

Both `backend/app/security.py` (a file) and `backend/app/security/` (empty directory) exist. This is confusing and should be cleaned up.

---

### M2. Inline Pydantic Models in Routers
**Files:** `audit.py:23-48`, `hosts.py:29-35,124-143`, `maintenance.py:20-35`, `notifications.py:33-103`, `backups.py:17-41`, `timeline.py:20-42`, `threat_scores.py:15-20`
**Category:** Inconsistent Patterns

Some routers define Pydantic response models inline while others use `schemas/`. This inconsistency makes the API contract harder to discover and maintain.

---

### M3. `main.py` is Overloaded (294 Lines)
**File:** `backend/app/main.py`
**Category:** Too Many Responsibilities

Defines: job scheduler functions (8 functions), health endpoints, overview endpoint, WebSocket handler, static file serving — all outside of routers. The scheduler job functions (lines 67-119) should be in a dedicated `scheduler.py` module.

---

### M4. Config Class Has 125+ Fields in Single Class
**File:** `backend/app/config.py`
**Category:** Missing Abstraction

All configuration (database, JWT, OIDC, AI, UEBA, backup, circuit breaker, etc.) lives in one flat `Settings` class. Grouping into sub-models (`DatabaseSettings`, `JWTSettings`, `OIDCSettings`, etc.) would improve discoverability.

---

### M5. Audit Action Strings Are Raw Strings With No Registry
**Files:** 20+ router and service files
**Category:** Code Smell / Naming Inconsistency

`await log_audit(db, "alert_status_update", ...)` uses raw strings with no central enum or constants. Typos are silent and grep-based auditing is harder.

---

### M6. No CSRF Token Protection
**Category:** Security

The backend uses cookies for auth but does not implement CSRF tokens. `SameSite=Lax` provides partial protection, but state-changing `POST` requests from same-site contexts could be exploited.

---

### M7. LIKE Wildcards Not Escaped in Search Queries
**Files:** `routers/search.py:54,66-99`, `services/query_builders.py:71-72,200,261,268`
**Category:** Security / Code Smell

User input is interpolated directly into LIKE patterns (`f"%{q}%"`) without escaping `%` and `_` characters, allowing LIKE injection.

---

### M8. Auth Cookie `Secure` Flag Conditional on Debug Mode
**File:** `backend/app/auth_cookies.py:13-16`
**Category:** Security

The `Secure` flag is only set when `debug=False` AND server URL uses HTTPS. If `DEBUG=true` is accidentally left on in production, cookies are sent over plain HTTP.

---

### M9. Frontend `ss_auth` Cookie is Not HttpOnly
**File:** `frontend/lib/auth/session.ts:13`
**Category:** Security

The middleware gate cookie is set via JavaScript and is not HttpOnly. While it only contains a marker (`1`), the pattern is fragile if the logic changes.

---

### M10. Rate Limiting Disabled in Development Mode
**File:** `backend/app/middleware/rate_limit.py:76`
**Category:** Security

All rate limiting is bypassed when `environment == "development"`. If `ENVIRONMENT` is accidentally set to `development` in production, all brute-force protections are disabled.

---

### M11. Repetitive Mutation Error Handling in Frontend (41 Instances)
**Files:** 15+ component files
**Category:** Duplicate Code

The pattern `onError: (e: Error) => toast("error", "<operation> failed", e.message)` appears 41 times. A `useMutationWithToast()` helper would eliminate this duplication.

---

### M12. Repetitive ConfirmDialog + pendingDelete Pattern
**Files:** `CorrelationRuleEditor.tsx`, `IntelPanels.tsx` (x2), `SavedSearchesPanel.tsx`, `NotificationRulesPanel.tsx`, `PlaybooksPanel.tsx`, `TeamManagementPanel.tsx`
**Category:** Duplicate Code

Same confirm-dialog state management pattern repeated in 7+ components.

---

### M13. No `pyproject.toml` for Backend
**Category:** Missing Abstraction

Backend uses `requirements.txt` only with no formal Python packaging. This limits tooling integration (ruff, mypy, pytest configuration) and makes dependency resolution less reliable.

---

### M14. Only 3 Unit Test Files vs. 35 Integration Tests
**Category:** Missing Tests

The test suite is heavily skewed toward integration/HTTP testing. Unit test coverage is minimal, making it harder to isolate bugs in business logic.

---

## Low Issues

### L1. Scripts Directory Bloat
**Files:** `scripts/` (25 active + 19 archived)
**Category:** Dead Code

44 total scripts, many as duplicate pairs (.sh + .ps1). The `scripts/archive/` directory with 19 legacy Python scripts should be removed from the repo.

---

### L2. `.vscode/` and `.cursor/` IDE Directories Committed
**Category:** Dead Code

IDE-specific configuration directories exist at the root. These should be gitignored.

---

### L3. `frontend/REDESIGN_AUDIT.md` Misplaced
**Category:** Broken Structure

Audit document placed inside `frontend/` rather than in `docs/`. Inconsistent with the rest of the documentation structure.

---

### L4. `backend/venv/` Present in Working Directory
**Category:** Dead Code

While properly gitignored, having the virtual environment in the working directory adds noise.

---

### L5. `frontend/test-results/` Directory Exists
**Category:** Dead Code

Playwright output directory exists in the working directory and should be gitignored.

---

### L6. Navigation Route Definitions Are String-Based
**Files:** `Sidebar.tsx:64-112`, `CommandPalette.tsx:68-95`
**Category:** Naming Inconsistency

Route labels and paths are hardcoded strings. A shared route config module would enforce consistency.

---

### L7. OIDC State Token Uses Same Signing Key as JWT
**File:** `backend/app/security.py:101-110`
**Category:** Security (Low Risk)

Shares the signing surface. An attacker who can forge JWT tokens can also forge OIDC state tokens.

---

### L8. `dangerouslySetInnerHTML` in ThemeScript
**File:** `frontend/components/ThemeScript.tsx:16`
**Category:** Security (Very Low Risk)

Uses `dangerouslySetInnerHTML` but the content is a static string with a nonce. Risk is negligible.

---

### L9. Mixed Shell Script Formats (.sh + .ps1)
**Category:** Maintainability

Scripts directory has both Linux and Windows scripts for the same operations. Not a bug but adds maintenance overhead.

---

### L10. `frontend/public/` Missing Logo Referenced in Logs
**Category:** Broken Structure

`frontend_run.txt` shows errors for `/logo_main.jpg` which does not exist — only `assets/logo_main.png` exists at the repo root, not in `frontend/public/`.

---

## Architecture Summary

### Strengths
1. **Clean layered architecture** — Routers → Services → Models with no circular dependencies
2. **Comprehensive middleware stack** — Rate limiting, timeouts, security headers, request tracing
3. **Dual search backend** — PostgreSQL primary + OpenSearch optional with automatic fallback
4. **Flexible infrastructure** — Memory or Redis for job queue and WS pub/sub
5. **Strong security foundation** — JWT, RBAC, MFA (TOTP), OIDC/SSO, audit trail with SHA-256 hash chaining
6. **Materialized views for analytics** — Pre-computed daily stats with configurable refresh
7. **Circuit breakers** — Protect external dependencies from cascade failures
8. **Read replica support** — Transparent read routing when configured
9. **94 test files** — Strong integration test coverage across most routers
10. **Multi-environment Docker Compose** — 7 compose files for dev, CI, prod, OpenSearch, PITR

### Weaknesses
1. **God modules** — `auth.py` (457 lines), `siem_analytics.py` (428 lines), `detection.py` (393 lines) need decomposition
2. **CRUD boilerplate** — 7+ routers repeat identical select→404 patterns
3. **Inline Pydantic models** — Some routers define schemas inline, others use `schemas/`
4. **Redundant commits** — 14+ locations call `db.commit()` despite `get_db()` handling it
5. **Frontend business logic in pages** — Alerts, simulation, and correlation editor pages contain significant logic
6. **Duplicate navigation** — Sidebar and CommandPalette define routes separately
7. **Stale documentation** — Multiple docs contradict the actual codebase state
8. **Committed secrets** — API keys and JWT secret in `.env` files
9. **Minimal frontend testing** — 7 unit tests for 96 components
10. **Flat config** — 125+ fields in a single Settings class

---

## Issue Count by Severity

| Severity | Count |
|----------|-------|
| Critical | 4 |
| High | 12 |
| Medium | 14 |
| Low | 10 |
| **Total** | **40** |
