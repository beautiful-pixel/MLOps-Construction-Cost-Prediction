# Overlay hostPath dans /home/ubuntu

À utiliser si :
- tu peux créer des `PersistentVolume` (cluster-admin), **mais**
- tu ne veux/peux pas écrire dans `/opt/...` (pas root),
- et tu veux un stockage stable (Retain) à des chemins que tu contrôles.

## Préparation (sur le serveur)

Crée les dossiers (sans root) :

```bash
mkdir -p /home/ubuntu/k8s-data/{postgres,airflow,mlflow-artifacts,prometheus,grafana}
```

Assure-toi que le repo est bien à :
- `/home/ubuntu/mlops-project`

## Déploiement

```bash
kubectl apply -n mlops -f k8s/oracle/03-secrets.yaml
kubectl apply -k k8s/oracle/overlays/hostpath-home
```

Si `kubectl apply -k` échoue avec une erreur `load-restrictor` (fichiers `../../` hors du dossier), utilise :

```bash
kubectl kustomize k8s/oracle/overlays/hostpath-home --load-restrictor LoadRestrictionsNone | kubectl apply -f -
```

Ou le script :

```bash
./scripts/deploy_oracle_k3s_simple.sh hostpath-home
```

## Remarques

- Sur K3s single-node, hostPath est OK.
- Sur multi-node, préférer NFS/Longhorn.
