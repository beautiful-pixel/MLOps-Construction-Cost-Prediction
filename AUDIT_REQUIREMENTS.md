AUDIT DES DEPENDENCIES ET REQUIREMENTS
======================================

Date: 20 Février 2026

1. ANALYSE DE requirements-base.txt
=====================================

Fichier: requirements-base.txt
Contenu:
- dvc>=3.66.1                 (Data versioning)
- joblib>=1.5.3               (Parallelization)
- mlflow>=3.9.0               (Model tracking)
- numpy>=1.26.0               (Numerical)
- pandas>=2.3.3               (Data manipulation)
- python-dotenv>=1.0.0        (Environment config)
- pytest>=9.0.2               (Testing - PROBLEME)
- pyyaml>=6.0.1               (Config files)
- rasterio>=1.4.4             (GIS data)
- scikit-learn>=1.3.0         (ML)

Problemes identifies:
- pytest dans les dependencies de prod
- Destiné pour src/ (pyproject.toml)
- Mais chaque container a ses propres requirements.txt
- requirements-base.txt n'est PAS utilisé par les containers

Verdict: requirements-base.txt est la liste d'ordre pour src/, 
mais les containers utilisent leurs propres requirements.txt


2. ANALYSE PAR MICROSERVICE
============================

SERVICE 1: API Gateway
======================
Location: api/gateway_api/

Dockerfile: Dockerfile (copie requirements.txt uniquement)
Current requirements.txt:
  fastapi>=0.115.0
  uvicorn>=0.34.0
  requests>=2.31.0
  mlflow>=3.9.0
  pydantic>=2.0
  pyyaml>=6.0.1
  python-jose[cryptography]
  passlib[bcrypt]==1.7.4
  bcrypt==4.0.1
  python-multipart

Dependencies from pyproject.toml (via "pip install -e ."):
  dvc, joblib, mlflow, numpy, pandas, python-dotenv, pytest, pyyaml, rasterio, scikit-learn

Analyse:
  DOUBLONS:
  - mlflow (dans requirements.txt ET pyproject.toml)
  - pyyaml (dans requirements.txt ET pyproject.toml)
  
  NON NECESSAIRES:
  - dvc (pas utilisé par gateway-api)
  - rasterio (pas utilisé par gateway-api)
  - scikit-learn (pas utilisé par gateway-api)
  - joblib (pas utilisé directement)
  - numpy (pas utilisé directement)
  - pytest (pas utilisé en production)
  - python-dotenv (utilisé? A vérifier)
  
  OPTIMISATIONS:
  - Retirer les doublons de requirements.txt
  - Les dépendances core (dvc, rasterio) devraient être dans src/ seulement
  - pytest ne devrait pas être dans pyproject.toml dependencies
  
Test Type: INTEGRATION (APIs HTTP)
  - Tests des endpoints
  - Tests d'authentification
  - Tests des erreurs
  - Pas besoin de unit tests pour les endpoints FastAPI
  - Unit tests seulement pour business logic (services)

Recommendation: REFACTOR
  - Creer requirements-dev.txt pour gateway_api
  - Nettoyer pyproject.toml


SERVICE 2: Inference API
========================
Location: api/inference_api/

Dockerfile: Dockerfile (copie requirements.txt + installe src/)
Current requirements.txt:
  fastapi>=0.115.0
  uvicorn>=0.34.0
  joblib>=1.5.0
  mlflow>=3.9.0
  prometheus_client>=0.20.0
  pandas>=2.0.0
  scikit-learn>=1.3.0

Dependencies from pyproject.toml:
  dvc, joblib, mlflow, numpy, pandas, python-dotenv, pytest, pyyaml, rasterio, scikit-learn

