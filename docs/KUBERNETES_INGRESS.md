# Ingress + cert-manager (Let's Encrypt TLS)

Expose SecuriSphere on a public hostname with automatic HTTPS. Routing mirrors `deploy/Caddyfile`: API paths → backend, everything else → frontend.

## Prerequisites

| Component | Install |
|-----------|---------|
| **NGINX Ingress Controller** | [ingress-nginx](https://kubernetes.github.io/ingress-nginx/deploy/) |
| **cert-manager** | `kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml` |
| **DNS** | `A` or `CNAME` record → ingress load balancer IP |

## 1. ClusterIssuer

Edit email in `deploy/cert-manager/cluster-issuer.yaml`, then:

```bash
kubectl apply -f deploy/cert-manager/cluster-issuer.yaml
kubectl get clusterissuer
```

Use `letsencrypt-staging` first to avoid rate limits while testing.

## 2. Helm (recommended)

```bash
helm upgrade --install securi ./helm/securi \
  -n securi --create-namespace \
  -f helm/securi/values-ingress.yaml \
  --set ingress.host=securi.yourdomain.com \
  --set config.serverUrl=https://securi.yourdomain.com \
  --set config.frontendUrl=https://securi.yourdomain.com \
  --set secrets.postgresPassword='...' \
  --set secrets.jwtSecret='...'
```

Rebuild frontend with matching URL:

```bash
docker build -f frontend/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=https://securi.yourdomain.com \
  -t ghcr.io/YOUR_ORG/Securi/frontend:latest .
```

### Helm values

| Key | Description |
|-----|-------------|
| `ingress.enabled` | Create Ingress resource |
| `ingress.host` | Public hostname |
| `ingress.className` | `nginx` |
| `ingress.certManager.clusterIssuer` | `letsencrypt-prod` |
| `ingress.stickySessions` | Cookie affinity for WebSockets / multi-replica backend |
| `ingress.tls.secretName` | TLS secret (auto-created by cert-manager) |

## 3. Raw Kustomize

Edit `k8s/ingress.yaml` host, then:

```bash
kubectl apply -f deploy/cert-manager/cluster-issuer.yaml
kubectl apply -k k8s/
```

`k8s/ingress.yaml` is included in the base kustomization.

## Path routing

| Path | Backend |
|------|---------|
| `/api/*` | API (8000) — includes WebSocket `/api/v1/ws` |
| `/docs`, `/openapi.json` | API |
| `/health/*` | API probes (optional external monitoring) |
| `/install.sh`, `/agent-bundle.tar.gz` | Agent bootstrap |
| `/*` | Next.js frontend (3000) |

## Verify TLS

```bash
kubectl -n securi get ingress,certificate
kubectl -n securi describe certificate securi-tls   # or release-prefixed name with Helm
curl -I https://securi.yourdomain.com/health/ready
```

Certificate `READY=True` may take 1–3 minutes after DNS propagates.

## WebSockets

Live event feed uses `/api/v1/ws`. Ingress annotations set long proxy timeouts and optional sticky sessions when `ingress.stickySessions=true`.

If connections drop behind ingress, increase `proxy-read-timeout` or scale backend to 1 replica with sticky sessions enabled.

## Staging checklist

1. Apply `letsencrypt-staging` issuer
2. Set `ingress.certManager.clusterIssuer=letsencrypt-staging`
3. Confirm browser shows staging certificate
4. Switch to `letsencrypt-prod`

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Certificate pending | DNS points to ingress LB; port 80 reachable for HTTP-01 |
| 502 on `/api` | `kubectl -n securi get pods`; backend readiness |
| Frontend loads, API 404 | `NEXT_PUBLIC_API_URL` mismatch — rebuild frontend image |
| WebSocket disconnects | Sticky sessions; timeout annotations |

## Related

- `deploy/Caddyfile` — Docker Compose equivalent
- `docs/HELM.md` — full chart install
- `docs/KUBERNETES.md` — cluster architecture
- `docs/PRODUCTION_SECURITY.md` — `TRUSTED_PROXY=true` (default in chart)
