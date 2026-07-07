# Kubernetes manifests

See [docs/KUBERNETES.md](../docs/KUBERNETES.md) for deploy instructions.

```bash
cp secret.example.yaml secret.yaml   # edit, do not commit
kubectl apply -f secret.yaml
kubectl apply -k .
```

Managed Postgres: `kubectl apply -k overlays/managed-db/`
