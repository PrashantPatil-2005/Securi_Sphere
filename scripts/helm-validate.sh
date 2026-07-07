#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
helm template securi helm/securi --namespace securi >/dev/null
helm template securi helm/securi -f helm/securi/values-managed-db.yaml --namespace securi >/dev/null
helm template securi helm/securi -f helm/securi/values-ingress.yaml --namespace securi >/dev/null
echo "Helm chart templates OK (default + managed-db + ingress)"
