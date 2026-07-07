# Kubernetes deployment

Run SecuriSphere on Kubernetes using Kustomize manifests in `k8s/`.

## Architecture

| Workload | Kind | Service port |
|----------|------|----------------|
| PostgreSQL | StatefulSet | 5432 (cluster) |
| Redis | Deployment | 6379 |
| Backend API | Deployment | 8000 |
| Job worker | Deployment | — |
| Frontend | Deployment | 3000 |

Ingress and TLS are covered in [KUBERNETES_INGRESS.md](KUBERNETES_INGRESS.md). For local testing use port-forward.

## Prerequisites

- Kubernetes 1.28+
- `kubectl` and cluster access
- Container images published (see `.github/workflows/release.yml` → GHCR)
- StorageClass for PVCs (Postgres + backups)

## Quick start (in-cluster Postgres)

### 1. Build and push images

```bash
# Tag release via git tag v1.0.0 — or build locally:
docker build -f backend/Dockerfile -t ghcr.io/YOUR_ORG/Securi/backend:latest .
docker build -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=https://securi.example.com \
  -t ghcr.io/YOUR_ORG/Securi/frontend:latest .
docker push ghcr.io/YOUR_ORG/Securi/backend:latest
docker push ghcr.io/YOUR_ORG/Securi/frontend:latest
```

**Important:** `NEXT_PUBLIC_API_URL` is baked at frontend **build time** (API rewrites). Rebuild when the public URL changes.

### 2. Configure secrets

```bash
cp k8s/secret.example.yaml k8s/secret.yaml
# Edit POSTGRES_PASSWORD, JWT_SECRET, DATABASE_URL
```

Never commit `k8s/secret.yaml`.

### 3. Customize

Edit `k8s/kustomization.yaml` image names and `k8s/configmap.yaml`:

- `SERVER_URL` / `FRONTEND_URL` — public HTTPS URL
- Feature flags (`ALLOW_REGISTRATION`, etc.)

### 4. Apply

```bash
kubectl apply -f k8s/secret.yaml
kubectl apply -k k8s/
```

### 5. Verify

```bash
kubectl -n securi get pods
kubectl -n securi port-forward svc/backend 8000:8000 &
curl -s http://localhost:8000/health/ready
kubectl -n securi port-forward svc/frontend 3000:3000 &
```

Validate manifests without a cluster:

```bash
chmod +x scripts/k8s-validate.sh
./scripts/k8s-validate.sh
```

## Managed PostgreSQL (RDS / Cloud SQL)

Use overlay without in-cluster Postgres:

```bash
# secret.yaml DATABASE_URL → your managed instance (include ?ssl=require)
kubectl apply -f k8s/secret.yaml
kubectl apply -k k8s/overlays/managed-db/
```

Enable automated backups and PITR on the managed instance — `docs/PITR_RUNBOOK.md`.

## Health probes

Backend uses existing endpoints:

| Probe | Path |
|-------|------|
| Liveness | `GET /health/live` |
| Startup | `GET /health/startup` |
| Readiness | `GET /health/ready` (503 when degraded) |

Frontend: `GET /healthz`. Full reference: [HEALTH_PROBES.md](HEALTH_PROBES.md).

## Scaling notes

| Component | Replicas | Notes |
|-----------|----------|-------|
| Backend | 1+ | WebSockets need sticky sessions when >1 (configure at ingress) |
| Worker | 1–N | Scale with job queue depth |
| Frontend | 1+ | Stateless |
| Postgres | 1 | Use managed HA for production |
| Redis | 1 | Use ElastiCache/Memorystore for HA |

## Backups

Backend mounts PVC `securi-backups` at `/var/backups/securi` — same as Docker Compose prod. See `docs/BACKUP_AUTOMATION.md`.

For Postgres data, use volume snapshots or managed DB backups — not the app backup PVC alone.

## Production checklist

- [ ] Images from trusted registry with pinned tags (not `:latest`)
- [ ] `secret.yaml` from vault / sealed-secrets / external-secrets
- [ ] Managed Postgres + PITR (`docs/PITR_RUNBOOK.md`)
- [ ] Encrypted PVCs / storage class (`docs/DB_ENCRYPTION_AT_REST.md`)
- [ ] Ingress + cert-manager (`docs/KUBERNETES_INGRESS.md`)
- [ ] Resource limits tuned for cluster size
- [ ] `ALLOW_REGISTRATION=false`, `ENVIRONMENT=production`

## File layout

```
k8s/
  namespace.yaml
  configmap.yaml
  secret.example.yaml      # template only
  postgres.yaml
  redis.yaml
  backend.yaml
  worker.yaml
  frontend.yaml
  kustomization.yaml
  ingress.yaml
  overlays/managed-db/     # omit in-cluster Postgres
```

## Related

- `docs/DEPLOYMENT.md` — Docker Compose reference
- `docs/PRODUCTION_SECURITY.md` — env checklist
- `docs/BACKUP_AUTOMATION.md` — scheduled pg_dump
- `docs/HELM.md` — Helm chart (`helm/securi/`)
- `docs/KUBERNETES_INGRESS.md` — Ingress + cert-manager TLS
