ANALYSE: UTILISATION DE pyproject.toml PAR SERVICE
===================================================

Date: 20 Février 2026


1. SERVICES UTILISANT pyproject.toml
=====================================

SERVICE 1: Gateway API
  Location: api/gateway_api/Dockerfile
  
  Dockerfile:
    COPY pyproject.toml .
    COPY README.md .
    COPY src/ src/
    RUN pip install --no-cache-dir -e .
  
  Install Order:
    1. requirements.txt (8 packages) -> fastapi, auth libs
    2. pyproject.toml (9 packages) -> src/ dependencies
  
  Total Installed: 17 packages
  
  Analyse:
    ✅ Installe les 2 -> OK pour compiler src/
    Mais charge TOUTES les dépendances src/ (dvc, rasterio, etc.)
    Certaines non nécessaires pour gateway-api
  
  Probleme:
    - Installe full src/ inutilement
    - Les dépendances ML (rasterio, scikit-learn, etc.) ne sont pas utilisées par gateway-api
    - Augmente la taille de l'image Docker inutilement

SERVICE 2: Inference API
  Location: api/inference_api/Dockerfile
  
  Dockerfile:
    COPY pyproject.toml .
    COPY README.md .
    COPY src/ src/
    RUN pip install --no-cache-dir -e .
    
    COPY api/inference_api/requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
  
  Install Order:
    1. pyproject.toml (9 packages) -> src/ dependencies
    2. requirements.txt (3 packages) -> fastapi, uvicorn, prometheus
  
  Total Installed: 12 packages (mais avec doublons, environ 10-11 uniques)
  
  Analyse:
    ✅ Installe les 2 -> OK pour compiler src/
    ✅ Installe requirements.txt APRES (peut override)
    BUT: Installe FULL src/ même si inference_api n'utilise que:
      - src/features/
      - src/models/
      - src/inference/
      - src/training/ (pas utilisé!)
      - src/registry/
  
  Probleme:
    - Installe rasterio, dvc, joblib (pas utilisé par inference-api)
    - Charge le full src/ package même si seulement 3-4 modules nécessaires

