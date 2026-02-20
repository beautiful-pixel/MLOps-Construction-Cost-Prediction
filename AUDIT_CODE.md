# 🔍 Audit Code - MLOps Construction Cost Prediction

**Date:** 20 Février 2026  
**Status:** ⚠️ Plusieurs problèmes critiques identifiés

---

## 📋 Table of Contents
1. [Issues Critiques (SECURITY)](#issues-critiques)
2. [Issues Majeurs](#issues-majeurs)
3. [Issues Mineurs](#issues-mineurs)
4. [Points Positifs](#points-positifs)
5. [Recommandations](#recommandations)

---

## 🚨 Issues Critiques (SECURITY)

### 1. **Hardcoded Default Credentials** [CRITICAL]
**Fichiers affectés:**
- [deployments/compose.yaml](deployments/compose.yaml#L82)
- [api/gateway_api/services/security.py](api/gateway_api/services/security.py#L12)
- [api/gateway_api/core/config.py](api/gateway_api/core/config.py#L1)

**Problème:**
```yaml
# compose.yaml - Airflow init
command: -c "airflow db migrate && airflow users create --username admin --password admin ...
```

```python
# security.py - Fake users DB
fake_users_db = {
    "admin": {"hashed_password": pwd_context.hash("admin"), ...},  # ❌ Default pwd "admin"
    "user": {"hashed_password": pwd_context.hash("user"), ...}     # ❌ Default pwd "user"
}
```

```python
# config.py - JWT secret par défaut
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")  # ❌ Insecure default
```

**Impact:** Tous les comptes d'accès utilisent des mots de passe triviaux. N'importe qui avec accès à ce code peut se connecter.

**Fix:**
```python
# config.py
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY must be set in environment")

# security.py - Remove hardcoded users, charge depuis une vraie DB ou un .env sécurisé
```

---

### 2. **JWT Secret Key utilisé en DEV** [CRITICAL]
**Fichier:** [api/gateway_api/core/config.py](api/gateway_api/core/config.py#L1)

**Problème:** Si `JWT_SECRET_KEY` n'est pas défini, la clé par défaut `"dev-secret-key"` est utilisée en production!

**Impact:** Quelqu'un avec cette clé peut forger des JWT valides pour n'importe quel utilisateur.

**Fix:**
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ JWT_SECRET_KEY environment variable is required")
```

---

### 3. **Airflow Default Credentials en Production** [HIGH]
**Fichier:** [deployments/compose.yaml](deployments/compose.yaml#L82)

**Problème:**
```bash
airflow users create --username admin --password admin
```

**Impact:** L'API Airflow est accessible avec `admin:admin`

**Fix:**
```bash
airflow users create --username $AIRFLOW_ADMIN_USER --password $AIRFLOW_ADMIN_PASSWORD
```

---

### 4. **Nginx .htpasswd avec Mot de Passe Weak** [HIGH]
**Fichier:** [deployments/nginx/.htpasswd](deployments/nginx/.htpasswd)

**Contenu:**
```
admin:$apr1$o48y0yZ7$ZmEO/UILgE9YzMx/KFHQf.
```

**Problème:** 
- Mot de passe faible (hash Apache apr1)
- Stocké en plaintext dans le repo
- Impossible de savoir le pwd original

**Fix:**
```bash
# Generate strong password
openssl passwd -apr1 "strong_random_password_here"
# Stocker dans .env ou secrets manager
```

---

### 5. **Credentials Stockés en Plaintext dans compose.yaml** [HIGH]
**Fichier:** [deployments/compose.yaml](deployments/compose.yaml)

**Problème:**
```yaml
POSTGRES_USER: airflow
POSTGRES_PASSWORD: airflow  # ❌ En plaintext
```

```python
# services/airflow_client.py
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")  # ❌ Default passwords
```

**Impact:** Base de données accessible avec creds par défaut

**Fix:**
- Utiliser Docker secrets
- Ou des variables d'environnement sécurisées
- Pas de defaults pour les mots de passe

---

## ⚠️ Issues Majeurs

### 6. **Pas d'Error Handling Robuste** [MAJOR]
**Fichiers:** Presque partout dans les APIs

**Exemple problématique:**
```python
# routers/training.py
except Exception as e:
    raise HTTPException(500, str(e))  # ❌ Expose les détails d'erreur
```

**Fix:**
```python
except Exception as e:
    logger.exception("Training failed")
    raise HTTPException(
        status_code=500, 
        detail="Internal server error"  # Ne pas exposer les détails
    )
```

---

### 7. **Logging Insuffisant** [MAJOR]
**Problème:** Pas de logs structurés pour audit/debugging

```python
# Aucun logging systématique des actions critiques
# - Connexions authentifiées
# - Modifications de configuration
# - Déclenchement de DAGs
```

**Fix:**
```python
import logging
logger = logging.getLogger(__name__)

@router.post("/training/run")
def run_training(request, user=Depends(require_admin)):
    logger.info(f"Training triggered by {user['username']}", 
                extra={
                    "feature_version": request.feature_version,
                    "user": user["username"],
                    "timestamp": datetime.utcnow()
                })
```

---

### 8. **Validation d'Input Manquante** [MAJOR]
**Fichier:** [api/gateway_api/routers/configs.py](api/gateway_api/routers/configs.py#L1)

**Problème:**
```python
@router.post("/features")
def create_feature_schema(payload: FeatureSchemaRequest, user=Depends(require_admin)):
    # Pas de validation des champs du payload
    # Pas de limite de taille
    # Pas de vérification du format YAML
```

**Impact:** Injection d'erreurs, DoS, corruption de données

**Fix:**
```python
from pydantic import BaseModel, validator, constr, confloat

class FeatureSchemaRequest(BaseModel):
    name: constr(min_length=1, max_length=255, regex=r"^[a-zA-Z0-9_-]+$")
    version: int = Field(..., ge=1, le=9999)
    schema: str = Field(..., max_length=100_000)  # Limit size
    
    @validator('schema')
    def validate_yaml(cls, v):
        try:
            yaml.safe_load(v)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        return v
```

---

### 9. **CORS Non Configuré** [MAJOR]
**Fichier:** [api/gateway_api/main.py](api/gateway_api/main.py)

**Problème:** Pas de configuration CORS explicite = par défaut très restrictif

```python
# main.py - Aucune configuration CORS
app = FastAPI(...)  # ❌ Pas de middleware CORS
```

**Impact:** Les requêtes cross-origin peuvent être bloquées

**Fix:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

### 10. **Pas de Rate Limiting dans les APIs** [MAJOR]
**Problème:** Les APIs Python n'ont pas de rate limiting (sauf nginx)

```python
# Aucune limite de requêtes par utilisateur
# Aucune limite de ressources
# Vulnerable aux attaques brute-force
```

**Fix:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/auth/login")
@limiter.limit("5/minute")
def login(request: Request, ...):
    ...
```

---

### 11. **Database Credentials dans Environment** [MAJOR]
**Fichier:** [deployments/compose.yaml](deployments/compose.yaml#L53-L56)

```yaml
postgres:
  environment:
    POSTGRES_USER: airflow        # ❌ En plaintext
    POSTGRES_PASSWORD: airflow    # ❌ En plaintext
```

**Impact:** Tout le monde dans le repo voit les creds

**Fix:**
- Utiliser `.env` (ajouté à `.gitignore`)
- Ou Docker secrets
- Ou Vault/Secrets Manager

---

## 📌 Issues Mineurs

### 12. **Imports Relatifs Inconsistents** [MINOR]
```python
# Mélange d'imports relatifs et absolus
from services.security import ...  # ❌ Relatif
from core.config import ...        # ❌ Relatif
from api.gateway_api.services import ...  # ❌ Incohérent

# Should be:
from .services.security import ...  # ✅ Explicite
from .core.config import ...
```

---

### 13. **Pas de Type Hints Complets** [MINOR]
```python
# security.py
def authenticate_user(username: str, password: str):  # ✅ Good
    return user  # ❌ Type not specified

# Should be:
def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    return user
```

---

### 14. **Pas de Tests** [MINOR]
**Structure:**
```
tests/
  e2e/      # Vide
  integration/  # Vide
  unit/     # Vide
```

**Impact:** Aucune couverture de test, régression risk élevé

---

### 15. **Dépendances Impinées** [MINOR]
**Fichiers:** requirements.txt utilisent `>=` sans version maximale

```txt
fastapi>=0.115.0  # ❌ Pas de limite supérieure
uvicorn>=0.34.0   # ❌ Peut casser en version majeure
```

**Fix:**
```txt
fastapi>=0.115.0,<1.0.0
uvicorn>=0.34.0,<0.35.0
```

---

### 16. **Configuration Manquante** [MINOR]
**Problème:** Pas de fichier .env.example complet

- `JWT_SECRET_KEY` - Missing
- `AIRFLOW_USER/PASSWORD` - Missing
- `INFERENCE_INTERNAL_TOKEN` - Présent mais faible

---

### 17. **Logging pas Structuré** [MINOR]
```python
# Aucune config de logging centralisée
# Aucun format de log standard
# Logs à la console sans rotation
```

**Fix:**
```python
# logging_config.py
LOGGING_CONFIG = {
    "version": 1,
    "handlers": {
        "default": {
            "formatter": "json",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/app.log",
            "maxBytes": 10485760,
            "backupCount": 5,
        }
    }
}
```

---

## ✅ Points Positifs

1. **Architecture bien structurée** - Séparation claire : API, services, routers
2. **Use of Pydantic** - Validation des données avec Pydantic
3. **FastAPI** - Framework moderne et sécurisé
4. **Authentication JWT** - Authentification par tokens (bien que configurée de manière faible)
5. **Docker Compose** - Infrastructure as Code
6. **Monitoring** - Prometheus + Grafana + nginx exporter
7. **MLflow Integration** - Model versioning et tracking
8. **Git DVC** - Data versioning

---

## 🔧 Recommandations Prioritaires

### Priority 1: CRITICAL (Week 1)
```
[ ] Générer une vraie JWT_SECRET_KEY et la stocker en .env
[ ] Changer les mots de passe Airflow/Postgres par défaut
[ ] Retirer les credentials du repo (ajouter .env à .gitignore)
[ ] Ajouter des vérifications de variables d'environnement obligatoires
```

### Priority 2: HIGH (Week 1-2)
```
[ ] Ajouter input validation robuste avec Pydantic
[ ] Implémenter structured logging
[ ] Ajouter error handling centralisé (middleware)
[ ] Configurer CORS explicitement
[ ] Ajouter rate limiting avec slowapi
```

### Priority 3: MEDIUM (Week 2-3)
```
[ ] Ajouter des tests (au moins 60% coverage)
[ ] Migrer fake_users_db vers une vraie BD
[ ] Configurer type hints complets
[ ] Mettre en place la rotation des logs
[ ] Ajouter health checks pour tous les services
```

### Priority 4: LOW (Ongoing)
```
[ ] Fixer les imports relatifs
[ ] Pinning des dépendances
[ ] Documentation API (OpenAPI)
[ ] Metrics supplémentaires
```

---

## 📚 Resources Recommandées

- **Security:** https://owasp.org/www-project-top-ten/
- **FastAPI:** https://fastapi.tiangolo.com/deployment/concepts/
- **JWT:** https://tools.ietf.org/html/rfc7519
- **12 Factor App:** https://12factor.net/

---

## 🎯 Conclusion

Le projet a une **bonne architecture de base**, mais souffre de **problèmes de sécurité critiques** liés à:
- Credentials par défaut
- Manque de validation
- Mauvaise gestion des secrets

**Estimated remediation time:** 2-3 semaines pour corriger les issues critiques et majeurs

**Severity Score:** 7/10 ⚠️