Analyse:
  DOUBLONS:
  - joblib (dans requirements.txt ET pyproject.toml)
  - mlflow (dans requirements.txt ET pyproject.toml)
  - pandas (dans requirements.txt ET pyproject.toml)
  - scikit-learn (dans requirements.txt ET pyproject.toml)
  
  NON NECESSAIRES:
  - dvc (pas utilisé par inference_api)
  - rasterio (pas utilisé)
  - pytest (pas utilisé en production)
  - python-dotenv (pas utilisé)
  - pyyaml (pas utilisé directement)
  - numpy (utilisé par pandas/sklearn en interne, pas besoin)
  
  BON:
  - prometheus_client (utilisé pour metrics)
  
Test Type: INTEGRATION + UNIT
  - Integration: tester les endpoints /predict, /health, /schema
  - Unit: tester load_production_model(), prediction logic
  - Besoin de mocks pour MLflow

Recommendation: REFACTOR
  - Retirer les doublons de requirements.txt
  - Retirer requirements.txt et utiliser seulement pyproject.toml
  - Ou bien creer requirements-dev.txt


SERVICE 3: Streamlit (ML Platform)
===================================
Location: apps/ml_platform/

Dockerfile: Dockerfile.streamlit (copie requirements.txt uniquement)
Current requirements.txt:
  streamlit>=1.32.0
  requests>=2.31.0
  pandas>=2.1.0
  plotly==6.5.2

Dependencies from pyproject.toml:
  dvc, joblib, mlflow, numpy, pandas, python-dotenv, pytest, pyyaml, rasterio, scikit-learn

Analyse:
  DOUBLONS:
  - pandas (dans requirements.txt AND pyproject.toml, mais versions diff)
  
  NON NECESSAIRES DANS STREAMLIT:
  - dvc
  - joblib
  - mlflow (devrait être implicite via requests)
  - numpy
  - rasterio
  - scikit-learn
  - pytest
  - python-dotenv (peut être besoin? Vérifier)
  
  MANQUANT dans requirements.txt:
  - plotly>=6.5.2 (present, bon)
  - requests (utilisé pour appeler gateway-api)
  - python-dotenv (if needed)
  
  PROBLEME:
  - Streamlit ne devrait pas installer tout src/
  - C'est une UI frontend, pas un ML service
  - Actuellement copie seulement requirements.txt mais installe full src/
  
Test Type: INTEGRATION UNIQUEMENT
  - Tests Streamlit nécessitent un client spécial
  - Focus sur tests que les boutons/pages fonctionnent
  - Besoin de mock de gateway-api

Recommendation: A REVOIR
  - Ne pas installer full src/ pour Streamlit
  - Creer un package minimal pour Streamlit
  - OU enlever pyproject.toml de Dockerfile.streamlit


SERVICE 4: Airflow
==================
Location: deployments/airflow/

Dockerfile: Dockerfile.airflow (custom Apache Airflow)
Current requirements.txt:
  apache-airflow-providers-docker
  apache-airflow-providers-postgres

Dependencies from pyproject.toml:
  dvc, joblib, mlflow, numpy, pandas, python-dotenv, pytest, pyyaml, rasterio, scikit-learn

Analyse:
  BON:
  - Seulement les providers Airflow nécessaires
  - Léger et spécifique
  
  PROBLEME:
  - Installe full src/ via "pip install -e ."
  - Airflow importe les DAGs depuis /opt/project/dags
  - Mais n'a pas besoin de toutes les dépendances src/
  
  SUGGESTION:
  - Creer requirements-airflow.txt qui contient UNIQUEMENT:
    * apache-airflow-providers-docker
    * apache-airflow-providers-postgres
    * Mais AUSSI les deps nécessaires pour DAGs (dvc, dbt, etc.)
  
Test Type: INTEGRATION + UNIT
  - Integration: DAGs se déclenchent, configs chargées
  - Unit: Logique des tâches Airflow testées
  - Besoin de mock de services externes

Recommendation: NETTOYER
  - Creer requirements-airflow.txt spécifique
  - Garder seulement deps nécessaires
  - Ne pas charger src/ inutilementSERVICE 5: MLflow