SERVICE 3: Streamlit (ML Platform)
  Location: apps/ml_platform/Dockerfile.streamlit
  
  Dockerfile:
    COPY apps/ml_platform/requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    COPY apps/ml_platform/ .
  
  Install Order:
    1. requirements.txt UNIQUEMENT (3 packages)
  
  NO pyproject.toml!
  NO "pip install -e ."!
  
  Total Installed: 3 packages
  
  Analyse:
    ✅ CORRECT! Ne charge pas src/ inutilement
    ✅ Léger et rapide
    ✅ A garder comme est
  
  Note: Streamlit n'a pas besoin de src/ pour fonctionner
        (C'est une UI qui appelle gateway-api via HTTP)

SERVICE 4: Airflow
  Location: deployments/airflow/Dockerfile.airflow
  
  Dockerfile:
    COPY --chown=airflow:airflow pyproject.toml .
    COPY --chown=airflow:airflow README.md .
    COPY --chown=airflow:airflow src/ src/
    
    RUN pip install --no-cache-dir -r requirements.txt
    RUN pip install --no-cache-dir -e .
  
  Install Order:
    1. requirements.txt (2 packages) -> airflow-providers
    2. pyproject.toml (9 packages) -> src/ dependencies
  
  Total Installed: 11 packages
  
  Analyse:
    ✅ Installe les 2 -> OK pour compiler src/
    ✅ Airflow a BESOIN de src/ (DAGs importent src/)
    ✅ Les dépendances (dvc, mlflow, etc.) sont utilisées par DAGs
  
  Verdict: OK comme est

SERVICE 5: MLflow
  Location: deployments/mlflow/Dockerfile.mlflow
  
  Dockerfile:
    RUN pip install --no-cache-dir mlflow psycopg2-binary
  
  NO pyproject.toml!
  NO "pip install -e ."!
  
  Total Installed: 2 packages (+ leurs dépendances)
  
  Analyse:
    ✅ CORRECT! Seulement ce qui est nécessaire
    ✅ Léger et rapide
    ✅ A garder comme est


2. RESUME: UTILISATION DE pyproject.toml
==========================================

┌─────────────────────┬──────────────┬──────────────────┬──────────────┐
│ Service             │ Utilise      │ Necesaire?       │ Verdict      │
├─────────────────────┼──────────────┼──────────────────┼──────────────┤
│ Gateway API         │ OUI          │ PARTIELLEMENT    │ OPTIMISER    │
│ Inference API       │ OUI          │ PARTIELLEMENT    │ OPTIMISER    │
│ Streamlit           │ NON          │ N/A              │ BON          │
│ Airflow             │ OUI          │ OUI              │ BON          │
│ MLflow              │ NON          │ N/A              │ BON          │
│ Nginx               │ NON          │ N/A              │ BON          │
└─────────────────────┴──────────────┴──────────────────┴──────────────┘


3. ADAPTATIONS NECESSAIRES POUR requirements.txt
=================================================

GATEWAY API:
  Situation actuelle:
    - requirements.txt: 8 packages (fastapi, auth libs)
    - pyproject.toml: 9 packages (FULL src/)
  
  Probleme:
    - Charge dvc, rasterio, scikit-learn (non utilisés)
    - Ajoute 200+ MB de dépendances inutiles
  
  Adaptation proposée:
    Créer api/gateway_api/requirements-prod.txt
    
    Contenu:
      fastapi>=0.115.0,<1.0
      uvicorn>=0.34.0,<1.0
      requests>=2.31.0,<3.0
      pydantic>=2.0,<3.0
      python-jose[cryptography]
      passlib[bcrypt]==1.7.4
      bcrypt==4.0.1
      python-multipart
      
      mlflow>=3.9.0,<4.0
      pyyaml>=6.0.1,<7.0
      
    Note: Ajouter mlflow + pyyaml (au lieu de full src/)
    
    Dockerfile change:
      COPY api/gateway_api/requirements-prod.txt requirements.txt
      RUN pip install --no-cache-dir -r requirements.txt
      
      # RETIRER:
      # COPY pyproject.toml
      # COPY README.md
      # COPY src/ src/
      # RUN pip install --no-cache-dir -e .
  
  Reduction:
    - De 17 packages -> 10-12 packages
    - De ~400 MB -> ~250 MB (estimation)

INFERENCE API:
  Situation actuelle:
    - requirements.txt: 3 packages (fastapi, uvicorn, prometheus)
    - pyproject.toml: 9 packages (FULL src/)
  
  Probleme:
    - Charge rasterio, dvc, joblib (non utilisés directement)
    - Order: pyproject.toml AVANT requirements.txt (npm bonnes pratiques)
  
  Adaptation proposée:
    Merger requirements.txt dans pyproject.toml
    
    Créer [project.optional-dependencies]
    
    pyproject.toml:
      dependencies = [
        "joblib>=1.5.3,<2.0",
        "mlflow>=3.9.0,<4.0",
        "pandas>=2.3.3,<3.0",
        "scikit-learn>=1.3.0,<2.0",
        "pyyaml>=6.0.1,<7.0",
        "fastapi>=0.115.0,<1.0",
        "uvicorn>=0.34.0,<1.0",
        "prometheus_client>=0.20.0,<1.0",
      ]
    
    Dockerfile:
      COPY pyproject.toml .
      COPY src/ src/
      RUN pip install --no-cache-dir -e .
      
      # RETIRER: requirements.txt
    
    Reduction:
    - De ~12 packages -> ~9 packages
    - Consolidation (une seule source)

STREAMLIT:
  Situation: BON
  Action: AUCUNE
  
  Garder:
    COPY apps/ml_platform/requirements.txt
    (sans pyproject.toml)

AIRFLOW:
  Situation: BON
  Action: AUCUNE
  
  Justification:
    - Airflow DOIT charger src/ pour les DAGs
    - Dépendances utilisées (dvc, mlflow, etc.)


4. REQUIREMENTS-DEV.txt POUR GITHUB ACTIONS
============================================

Situation actuelle:
  - tests/requirements.txt existe ✅
  - Contient pytest, pytest-asyncio, pytest-cov, httpx
  
  Contenu actuel:
    pytest>=7.0.0
    pytest-asyncio>=0.21.0
    pytest-cov>=4.0.0
    httpx>=0.24.0
    python-jose[cryptography]
    passlib[bcrypt]
    bcrypt
  
  Probleme:
    ❌ Duplica python-jose, passlib, bcrypt (deja dans gateway_api/requirements.txt)
    ❌ Manque: black, flake8, mypy, isort (linting/formatting)
    ❌ Manque: pytest-xdist (parallel testing)
    ❌ Manque: responses (HTTP mocking)

RECOMMANDATION: DEUX FILES

1. tests/requirements.txt (pour tests uniquement)
   pytest>=7.0.0,<8.0
   pytest-asyncio>=0.21.0,<1.0
   pytest-cov>=4.0.0,<5.0
   httpx>=0.24.0,<1.0
   pytest-xdist>=3.0.0
   responses>=0.23.0

2. requirements-dev.txt (pour développement local ET CI)
   -r tests/requirements.txt
   
   black>=23.0.0,<24.0
   flake8>=6.0.0,<7.0
   mypy>=1.0.0,<2.0
   isort>=5.12.0,<6.0
   pytest-watch>=4.2.0


GITHUB ACTIONS: workflow complet
=================================

.github/workflows/tests.yml:

name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10"]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install base dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-base.txt
      
      - name: Install dev dependencies
        run: |
          pip install -r requirements-dev.txt
      
      - name: Lint with black
        run: black --check api/ apps/ src/ tests/
      
      - name: Lint with flake8
        run: flake8 api/ apps/ src/ tests/ --max-line-length=100
      
      - name: Type check with mypy
        run: mypy api/ src/
      
      - name: Sort imports with isort
        run: isort --check-only api/ apps/ src/ tests/
      
      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --cov=api/gateway_api/services \
                                  --cov=src/ \
                                  --cov-report=xml
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v --cov=api/gateway_api \
                                         --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella


5. SYNTHESE ET ACTIONS
======================

ACTIONS IMMEDIATES:

1. ✅ DONE: requirements-base.txt (retirer pytest)
2. ✅ DONE: requirements-dev.txt (créer avec black, flake8, etc.)
3. ✅ DONE: tests/requirements.txt (créer)

4. TODO: Adapter Gateway API
   - Créer api/gateway_api/requirements-prod.txt
   - Modifier Dockerfile pour ne pas charger src/
   
5. TODO: Adapter Inference API
   - Merger requirements.txt dans pyproject.toml
   - Modifier Dockerfile pour une seule source
   
6. TODO: Créer .github/workflows/tests.yml
   - GitHub Actions pour CI
   
7. TODO: Mettre à jour pyproject.toml
   - Version pinning
   - Optional-dependencies pour dev

IMPACT:

Images Docker:
  Gateway API:
    Avant: ~400 MB
    Apres: ~250 MB (-37%)
    
  Inference API:
    Avant: ~350 MB
    Apres: ~300 MB (-14%)
  
  Total reduction: ~150 MB across stack

Build time:
  Réduction estimée: 30-40% (moins de pip installs)

Clarity:
  ✅ Une source de vérité par service
  ✅ Dépendances explicites
  ✅ Dev vs prod séparé


6. FICHIERS A CREER/MODIFIER
=============================

Files READY:
  ✅ requirements-base.txt (modifié - pytest retiré)
  ✅ requirements-dev.txt (créé)
  ✅ tests/requirements.txt (créé)
  ✅ deployments/mlflow/requirements.txt (créé)

Files TODO:
  🔲 api/gateway_api/requirements-prod.txt
  🔲 Modify: api/gateway_api/Dockerfile
  🔲 Modify: api/inference_api/Dockerfile
  🔲 .github/workflows/tests.yml
  🔲 Update: pyproject.toml (version pinning)

PRIORITE:
  HIGH: Gateway API + Inference API cleanup
  HIGH: GitHub Actions workflow
  MEDIUM: pyproject.toml finalization
