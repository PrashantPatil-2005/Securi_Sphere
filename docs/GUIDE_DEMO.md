# Securi 5-Minute Demo Script

Use this flow for guide presentations and viva demos.

## Prerequisites

- Backend running on `http://localhost:8000` (or your `SERVER_URL` / LAN IP)
- Frontend on `http://localhost:3000` (or `FRONTEND_URL`)
- **Windows quick start:** `.\scripts\start-infra.ps1` then `.\scripts\dev-windows.ps1` — verify with `.\scripts\verify-local.ps1`
- **Same-machine scripts:** if `SERVER_URL` is a LAN IP but the API is only bound locally, `demo-setup.ps1` and `verify-local.ps1` auto-fallback to `http://127.0.0.1:8000`

### Option A — Simulation only (no VM, fastest)

1. Run `.\scripts\demo-setup.ps1` (Windows) or `./scripts/demo-setup.sh` (Linux)
2. Or register at `/register`, add a host from **Hosts** (stays inactive — that is fine), then use Attack Lab

**Tip:** For dashboard KPI charts to include simulated data during the demo, set `EXCLUDE_SIMULATED_FROM_DASHBOARD=false` in backend `.env` and restart. Purge simulated data from **Attack Lab** when finished.

### Option B — With live agent (optional)

- Ubuntu VM with agent enrolled (see [DEPLOYMENT.md](./DEPLOYMENT.md))

## Automated validation

With Postgres, backend, and frontend running:

```powershell
.\scripts\validate-demo-flow.ps1
```

Linux/macOS: `./scripts/validate-demo-flow.sh`

This runs `demo-setup`, checks public settings (`demo_mode`, simulation flags), typechecks the frontend, and runs Playwright smoke + golden-path tests (`E2E_FULL_STACK=1`). Install browsers first if needed: `cd frontend && npx playwright install chromium`.

Skip E2E: `.\scripts\validate-demo-flow.ps1 -SkipE2E`

## Demo credentials (demo-setup scripts)

| Field | Value |
|-------|-------|
| Email | `demo@securi.local` |
| Password | `Demo1234!` |

With `DEMO_MODE=true` in `backend/.env`, the demo user is also seeded automatically on backend startup.

## Demo flow (< 5 minutes)

### 1. Register or log in (30s)

1. Open `/register` (first user becomes admin) or sign in with demo credentials above
2. **Option B only:** **Hosts** → add host → **Enroll** → run install command on Linux VM → confirm **online**

### 2. Run attack simulation (45s)

1. Open **Attack Lab** → **Presets** tab
2. Select target host and **Multi-Stage Attack** (default) → **Run simulation**
3. Follow the **Guided investigation** bar (Triage alerts → Review offense → Case Workspace)
4. Optional: **Custom** tab for your own chain, or **History** for past runs

> **Quick preset:** **Brute Force** is faster if time is tight (fewer timeline steps).

### 3. Investigate offenses (60s)

1. **Offenses** → select grouped offense
2. Click **Promote to incident** or **Open Case Workspace** for unified view
3. **Case Workspace** (`/investigation`) shows alert + offense + host + events in one pane

### 4. Attack timeline (45s)

1. **Timeline** → select reconstructed chain
2. Point out vertical attack chain + MITRE technique chips
3. Highlight confidence percentage

### 5. Explainable risk (30s)

1. **Overview** or **Hosts** → click risky host name
2. Open **Host risk drawer** — threat score, health score, factor breakdown

### 6. MITRE coverage (30s)

1. **MITRE ATT&CK** → coverage % rings per tactic
2. Heatmap cells show event intensity; click a technique for drilldown

### 7. Wrap-up (30s)

- Cross-host correlation rule visible under **Rules → Correlation**
- Network topology force graph on **Network**
- Notifications fire on critical/high alerts and offenses (email/Telegram if configured)

## Talking points

- **Investigation narrative:** events → alerts → offenses → timeline → incident
- **Differentiators vs flat alert lists:** offense grouping, explainable scoring, attack reconstruction
- **Production-lite:** maintenance windows (**Operations → Maintenance** at `/maintenance`), saved-search alert cron, UTF-8 CI guard

## SOC lab search hints (multi-stage scenario)

After **Multi-Stage Attack**, try in **SIEM Search**:

- `event_type:network_flow`
- `source_ip:10.0.0.50`
