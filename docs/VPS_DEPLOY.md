# VPS deployment handoff — run on Ubuntu 22.04+ with Docker installed.

## Quick deploy

```bash
git clone https://github.com/YOUR_ORG/Securi_Sphere.git Securi
cd Securi
chmod +x scripts/deploy-linux.sh scripts/demo-setup.sh
./scripts/deploy-linux.sh YOUR_DOMAIN_OR_IP
```

Wait ~30s, then open `http://YOUR_DOMAIN_OR_IP:3000`, register admin, add a host, install agents.

## HTTPS with Caddy

1. Point DNS A record to VPS IP.
2. Set in `.env`:

```env
SERVER_URL=https://your-domain.com
FRONTEND_URL=https://your-domain.com
```

3. Start with Caddy overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.caddy.yml up -d --build
```

4. Rebuild frontend so `NEXT_PUBLIC_API_URL` matches `SERVER_URL`.

## Post-bootstrap lockdown

After first admin account:

```env
ALLOW_REGISTRATION=false
ENABLE_SIMULATION=false
EXCLUDE_SIMULATED_FROM_DASHBOARD=true
DEBUG=false
ENVIRONMENT=production
```

Restart: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

## Backups

Automated backups are built in — see [BACKUP_AUTOMATION.md](BACKUP_AUTOMATION.md). For minute-level recovery, see [PITR_RUNBOOK.md](PITR_RUNBOOK.md).

Quick manual backup:

```bash
./scripts/backup-postgres.sh
```

Legacy one-liner:

```bash
docker exec securi-postgres pg_dump -U securi securi | gzip > securi_backup_$(date +%Y%m%d).sql.gz
```

Restore (empty DB):

```bash
gunzip -c securi_backup.sql.gz | docker exec -i securi-postgres psql -U securi -d securi
```

## Agent install (monitored hosts)

On each Ubuntu VM:

```bash
curl -fsSL http://YOUR_DOMAIN_OR_IP:8000/install.sh | sudo bash -s -- \
  --token ENROLL_TOKEN --server http://YOUR_DOMAIN_OR_IP:8000
```

See [AGENT_INSTALL.md](AGENT_INSTALL.md) for enrollment flow.

## Production toggles (optional scale)

| Variable | When to enable |
|----------|----------------|
| `REDIS_URL` + `JOB_QUEUE_BACKEND=redis` | Background jobs |
| `WS_PUBSUB_BACKEND=redis` | Multiple API instances |
| `JWT_ALGORITHM=RS256` | Asymmetric JWT — see PRODUCTION_SECURITY.md |
| `AGENT_MTLS_ENABLED=true` | Agent certificate verification |
| `EVENT_PARTITIONING_ENABLED=true` | Large event volume (schema must be reconciled first) |

## Firewall

- Allow: 22 (SSH), 80/443 (Caddy) or 3000+8000 (direct)
- Block public access to 5432, 6379

## Health checks

```bash
curl -s http://localhost:8000/api/v1/system/health
docker compose ps
docker compose logs -f backend --tail 50
```

## Windows LAN → VPS migration

1. Export Postgres backup from Windows Docker volume.
2. Deploy on VPS with `deploy-linux.sh`.
3. Restore backup or re-enroll agents with new server URL.
4. Update agent `SERVER_URL` on each host or reinstall via `install.sh`.
