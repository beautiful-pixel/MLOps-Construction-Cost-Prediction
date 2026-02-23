# Guide des Tests d'Intégration

## Vue d'ensemble

Les tests d'intégration nécessitent que les services soient en cours d'exécution. Ils testent les interactions réelles entre composants via leurs API HTTP.

## Types de tests

### Unit Tests (✅ Rapides - Pas de dépendances)
```bash
make test-unit
```
- Tests locaux sans services externes
- Pas de dépendances docker
- Exécution en < 5 secondes
- Idéal pour développement rapide

### Integration Tests (🐢 Lents - Nécessite docker-compose)
```bash
make test-integration-with-compose
```
- Teste les endpoints HTTP réels
- Nécessite docker-compose
- Exécution en 1-2 minutes
- Valide le système entier

### Tous les tests
```bash
make test
```
- Lance les unit tests
- Saute les integration tests (skipés par défaut)

## Lancer les tests d'intégration

### Option 1: Avec la commande make (Recommandé)
```bash
make test-integration-with-compose
```

**Ce que fait cette commande:**
1. Démarre postgres, gateway-api, et inference-api
2. Attend 30 secondes que les services soient prêts
3. Lance les tests d'intégration
4. Arrête les services

### Option 2: Manuel (Plus de contrôle)

**Étape 1: Démarrer les services**
```bash
make start-dev gateway-api inference-api
```

Ou avec postgres:
```bash
make start-dev postgres gateway-api inference-api
```

**Étape 2: Vérifier que les services sont prêts**
```bash
make ps-dev
```

Attendre que les services montrent `Up` status.

**Étape 3: Lancer les tests**
```bash
# Tous les tests d'intégration
pytest -v tests/integration/ -m integration

# Ou un test spécifique
pytest -v tests/integration/test_gateway_endpoints.py::TestAuthenticationEndpoints::test_login_success

# Avec timeout court (utile pour debugging)
pytest -v tests/integration/ -m integration --timeout=5
```

**Étape 4: Arrêter les services**
```bash
make stop-dev
```

## Configuration de l'environnement

Les tests d'intégration utilisent `.env.test` qui est automatiquement chargé par conftest.py:

```bash
cat .env.test
```

Variables importantes pour les tests:
- `GATEWAY_PORT=8100` - Port du gateway API
- `INFERENCE_PORT=8101` - Port de l'inference API
- `CONFIG_ROOT=./configs` - Chemin des configs

## Debugging des tests d'intégration

### Afficher les détails complets
```bash
pytest -vv tests/integration/ -s --tb=long
```

### Arrêter au premier échec
```bash
pytest tests/integration/ -x
```

### Exécuter un test spécifique avec pause
```bash
pytest tests/integration/test_gateway_endpoints.py -k "test_login_success" -vv -s
```

### Voir les logs des services
```bash
# Dans un autre terminal
make logs-dev gateway-api
```

### Attendre un service
Si les tests faileut avec "Connection refused", augmentez le timeout:
```bash
# Attendre 60 secondes avant de lancer les tests
sleep 60 && pytest -v tests/integration/ -m integration
```

## Points courants de blocage

### 1. Services pas prêts
**Symptôme:** `ConnectionRefusedError`, `Connection timeout`
**Solution:** 
```bash
make ps-dev
# Vérifier que tous les services sont "Up"
sleep 30  # Attendre plus longtemps
```

### 2. Ports en conflit
**Symptôme:** `Address already in use`
**Solution:**
```bash
make stop-dev
make clean-dev  # Nettoie aussi les volumes
make start-dev
```

### 3. Erreurs de configuration
**Symptôme:** `CONFIG_ROOT not defined`
**Solution:** 
```bash
# Vérifier que .env.test existe
ls -la .env.test

# Vérifier le contenu
cat .env.test | grep CONFIG_ROOT
```

### 4. Tests en timeout
**Symptôme:** `timeout` errors
**Solution:**
```bash
# Augmenter le timeout à 30s
pytest --timeout=30 tests/integration/
```

## Architecture des tests

```
tests/
├── unit/                          # Tests sans services
│   ├── test_data_pipeline.py
│   ├── test_features_models.py
│   └── ...
├── integration/                   # Tests avec services
│   ├── test_gateway_endpoints.py  # Gateway API endpoints
│   ├── test_auth_endpoints.py     # Authentication
│   ├── test_dataset_endpoints.py  # Dataset management
│   └── ...
└── conftest.py                    # Fixtures partagées
```

## Configuration pytest

Dans `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",  # Utilisé par les tests d'intégration
]
```

## CI/CD Integration

Les tests d'intégration sont **skippés par défaut** en CI pour éviter les complications. Pour les lancer en CI:

### GitHub Actions
```yaml
- name: Start services for integration tests
  run: make start-dev
  
- name: Wait for services
  run: sleep 30
  
- name: Run integration tests
  run: pytest -v tests/integration/ -m integration
  
- name: Stop services
  run: make stop-dev
  if: always()
```

## Bonnes pratiques

✅ **À faire:**
- Utiliser `make test-unit` pour développement rapide
- Utiliser `make test-integration-with-compose` pour tester l'intégration
- Vérifier les logs avec `make logs-dev [service]` si ça bloque
- Nettoyer avec `make clean-dev` si les services sont coincés

❌ **À éviter:**
- Ne pas exécuter `pytest tests/integration/` seul (sans services)
- Ne pas oublier les timeouts sur les tests d'intégration
- Ne pas relancer les tests d'intégration rapidement sans arrêter les services

## Commandes rapides

```bash
# Développement rapide (tests unit uniquement)
make test-unit                      # Tests rapides, pas de dépendances

# Tests d'intégration complets
make test-integration-with-compose  # Auto-démarrage/arrêt des services + RUN_INTEGRATION_TESTS=true

# Lancer les tests d'intégration manuellement
RUN_INTEGRATION_TESTS=true pytest tests/integration/

# Debugging
make start-dev postgres gateway-api inference-api
make ps-dev
RUN_INTEGRATION_TESTS=true pytest -vv tests/integration/ -s
make logs-dev gateway-api
make stop-dev

# Nettoyage
make clean-dev
```
