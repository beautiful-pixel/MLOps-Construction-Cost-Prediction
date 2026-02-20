# Tests de l'API Gateway

## Structure des Tests

tests/
├── conftest.py                          Configuration pytest et fixtures partagées
├── requirements.txt                     Dépendances de test
├── unit/
│   └── test_security.py                Tests unitaires de sécurité
├── integration/
│   ├── test_auth_endpoints.py           Tests intégration authentification
│   ├── test_protected_endpoints.py      Tests endpoints protégés
│   └── test_all_endpoints.py            Tests de tous les endpoints

## Types de Tests

### Tests Unitaires (Unit Tests)
Tests des fonctions isolées sans dépendances externes.

Fichier: tests/unit/test_security.py

Contient:
- Hachage/vérification de mots de passe
- Génération/validation de tokens JWT
- Validation de credentials
- Configuration de sécurité

Exécution:
```bash
pytest tests/unit/ -v
```

### Tests d'Intégration (Integration Tests)
Tests des endpoints HTTP complets avec requêtes réelles.

Fichiers:
- tests/integration/test_auth_endpoints.py
  Teste l'authentification login, tokens, credentials invalides

- tests/integration/test_protected_endpoints.py
  Teste l'accès aux endpoints sécurisés, roles, permissions

- tests/integration/test_all_endpoints.py
  Teste tous les endpoints de l'API avec authentification

Exécution:
```bash
pytest tests/integration/ -v
```

## Installation

```bash
cd tests
pip install -r requirements.txt
cd ..
```

## Exécution des Tests

### Tous les tests
```bash
pytest tests/ -v
```

### Tests avec couverture de code
```bash
pytest tests/ --cov=api/gateway_api --cov-report=html
```

### Tests unitaires uniquement
```bash
pytest tests/unit/ -v
```

### Tests d'intégration uniquement
```bash
pytest tests/integration/ -v
```

### Tests d'un fichier spécifique
```bash
pytest tests/unit/test_security.py -v
```

### Tests d'une classe spécifique
```bash
pytest tests/unit/test_security.py::TestPasswordHashing -v
```

### Tests d'une fonction spécifique
```bash
pytest tests/unit/test_security.py::TestPasswordHashing::test_verify_password_with_correct_password -v
```

### Tests en mode verbose avec output détaillé
```bash
pytest tests/ -vv -s
```

### Tests avec arrêt à la première erreur
```bash
pytest tests/ -x
```

### Tests avec arrêt après N erreurs
```bash
pytest tests/ --maxfail=3
```

## Couverture de Code

Pour générer un rapport de couverture:

```bash
pytest tests/ --cov=api/gateway_api --cov-report=html
```

Puis ouvrir: htmlcov/index.html

Objectif: >80% de couverture pour les composants critiques de sécurité

## Fixtures Pytest

Fichier: tests/conftest.py

Fixtures disponibles:

- test_secret_key: Clé JWT de test
- test_algorithm: Algorithme JWT de test
- test_user_credentials: Credentials utilisateur de test
- test_admin_credentials: Credentials admin de test
- valid_jwt_token: Token JWT valide
- expired_jwt_token: Token JWT expiré
- hashed_password: Mot de passe hashé
- hashed_admin_password: Mot de passe admin hashé

Utilisation dans un test:
```python
def test_my_test(valid_jwt_token, test_user_credentials):
    assert valid_jwt_token is not None
    assert test_user_credentials["username"] == "testuser"
```

## Cas de Test Couverts

### Authentification (test_auth_endpoints.py)
- Login avec credentials valides
- Login avec credentials invalides
- Login avec username/password vides
- Login avec fields manquants
- Format du token (JWT avec 3 parties)
- Claims du token (sub, role, exp)
- Roles corrects (admin, user)
- Cas sensibilité (username, password)

### Endpoints Protégés (test_protected_endpoints.py)
- Accès sans token -> 401
- Accès avec token invalide -> 401
- Accès avec token malformé -> 401
- Accès avec token valide -> 200
- Endpoints admin uniquement -> 403 pour user
- Format des réponses JSON
- Headers de sécurité
- Messages d'erreur (pas d'infos sensibles)
- Input validation (XSS, long inputs)
- Concurrence (tokens simultanés)

### Tous les Endpoints (test_all_endpoints.py)
- /auth/login
- /info
- /status
- /predict
- /configs/*
- /training/run
- /pipeline/*
- /models
- /experiments
- /data-contracts
- /features

Chacun testé pour:
- Authentification requise
- Permissions (user vs admin)
- Format de réponse
- Codes d'erreur

### Sécurité (test_security.py)
- Hash de mots de passe (bcrypt)
- Vérification de mots de passe
- Génération de tokens JWT
- Décodage de tokens
- Tokens expirés
- Validation de secret_key
- Algorithme sécurisé

## Mocking et Fixtures

Pour les endpoints qui dépendent de services externes (Airflow, MLflow):

```python
from unittest.mock import patch

def test_training_endpoint():
    with patch('services.airflow_client.airflow_service.trigger_dag') as mock_trigger:
        mock_trigger.return_value = {"dag_run_id": "test_123"}
        
        response = client.post("/training/run", json={...})
        assert response.status_code == 200
```

## Bonnes Pratiques

1. Tests indépendants
   Chaque test doit être exécutable isolément, sans dépendre d'autres tests

2. Noms descriptifs
   test_login_with_invalid_username est mieux que test_login_fail

3. Arrangement-Action-Assertion (AAA)
   Arranger les données -> Agir -> Assertions

4. Un concept par test
   Un test = un comportement testé

5. Tests rapides
   Les tests doivent s'exécuter en < 1 seconde généralement

## Intégration Continue

Pour ajouter au CI/CD (Github Actions, etc):

```yaml
- name: Run tests
  run: |
    pip install -r tests/requirements.txt
    pytest tests/ --cov=api/gateway_api --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Dépannage

### Tests échouent avec "module not found"
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/api/gateway_api"
pytest tests/
```

### Tests lents
```bash
pytest tests/ --durations=10
```

### Cache problématique
```bash
pytest --cache-clear tests/
```

### Réinitialiser tout
```bash
rm -rf .pytest_cache __pycache__ tests/__pycache__
pytest tests/ -v
```

## Objectives de Test

- Authentification: 100% (critique)
- Endpoints protégés: 100% (critique)
- Gestion des rôles: 100% (critique)
- Validation d'input: 80%+
- Cas d'erreur: 90%+
- Couverture globale: 70%+
