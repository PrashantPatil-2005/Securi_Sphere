# Helm chart

SecuriSphere Kubernetes deployment via Helm 3.

## Install

```bash
helm upgrade --install securi ./helm/securi \
  --namespace securi \
  --create-namespace \
  --set secrets.postgresPassword='YOUR_STRONG_PASSWORD' \
  --set secrets.jwtSecret='YOUR_JWT_SECRET_MIN_32_CHARS' \
  --set image.backend.repository=ghcr.io/YOUR_ORG/Securi/backend \
  --set image.frontend.repository=ghcr.io/YOUR_ORG/Securi/frontend \
  --set config.serverUrl=https://securi.example.com \
  --set config.frontendUrl=https://securi.example.com
```

Build the frontend image with the same public URL:

```bash
docker build -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=https://securi.example.com \
  -t ghcr.io/YOUR_ORG/Securi/frontend:latest .
```

## Values file

```bash
cp helm/securi/values-managed-db.yaml my-values.yaml
# edit secrets.databaseUrl, image repos, URLs
helm upgrade --install securi ./helm/securi -n securi -f my-values.yaml
```

Never commit production secrets in values files — use `--set`, SOPS, or External Secrets.

## Managed PostgreSQL

```bash
helm upgrade --install securi ./helm/securi \
  -n securi \
  -f helm/securi/values-managed-db.yaml \
  --set secrets.databaseUrl='postgresql+asyncpg://...' \
  --set secrets.jwtSecret='...'
```

## Existing secrets

```yaml
secrets:
  create: false
  existingSecret: my-securi-secrets
```

Secret must contain keys: `POSTGRES_PASSWORD`, `JWT_SECRET`, `DATABASE_URL`.

## Upgrade / rollback

```bash
helm upgrade securi ./helm/securi -n securi -f my-values.yaml
helm history securi -n securi
helm rollback securi 1 -n securi
```

## Validate templates

```bash
./scripts/helm-validate.sh
```

## Ingress + TLS

Enable public HTTPS with cert-manager:

```bash
kubectl apply -f deploy/cert-manager/cluster-issuer.yaml
helm upgrade --install securi ./helm/securi -n securi -f helm/securi/values-ingress.yaml \
  --set ingress.host=securi.yourdomain.com
```

Full guide: [KUBERNETES_INGRESS.md](KUBERNETES_INGRESS.md)

## Graceful shutdown

```yaml
gracefulShutdown:
  terminationGracePeriodSeconds: 45
  preStopSleepSeconds: 5
```

See [GRACEFUL_SHUTDOWN.md](GRACEFUL_SHUTDOWN.md).

## Chart vs raw manifests

| Approach | Path |
|----------|------|
| Helm (parameterized) | `helm/securi/` |
| Kustomize (static) | `k8s/` |

Both deploy the same workloads. Prefer Helm for multi-environment releases.

## Related

- `docs/KUBERNETES.md` — architecture and probes
- `docs/PITR_RUNBOOK.md` — managed DB recovery
- `docs/BACKUP_AUTOMATION.md` — backup PVC on backend
- Ingress + cert-manager — `docs/KUBERNETES_INGRESS.md`