===================
Location: deployments/mlflow/

Dockerfile: Dockerfile.mlflow (simple, pas de requirements.txt)
Contenu Dockerfile:
  RUN pip install --no-cache-dir mlflow psycopg2-binary

Analyse:
  BON:
  - Très léger
  - Seulement ce qui est nécessaire (mlflow + postgres driver)
  - N'installe pas src/
  
  SUGGESTION:
  - Creer deployments/mlflow/requirements.txt pour plus de clarté
  - Maintenir cohérence avec autres services

Test Type: INTEGRATION UNIQUEMENT
  - MLflow est un service externe
  - Tests vérifient la connexion et l'API
  - Pas de unit tests utiles

Recommendation: OK
  - Creer requirements.txt pour cohérence
  - Rien d'urgent


3. SYNTHESE PAR SERVICE
=======================

┌─────────────────────┬───────────┬────────┬──────────┬────────────────┐
│ Service             │ État      │ Nettoy?│ Dev Req? │ Test Type      │
├─────────────────────┼───────────┼────────┼──────────┼────────────────┤
│ Gateway API         │ A REVOIR  │ OUI    │ OUI      │ INTEGRATION    │
│ Inference API       │ A REVOIR  │ OUI    │ OUI      │ INTEGRATION+   │
│ Streamlit           │ PROBLEME  │ OUI    │ OUI      │ INTEGRATION    │
│ Airflow             │ A REVOIR  │ OUI    │ OUI      │ INTEGRATION+   │
│ MLflow              │ BON       │ NON    │ NON      │ INTEGRATION    │
│ Nginx               │ BON       │ NON    │ NON      │ -              │
│ Prometheus/Grafana  │ BON       │ NON    │ NON      │ -              │
└─────────────────────┴───────────┴────────┴──────────┴────────────────┘


4. PROBLEMES IDENTIFIES
========================

PROBLEME 1: pyproject.toml contient pytest
  - pytest ne devrait pas être dans les dependencies de production
  - Uniquement en dev
  - Impact: tous les containers l'installent inutilement
  
PROBLEME 2: Duplication de dépendances
  - Gateway API: mlflow + pyyaml en double
  - Inference API: 4 dépendances en double
  - Streamlit: pandas double avec version différente
  
PROBLEME 3: Dépendances non utilisées
  - Gateway API installe rasterio, dvc, scikit-learn - ne les utilise pas
  - Inference API installe dvc, rasterio - ne les utilise pas
  - Streamlit installe rasterio, dvc, scikit-learn - ne les utilise pas
  - Chacun installe full src/ sans besoin
  
PROBLEME 4: requirements-base.txt inutilisé
  - Listé dans le repo
  - N'est pas utilisé par aucun container
  - Cause confusion
  
PROBLEME 5: Pas de requirements-dev.txt
  - Les tests ont besoin de pytest, pytest-cov, httpx, etc.
  - Pas de fichier pour spécifier cela
  
PROBLEME 6: Streamlit charge src/ entier
  - UI frontend ne devrait pas installer ML dependencies
  - Cause des installations inutiles et long build


5. RECOMMENDATIONS PRIORITAIRES
=================================

PRIORITY 1: Nettoyer pyproject.toml
  Action:
  - Retirer pytest de [project] dependencies
  - Créer section [project.optional-dependencies] pour dev

PRIORITY 2: Créer requirements-dev.txt
  Action:
  - Créer tests/requirements.txt pour tests API
  - Créer requirements-dev.txt pour développement local
  
PRIORITY 3: Retirer doublons de requirements.txt
  Action:
  - Gateway API: retirer mlflow, pyyaml
  - Inference API: retirer joblib, mlflow, pandas, scikit-learn
  - Streamlit: aligner pandas version

