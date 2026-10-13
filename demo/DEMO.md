# Securi Sphere — How to Give the Demo

A step-by-step guide to running the demo live (viva / project review / jury).
All alert titles, counts and MITRE ids in this document were captured from a
real `multi_stage_attack` run against the seeded `demo-server` host.

---

## 1. Before the demo (setup)

### Start the stack

```powershell
# Windows (recommended)
.\scripts\start-infra.ps1      # Postgres + Redis
.\scripts\dev-windows.ps1      # backend + frontend
.\scripts\verify-local.ps1     # sanity check
```

Or with Docker:

```powershell
docker compose up -d --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

### Enable demo mode

In `backend/.env` (and `.env` if you start the backend from the repo root):

```env
DEMO_MODE=true
EXCLUDE_SIMULATED_FROM_DASHBOARD=false
```

Restart the backend. Demo mode then seeds, on every startup:

- the admin account below (override the password with `DEMO_USER_PASSWORD`)
- a target host named **`demo-server`**
- detection rules, MITRE data and correlation rules

`EXCLUDE_SIMULATED_FROM_DASHBOARD=false` makes the simulated events show up in
the dashboard KPIs. Leave it `true` if you want the dashboards to show only
real agent data.

### Demo credentials

| Field | Value |
|-------|-------|
| Email | `demo@securi.local` |
| Password | `Demo1234!` |

---

## 2. Pre-load attack data (2 minutes, do this early)

1. Log in → **Attack Lab** (`/simulation`)
2. Target host: **demo-server** (already there), scenario: **Multi-Stage Attack**
3. Click **Run simulation** — the chain streams for ~10 seconds
4. Optional speed-run: use **Brute Force** preset if time is tight

You should end up with **17 events, 6 alerts, 1 offense, 1 timeline**.

> No `demo-server`? Add a host from **Hosts** (it stays `inactive` without an
> enrolled agent — that is fine and does not affect the run).

Automated pre-check:

```powershell
.\scripts\validate-demo-flow.ps1 -SkipE2E
```

---

## 3. The 5-minute demo script

Use the checklist during the talk:

- [ ] Run **Multi-Stage Attack** in Attack Lab — watch the raw log tail
- [ ] **Alerts** — "the SIEM named it"
- [ ] **Offense** — "it correlated the kill chain"
- [ ] **MITRE ATT&CK** — stop, take questions

### Step 1 — The evidence, live (1 min 30 s)

> "Watch it run. The events arrive one at a time and you can read the raw
> log lines as they land — every one is prefixed `[SIMULATED]`, because we
> label synthetic telemetry so it can never be confused with real data."

**Show:**
- the raw log tail scrolling (`Failed password for svc_deploy from 198.51.100.23 ...`)
- the live kill-chain banner climbing: recon → brute force → privilege escalation → impact
- the progress banner: injecting → correlating → building timelines

### Step 2 — Alerts (1 min)

> "Raw logs are noise. The rules gave them names."

**Show:** the run result — six detections:

| Severity | Alert | Rule | MITRE |
|----------|-------|------|-------|
| high | `SSH brute force in progress on demo-server from 198.51.100.23` | `failed_logins` | T1110 |
| critical | `Brute Force Attempt` | `brute_force` | T1110 |
| critical | `Compromised account on demo-server` | `ssh_success_after_failures` | T1110 |
| critical | `Privilege escalation on demo-server` | `privilege_escalation` | T1548.003 |
| critical | `Direct root login on demo-server` | `root_login` | T1078.003 |
| high | `Service Failure` | `service_failure` | — |

Also point at **"What actually fired"**: detections grouped by kill-chain
stage with "6 of 6 expected detections raised".

### Step 3 — Offense timeline (1 min)

> "Six alerts would still be six disconnected emails. The offense engine
> groups them into one story."

**Show:** Offenses → newest offense, titled
`SSH brute force in progress on demo-server from 198.51.100.23`, risk
`critical`, **16 correlated events + 6 alerts**, attack timeline, related
user `svc_deploy`, source `198.51.100.23`.

### Step 4 — MITRE + wrap-up (1 min)

> "Each stage maps to a published MITRE technique — T1110, T1548.003,
> T1078.003. That is the full kill chain."

**Show:** MITRE ATT&CK coverage heatmap → stop → take questions.

### Optional — Replay / Reset (30 s if asked)

> "Same chain again, on demand — and Reset removes only that run's
> synthetic data, leaving real detections on the same host untouched."

**Show:** Attack Lab → **History** → per-row **Replay** / **Reset**.

---

## 4. Talking points

- **Narrative:** events → alerts → offenses → timeline → incident
- **Why not a flat alert list?** offense grouping, explainable scoring,
  attack reconstruction
- **Architecture:** 3-layer pipeline (agent → FastAPI → Postgres/Redis),
  inspired by IBM QRadar
- **Production-lite:** RBAC, MFA, HMAC-signed agent telemetry,
  tamper-evident audit log
- **Honesty:** synthetic telemetry is labelled `[SIMULATED]` end to end, and
  dashboards can exclude it entirely (`EXCLUDE_SIMULATED_FROM_DASHBOARD`)

---

## 5. Troubleshooting

| Problem | Fix |
|---------|-----|
| Backend won't start | `.\scripts\verify-local.ps1`; check ports 8000/5432/6379 |
| No `demo-server` host | Set `DEMO_MODE=true` and restart the backend |
| Login fails | `DEMO_MODE=true` + restart; password is `Demo1234!` |
| No alerts appear | Re-run the preset; check `EXCLUDE_SIMULATED_FROM_DASHBOARD=false` |
| Run button disabled | No hosts — add one from **Hosts** |
| Frontend blank | `cd frontend; npm install; npm run dev` |

**Purge after demo:** Attack Lab → **History** → *Purge all simulated data*.
Purge removes only rows tagged as simulated — real events, alerts, timelines
and offenses on the same host are left alone.

---

## 6. Related docs

- `../jury_script.md` — full viva talk track
- `../docs/GUIDE_DEMO.md` — detailed demo flow
- `../docs/SOC_LAB_SCENARIO.md` — lab scenario
- `../README.md` — project overview
