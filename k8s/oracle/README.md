# Déploiement K3s (Oracle) – namespace `mlops`

Ces manifests sont adaptés à ton schéma :
- NodePort `30080` → `gateway-api` (exposé en `/api/*` via Nginx du serveur)
- NodePort `30300` → `grafana` (exposé en `/grafana/*` via Nginx du serveur)
- Airflow / MLflow / Postgres / Prometheus en ClusterIP
- PV/PVC hostPath (storageClass `manual`) à adapter à ton serveur.

## 1) Pré-requis

- K3s installé
- Images Docker disponibles sur le nœud (ou registry privée)
- Les dossiers hostPath existent et sont accessibles :
  - `/opt/k8s-data/postgres`
  - `/opt/k8s-data/airflow`
  - `/opt/k8s-data/mlflow-artifacts`
  - `/opt/k8s-data/prometheus`
  - `/opt/k8s-data/grafana`
  - `/home/ubuntu/mlops-project` (checkout du repo + data/configs)

Si tu n’as **pas** les droits root (ou pas les droits de créer des `PersistentVolume`), utilise l’overlay K3s `local-path` :
- [k8s/oracle/overlays/local-path](k8s/oracle/overlays/local-path)

Si tu peux créer des `PersistentVolume` mais que tu n’as pas root (donc tu préfères des dossiers sous `/home/ubuntu`), utilise :
- [k8s/oracle/overlays/hostpath-home](k8s/oracle/overlays/hostpath-home)

## 2) Secrets

Copie `03-secrets.example.yaml` en `03-secrets.yaml` et remplace les valeurs `CHANGE_ME`.

Puis applique le secret :

```bash
kubectl apply -f k8s/oracle/03-secrets.yaml
```

Pourquoi c’est important : ce projet utilise bien **Postgres** (Airflow + MLflow backend store + Gateway DB). Les identifiants Postgres et les clés/tokens sont donc gérés via ce Secret.

## 3) Appliquer les manifests

### Workflow simple (recommandé)

Sur le serveur Oracle (le nœud K3s), l’idée est :
- tu mets à jour le code via `git pull` dans un dossier (ex: `/home/ubuntu/mlops-project`),
- puis tu appliques les manifests avec `kubectl apply -k ...`.

Exemple :

```bash
cd /home/ubuntu/mlops-project
git pull

# Secret local uniquement (le fichier est ignoré par git)
cp k8s/oracle/03-secrets.example.yaml k8s/oracle/03-secrets.yaml
# édite les CHANGE_ME
kubectl apply -f k8s/oracle/03-secrets.yaml

# Applique l'overlay storage adapté
kubectl apply -k k8s/oracle/overlays/hostpath-home
```

Si tu as une erreur du type :
`file ... is not in or below ... (load-restrictor)`
c'est une restriction de `kubectl apply -k` sur certaines versions. Utilise à la place :

```bash
kubectl kustomize k8s/oracle/overlays/hostpath-home --load-restrictor LoadRestrictionsNone | kubectl apply -f -
```

Ou plus simple, via le script :

```bash
./scripts/deploy_oracle_k3s_simple.sh hostpath-home
```

Vérifications rapides :

```bash
kubectl -n mlops get pods
kubectl -n mlops get svc
```

Depuis la racine du repo :

```bash
kubectl apply -k k8s/oracle
```

Alternative sans PV hostPath (PVC dynamiques K3s) :

```bash
kubectl apply -k k8s/oracle/overlays/local-path
```

Si `kubectl apply -k` échoue (load-restrictor), utilise :

```bash
kubectl kustomize k8s/oracle/overlays/local-path --load-restrictor LoadRestrictionsNone | kubectl apply -f -
```

Alternative PV hostPath dans `/home/ubuntu` (si tu peux créer des PV mais pas écrire dans `/opt`) :

```bash
kubectl apply -k k8s/oracle/overlays/hostpath-home
```

Notes:
- Le `Job` `airflow-init` doit être exécuté une fois (migrations + user admin).
- Le `Postgres` initialise aussi la DB `mlflow` + `gateway_api` via le script init.

### Note importante sur l'overlay `local-path`

Avec `local-path`, le PVC `project-pvc` est un volume **vide** provisionné par K3s : il ne contient pas ton repo.
Si tu veux que les pods lisent tes DAGs/configs/data depuis un dossier git du serveur, préfère l'overlay `hostpath-home`.

## 4) Reverse proxy Nginx (serveur Oracle)

### API
Le gateway tourne sur le NodePort `30080`. Pour que l’API externe soit sous `/api/*` tout en gardant l’app interne (routes sans préfixe), il faut **stripper** `/api/` côté Nginx :

```nginx
location /api/ {
  proxy_pass http://127.0.0.1:30080/;  # trailing slash = strip /api/
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Grafana
Grafana est configuré pour servir depuis le subpath `/grafana/` (GF_SERVER_SERVE_FROM_SUB_PATH=true).
Dans ce cas, **ne strippe pas** le préfixe :

```nginx
location /grafana/ {
  proxy_pass http://127.0.0.1:30300;   # pas de trailing slash = conserve /grafana/
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Streamlit
Tu as 2 options :
- Streamlit **standalone** sur le serveur : `/` → `localhost:8501` (comme ton schéma)
- Streamlit **dans K3s** (optionnel) via `90-streamlit.yaml` puis `/` → `localhost:30501`

## 5) Points d’attention (adaptations vs anciens manifests)

- `gateway-api` écoute en interne sur `8100` (Service `8080` → target `8100`, NodePort `30080`).
- MLflow utilise Postgres (`postgres/mlflow`) + artifacts dans `/mlflow_artifacts` (PVC dédié) — pas SQLite.
- Les pipelines (Airflow + inference/gateway) lisent les configs via `CONFIG_ROOT` et les données via `DATA_ROOT`.
  On monte donc `project-pvc` sur `/opt/project`.
