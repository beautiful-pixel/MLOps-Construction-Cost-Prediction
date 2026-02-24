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

echo "Applying manifests (overlay=$OVERLAY)..."
if [[ "$OVERLAY" == "base" ]]; then
  kubectl apply -k "$ROOT_DIR/k8s/oracle"
else
  kubectl apply -k "$ROOT_DIR/k8s/oracle/overlays/$OVERLAY"
fi

echo "\nStatus:"
kubectl -n "$NAMESPACE" get pods
kubectl -n "$NAMESPACE" get svc

echo "\nTip: if this is the first install, ensure airflow-init Job completes:" 
echo "  kubectl -n $NAMESPACE get jobs"
echo "  kubectl -n $NAMESPACE logs job/airflow-init"