PRIORITY 4: Nettoyer dépendances inutiles
  Action:
  - Gateway API: installer SEULEMENT src/utils (pas full src/)
  - Inference API: installer SEULEMENT src/inference, src/features, src/models
  - Streamlit: ne pas installer src/ du tout, OU créer mini-package
  - Airflow: ne pas installer src/, charger DAGs autrement

PRIORITY 5: Créer requirements.txt pour MLflow
  Action:
  - deployments/mlflow/requirements.txt
  - Contenu: mlflow, psycopg2-binary

PRIORITY 6: Documenter les dépendances
  Action:
  - Créer DEPENDENCIES.md expliquant chaque dépendance
  - Pourquoi elle est nécessaire
  - Quelle version minimum


6. STRUCTURE PROPOSEE
======================

Nouvelle structure:

requirements-base.txt
  -> Suppression de pytest
  -> Seulement dépendances CORE du projet

requirements-dev.txt (nouveau)
  -> pytest, pytest-cov, black, flake8, mypy, etc.
  -> Pour développement local

pyproject.toml (modifié)
  [project.optional-dependencies]
  dev = ["pytest>=9.0.2", "pytest-cov>=4.0.0", ...]

api/gateway_api/requirements.txt
  -> Retirer mlflow, pyyaml
  -> Ajouter version pinning pour versions critiques

api/inference_api/requirements.txt
  -> Retirer les doublons
  -> Ajouter version pinning

apps/ml_platform/requirements.txt
  -> Aligner versions avec requirements-base.txt

deployments/airflow/requirements.txt
  -> Garder comme est (bon)

deployments/mlflow/requirements.txt (nouveau)
  mlflow>=3.9.0
  psycopg2-binary>=2.9.0

tests/requirements.txt
  -> Pytest et outils de test

Dockerfiles (modifiés):
  - Gateway API: installer SEULEMENT nécessaire
  - Inference API: optimiser
  - Streamlit: ne pas installer src/
  - Airflow: optimiser


7. TESTS A METTRE EN PLACE
============================

GATEWAY API:
  - INTEGRATION: endpoints, auth, permissions
  - UNIT: services/security.py, services/config_service.py
  - Coverage: 80%+
  
INFERENCE API:
  - INTEGRATION: /predict, /health, /schema endpoints
  - UNIT: models/loader.py, inference/schema_builder.py
  - Coverage: 75%+
  
STREAMLIT:
  - INTEGRATION: page navigation, API calls
  - NO UNIT TESTS (UI)
  - Coverage: 50%+
  
AIRFLOW:
  - INTEGRATION: DAG validation, task execution
  - UNIT: DAG operators, logic
  - Coverage: 70%+

MLflow:
  - INTEGRATION ONLY (external service)
  - Test: API connectivity, artifact storage


8. ACTIONS IMMEDIATES
=====================

Action 1: Créer requirements-dev.txt
  Faire: Créer requirements-dev.txt root level
  
Action 2: Nettoyer pyproject.toml
  Faire: Retirer pytest, créer optional-dependencies
  
Action 3: Créer requirements.txt pour MLflow
  Faire: deployments/mlflow/requirements.txt
  
Action 4: Documenter dependencies
  Faire: Créer DEPENDENCIES.md

Action 5: Tests pour Gateway API (DONE)
  Statut: Complété (tests/unit/, tests/integration/)

Action 6: Générer tests pour Inference API
  Faire: tests/inference_api/ (integration + unit)
  
Action 7: Générer tests pour Airflow
  Faire: tests/airflow/ (integration + unit)


9. IMPACT DE CES CHANGEMENTS
=============================

Build Size:
  - Réduction esperée: 20-30%
  - Moins de dépendances inutiles installées

Security:
  - Moins de packages = moins de vulnérabilités
  - Plus facile à maintenir

Performance:
  - Installation plus rapide
  - Taille des images Docker réduite

Maintenabilité:
  - Plus clair ce qui dépend de quoi
  - Problèmes de dépendances plus faciles à diagnostiquer
