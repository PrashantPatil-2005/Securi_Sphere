# Securi 5-Minute Demo Script

Use this flow for guide presentations and viva demos.

## Prerequisites

- Backend running on `http://localhost:8000`
- Frontend on `http://localhost:3000`
- Ubuntu VM with agent enrolled (see [DEPLOYMENT.md](./DEPLOYMENT.md))

## Demo flow (< 5 minutes)

### 1. Register and add host (30s)

1. Log in as analyst/admin
2. **Hosts** → add host → **Enroll** → run install command on Linux VM
3. Confirm host status turns **online**

### 2. Run attack simulation (45s)

1. Open **Simulation** wizard
2. Step 1: select target host
3. Step 2: choose **brute_force** scenario → **Run**
4. Step 3: links to Events, Offenses, Timeline

### 3. Investigate offenses (60s)

1. **Offenses** → select grouped offense
2. Show related entities (hosts, users)
3. Review embedded timeline entries
4. Click **Promote to incident**

### 4. Attack timeline (45s)

1. **Timeline** → select reconstructed chain
2. Point out vertical attack chain + MITRE technique chips
3. Highlight confidence percentage

### 5. Explainable risk (30s)

1. **Overview** or **Hosts** → click risky host name
2. Open **Host risk drawer** — threat score, health score, factor breakdown

### 6. MITRE coverage (30s)

1. **MITRE ATT&CK** → coverage % rings per tactic
2. Heatmap cells show event intensity

### 7. Wrap-up (30s)

- Cross-host correlation rule visible under **Rules → Correlation**
- Network topology force graph on **Network**
- Notifications fire on critical/high alerts and offenses (email/Telegram if configured)

## Talking points

- **Investigation narrative:** events → alerts → offenses → timeline → incident
- **Differentiators vs flat alert lists:** offense grouping, explainable scoring, attack reconstruction
- **Production-lite:** maintenance windows (**Operations → Maintenance** at `/maintenance`), saved-search alert cron, UTF-8 CI guard
