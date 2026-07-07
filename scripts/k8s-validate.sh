#!/usr/bin/env bash
# Validate Kubernetes manifests (client-side dry run).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/k8s"
kubectl kustomize . >/dev/null
kubectl kustomize overlays/managed-db >/dev/null
echo "k8s manifests OK (base + managed-db overlay)"
