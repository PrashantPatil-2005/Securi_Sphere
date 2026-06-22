# Securi Deployment Guide

Complete guide to host the Securi dashboard on Linux and run a live demo.

## What you are deploying

| Component | Port (default) | Role |
|-----------|----------------|------|
| **Frontend** (Next.js dashboard) | 3000 | Web UI |
| **Backend** (FastAPI API) | 8000 | Auth, events, detection, WebSocket |
| **PostgreSQL** | 5432 (internal) | Data store |
| **Redis** | 6379 (internal) | Background jobs |
| **Agent** (on each monitored VM) | — | Sends events/metrics to API |

The dashboard has **no hardcoded dummy data**. Charts show real agent data. Empty states mean no hosts are reporting yet. The only synthetic data comes from the **Simulation** feature (admin-only), which is hidden from dashboard analytics by default.

---

## Option A — Quick deploy on Linux (Docker, recommended)

### Prerequisites

- Ubuntu 22.04+ or similar Linux server
- Docker Engine + Docker Compose plugin
- Ports **3000** and **8000** open (or 80/443 behind a reverse proxy)

### Steps

1. Clone the repo on your Linux server:

```bash
git clone https://github.com/YOUR_ORG/Securi.git
cd Securi
```

2. Run the deploy script:

```bash
chmod +x scripts/deploy-linux.sh scripts/demo-setup.sh
./scripts/deploy-linux.sh YOUR_SERVER_IP
```

This creates `.env` with random `JWT_SECRET` and `POSTGRES_PASSWORD`, builds images, and starts all services.

3. Open the dashboard:

```
http://YOUR_SERVER_IP:3000
```

4. Register the first account at `/register` — the **first user becomes admin**.

5. Add a host in **Hosts → Add host**, then install the agent on a Linux VM (see below).

### Check services

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
```

### Stop / restart

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Option B — Manual install on Linux (without full Docker stack)

Use this if you want Postgres in Docker but run backend/frontend natively.

### 1. PostgreSQL

```bash
docker compose up -d postgres redis
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env: DATABASE_URL, JWT_SECRET, SERVER_URL, FRONTEND_URL
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm ci
export NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP:8000
npm run build
npm run start
```

Dashboard: `http://YOUR_SERVER_IP:3000`

---

## HTTPS with Caddy (production)

For a public demo or production, put Caddy in front of the stack.

### 1. Point DNS

Create an A record: `securi.yourdomain.com → YOUR_SERVER_IP`

### 2. Update `.env`

```env
SERVER_URL=https://securi.yourdomain.com
FRONTEND_URL=https://securi.yourdomain.com
ENVIRONMENT=production
DEBUG=false
ALLOW_REGISTRATION=false
TRUSTED_PROXY=true
```

Rebuild frontend so `NEXT_PUBLIC_API_URL` picks up `SERVER_URL`:

```bash
docker compose up -d --build frontend backend
```

### 3. Add Caddy to compose

Create `docker-compose.caddy.yml`:

```yaml
services:
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    environment:
      SECURI_DOMAIN: securi.yourdomain.com
    depends_on:
      - frontend
      - backend

volumes:
  caddy_data:
```

Start with:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.caddy.yml up -d
```

Edit `deploy/Caddyfile` and set your domain. Caddy obtains TLS certificates automatically.

---

## Install agents on Linux VMs

**Full guide:** [AGENT_INSTALL.md](AGENT_INSTALL.md) — add host, enroll, install, troubleshoot, how it works.

Each monitored machine needs the Securi agent.

1. In the dashboard: **Hosts → Add host → Enroll** → copy install command
2. On the Ubuntu VM:

```bash
curl -fsSL http://YOUR_SERVER:8000/install.sh | sudo bash -s -- \
  --token ENROLLMENT_TOKEN \
  --server http://YOUR_SERVER:8000
```

3. Verify:

```bash
sudo systemctl status securi-agent
sudo journalctl -u securi-agent -f
```

Within ~30 seconds the host should show **online** in the dashboard and events/metrics will populate.

For HTTPS servers, use `https://securi.yourdomain.com` as `--server`.

---

## Dashboard features (what works today)

