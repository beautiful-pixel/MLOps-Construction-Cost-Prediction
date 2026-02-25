#!/usr/bin/env bash
set -euo pipefail

OVERLAY="${1:-hostpath-home}"
NAMESPACE="${NAMESPACE:-mlops}"

case "$OVERLAY" in
  hostpath-home|local-path|base)
    ;;
  *)
    echo "Usage: $0 [hostpath-home|local-path|base]" >&2
    exit 2
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SECRET_FILE="$ROOT_DIR/k8s/oracle/03-secrets.yaml"

if [[ ! -f "$SECRET_FILE" ]]; then
  echo "Missing secret file: $SECRET_FILE" >&2
  echo "Create it from example (do NOT commit it):" >&2
  echo "  cp k8s/oracle/03-secrets.example.yaml k8s/oracle/03-secrets.yaml" >&2
  exit 1
fi

echo "Applying secret..."
kubectl apply -n "$NAMESPACE" -f "$SECRET_FILE" || kubectl apply -f "$SECRET_FILE"

apply_kustomize_dir() {
  local kustomize_dir="$1"

  # Fast path: works when the kubectl/kustomize load-restrictor allows it.
  if kubectl apply -k "$kustomize_dir"; then
    return 0
  fi

  echo "kubectl apply -k failed (likely load-restrictor). Falling back to build+apply..." >&2

  if kubectl kustomize "$kustomize_dir" --load-restrictor LoadRestrictionsNone >/dev/null 2>&1; then
    kubectl kustomize "$kustomize_dir" --load-restrictor LoadRestrictionsNone | kubectl apply -f -
    return 0
  fi

  if command -v kustomize >/dev/null 2>&1; then
    kustomize build --load-restrictor LoadRestrictionsNone "$kustomize_dir" | kubectl apply -f -
    return 0
  fi

  echo "ERROR: Cannot apply kustomize overlay due to load-restrictor, and neither 'kubectl kustomize --load-restrictor' nor 'kustomize' is available." >&2
  echo "Fix options:" >&2
  echo "  - Install kustomize (binary in your home dir is enough), then rerun this script" >&2
  echo "  - Or run: kubectl kustomize <dir> --load-restrictor LoadRestrictionsNone | kubectl apply -f -" >&2
  return 1
}

echo "Applying manifests (overlay=$OVERLAY)..."
if [[ "$OVERLAY" == "base" ]]; then
  apply_kustomize_dir "$ROOT_DIR/k8s/oracle"
else
  apply_kustomize_dir "$ROOT_DIR/k8s/oracle/overlays/$OVERLAY"
fi

echo "\nStatus:"
kubectl -n "$NAMESPACE" get pods
kubectl -n "$NAMESPACE" get svc

echo "\nTip: if this is the first install, ensure airflow-init Job completes:" 
echo "  kubectl -n $NAMESPACE get jobs"
echo "  kubectl -n $NAMESPACE logs job/airflow-init"
