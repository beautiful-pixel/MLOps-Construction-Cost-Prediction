# Overlay K3s local-path (sans root)

Utilise des PVC provisionnés dynamiquement par la StorageClass `local-path` (K3s), sans PV hostPath.

## Prérequis

- K3s avec `local-path` activée (par défaut sur K3s)
- Droits RBAC sur le namespace `mlops` pour créer PVC/Deployments/Services

## Déploiement

1) Crée un secret local (ne commite pas le vrai) :

```bash
cp k8s/oracle/03-secrets.example.yaml k8s/oracle/03-secrets.yaml
# édite les CHANGE_ME
kubectl apply -f k8s/oracle/03-secrets.yaml
```

2) Applique l’overlay :

```bash
kubectl apply -k k8s/oracle/overlays/local-path
```

## Notes

- `ReadWriteOnce` n’empêche pas plusieurs pods sur le même noeud de monter le volume, mais ça reste du stockage *local-node*.
- Si ton cluster devient multi-noeud, il faudra passer sur Longhorn/NFS (RWX) pour `project-pvc`.

### Attention : contenu de `project-pvc`

Cet overlay crée un PVC `project-pvc` via `local-path` : il est **vide** au départ.
Or, dans nos manifests, Airflow/inference montent `/opt/project` depuis ce volume (DAGs/configs/data).

Donc, si tu veux un workflow simple basé sur `git pull` dans `/home/ubuntu/mlops-project`, utilise plutôt :
- [k8s/oracle/overlays/hostpath-home](../hostpath-home)