| Section | Pages | Status |
|---------|-------|--------|
| Overview | Dashboard, Analytics, Metrics | Live API data |
| Operations | Hosts, Events, Alerts, Offenses, Investigations | Full |
| Intelligence | MITRE, Timeline, Network, Search | Full |
| Administration | Rules, Reports, Audit, Simulation, System Health | Admin/analyst RBAC |
| Settings | Theme, notifications, system info | Theme + notifications wired |

**Not yet in UI:** correlation rules editor, maintenance windows (API exists only).

---

## Running a live demo

### Automated demo prep

After the stack is up:

```bash
./scripts/demo-setup.sh http://YOUR_SERVER_IP:8000
```

This creates:
- User: `demo@securi.local` / `Demo1234!`
- Host: `demo-server`
- Runs `brute_force` simulation (optional: `RUN_SIMULATION=false ./scripts/demo-setup.sh ...`)

### Show simulation on dashboard charts

By default, simulated events are **excluded** from dashboard analytics so production stays clean. For a demo where charts light up immediately:

```env
EXCLUDE_SIMULATED_FROM_DASHBOARD=false
```

Restart backend, run simulation, then show Dashboard → Alerts → Timeline → MITRE.

### Demo walkthrough (5 minutes)

1. **Dashboard** — KPIs, security timeline, host risk
2. **Hosts** — show enrolled agents
3. **Events** — live feed / filtered list
4. **Alerts** — detection rules firing
5. **Offenses** — grouped incidents
6. **Timeline** — attack chain reconstruction
7. **MITRE ATT&CK** — technique mapping
8. **Simulation** (admin) — run `brute_force` live if no real attacks yet

### Clean up after demo

In the dashboard: **Simulation → Purge simulated data**

Or via API:

```bash
curl -X DELETE http://YOUR_SERVER:8000/api/v1/simulation/purge \
  -b "your-session-cookie"
```

Set `EXCLUDE_SIMULATED_FROM_DASHBOARD=true` again for production.

---

## Environment variables

| Variable | Description | Demo | Production |
|----------|-------------|------|------------|
| `JWT_SECRET` | Required. Random 32+ byte secret | Generated by script | Strong random |
| `POSTGRES_PASSWORD` | Postgres password | Generated by script | Strong random |
| `SERVER_URL` | Public API URL | `http://IP:8000` | `https://domain` |
| `FRONTEND_URL` | Dashboard URL (CORS/cookies) | `http://IP:3000` | `https://domain` |
| `ALLOW_REGISTRATION` | Public signup | `true` | `false` |
| `ENABLE_SIMULATION` | Attack simulation API | `true` | `false` |
| `EXCLUDE_SIMULATED_FROM_DASHBOARD` | Hide sim data in charts | `false` during demo | `true` |
| `ENVIRONMENT` | Shown in Settings | `development` | `production` |
| `DEBUG` | Verbose errors | `true` | `false` |
| `TRUSTED_PROXY` | Behind reverse proxy | `false` | `true` |

See `.env.example` for the full list.

---

## Firewall

```bash
# UFW example
sudo ufw allow 22/tcp
sudo ufw allow 3000/tcp   # or 80/443 if using Caddy
sudo ufw allow 8000/tcp   # only if API exposed directly
sudo ufw enable
```

Do **not** expose PostgreSQL (5432) or Redis (6379) to the internet. `docker-compose.prod.yml` binds them to localhost only.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Dashboard empty | Add hosts + install agents, or run Simulation for demo |
| `401` on API | Re-login; check `FRONTEND_URL` / `SERVER_URL` match how you access the site |
| Agent can't connect | Use server LAN/public IP, not `localhost`; open port 8000 |
| CORS errors | `FRONTEND_URL` must exactly match browser URL (scheme + host + port) |
| WebSocket disconnected | Ensure proxy forwards `/api/v1/ws` with Upgrade headers |
| Simulation disabled | Set `ENABLE_SIMULATION=true` and log in as admin |
| Charts don't show simulation | Set `EXCLUDE_SIMULATED_FROM_DASHBOARD=false` and restart backend |
| Migration errors | `docker compose restart backend` (migrations run on startup) |

---

## Windows dev → Linux server

If you develop on Windows and deploy on Linux:

1. Push code to git
2. On Linux: `git pull && ./scripts/deploy-linux.sh`
3. Point agents at the Linux server IP, not your Windows machine

For local VM testing from Windows, see README — use the host LAN IP (e.g. `192.168.56.1`) in agent `--server`.
