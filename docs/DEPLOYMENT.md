# Deployment Guide

## Phase 1: Local Development

See README.md. Copy .env.example to .env and set secrets locally.

## Phase 2: LAN Deployment

1. Set SERVER_URL and FRONTEND_URL in backend .env to your LAN IP
2. Run backend: uvicorn app.main:app --host 0.0.0.0 --port 8000
3. Allow firewall ports 8000 and 3000

## Phase 3: Internet Deployment (HTTPS)

Use Caddy or nginx as reverse proxy. Update URLs to HTTPS.

## Environment Variables

| Variable | Description |
|----------|-------------|
| DATABASE_URL | PostgreSQL connection string (set in local .env only) |
| JWT_SECRET | Secret for JWT signing (required) |
| POSTGRES_PASSWORD | Postgres password for docker-compose |
| MAIL_* | Optional email alerts (MAIL_HOST, MAIL_USER, MAIL_PASSWORD) |
| TELEGRAM_BOT_TOKEN | Optional Telegram alerts |


## Phase 4: Agent on Ubuntu VMs (VirtualBox)

### Prerequisites on each Linux VM

- Ubuntu 20.04+ with network access to the Windows host running SecuriSphere
- Use the host machine LAN IP (not `localhost`) for `--server`

Find your Windows host IP from the VM:

```bash
ip route | grep default   # gateway is often the host
# or use the IP shown in VirtualBox adapter settings (e.g. 192.168.56.1)
```

### Install steps (per VM)

1. In the dashboard, go to **Hosts** → **Add host** → **Generate enrollment token**
2. On the Ubuntu VM:

```bash
curl -s http://YOUR_HOST_IP:8000/install.sh | sudo bash -s --   --token ENROLLMENT_TOKEN   --server http://YOUR_HOST_IP:8000
```

3. Verify the agent:

```bash
sudo systemctl status securi-agent
sudo journalctl -u securi-agent -f
```

The agent sends heartbeats (with integrity hash), metrics every 30s, and auth/syslog events.

### Firewall notes

- Allow inbound TCP **8000** on the Windows host from the VM subnet
- PostgreSQL (5432) only needs to be reachable from the backend, not from VMs

### Test detection without a real attack

1. Log in as **admin**
2. Open **Simulation** → select host → run **brute_force**
3. Check **Timeline**, **Alerts**, and **MITRE** pages for results

### Troubleshooting

| Issue | Fix |
|-------|-----|
| `column hosts.agent_hash does not exist` | Run `python -m app.services.migrate` in backend |
| Agent can't reach server | Use host LAN IP; check Windows firewall |
| 401 on agent API | Re-generate enrollment token and reinstall |
| First user can't create hosts | First registered user is admin; later users are viewers |

### Demo credentials (local dev)

After running the smoke test script, you can use `demo@test.com` / `Demo1234!` (promote to admin via DB if needed).
