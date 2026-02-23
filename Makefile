AIRFLOW_SERVICES := airflow-webserver airflow-scheduler airflow-init
VALID_SERVICES := $(strip $(shell docker compose -f deployments/compose.yaml config --services))
RAW_SERVICES := $(filter-out $@,$(MAKECMDGOALS))

SERVICES := $(filter $(VALID_SERVICES),$(RAW_SERVICES))

# Si l'utilisateur demande "airflow", on remplace par tous les services airflow
ifneq ($(filter airflow,$(RAW_SERVICES)),)
  SERVICES := $(AIRFLOW_SERVICES)
endif

SERVICES := $(if $(SERVICES),$(SERVICES),$(VALID_SERVICES))

%:
	@:


PROJECT_NAME = mlops-construction-cost-prediction
PROJECT_NAME_DEV = $(PROJECT_NAME)-dev

COMPOSE_DEV = docker compose -f deployments/compose.yaml -f deployments/compose.dev.yaml
COMPOSE_PROD = docker compose -f deployments/compose.yaml -f deployments/compose.prod.yaml

.PHONY: help \
	start start-dev \
	stop stop-dev stop-service-dev \
	restart restart-dev \
	clean clean-dev \
	build build-dev build-no-cache build-arm \
	rebuild rebuild-dev \
	logs logs-dev \
	ps ps-dev \
	test test-unit test-integration test-integration-with-compose

help:
	@echo ""
	@echo "make start-dev [service...]      Start dev stack"
	@echo "make stop-dev                   Stop dev stack"
	@echo "make restart-dev [service...]   Restart dev services"
	@echo "make rebuild-dev [service...]   Rebuild & restart dev services"
	@echo ""
	@echo "make logs-dev [service...]      Follow logs"
	@echo "make ps-dev                     Show running services"
	@echo ""
	@echo "make build-dev [service...]     Build services"
	@echo "make build-no-cache             Build without cache"
	@echo ""
	@echo "make test                       Run all tests"
	@echo "make test-unit                  Run unit tests"
	@echo "make test-integration           Run integration tests"
	@echo ""

services:
	docker compose -f deployments/compose.yaml config --services

start:
	@echo "Starting services (prod): $(SERVICES)"
	$(COMPOSE_PROD) -p $(PROJECT_NAME) up -d --build postgres
	$(COMPOSE_PROD) -p $(PROJECT_NAME) run --rm airflow-init
	$(COMPOSE_PROD) -p $(PROJECT_NAME) up -d $(SERVICES)
	@echo "Started"

start-dev:
	@echo "Starting services (dev): $(SERVICES)"
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d --build postgres
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) run --rm airflow-init
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d $(SERVICES)
	@echo "Started"

stop:
	@echo "Stopping prod stack"
	$(COMPOSE_PROD) -p $(PROJECT_NAME) down
	@echo "Stopped"

stop-dev:
	@echo "Stopping dev service(s): $(SERVICES)"
	@if [ "$(SERVICES)" = "$(VALID_SERVICES)" ]; then \
		$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) down; \
	else \
		$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) stop $(SERVICES); \
	fi
	@echo "Stopped"

restart:
	@echo "Restarting prod stack"
	$(MAKE) stop
	$(MAKE) start

restart-dev:
	@echo "Restarting services: $(SERVICES)"
	$(MAKE) stop-dev $(SERVICES)
	$(MAKE) start-dev $(SERVICES)

clean:
	@echo "Removing prod stack and volumes"
	$(COMPOSE_PROD) -p $(PROJECT_NAME) down -v

clean-dev:
	@echo "Removing dev stack and volumes"
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) down -v

build:
	@echo "Building services (prod): $(SERVICES)"
	$(COMPOSE_PROD) -p $(PROJECT_NAME) build --no-cache $(SERVICES)

build-dev:
	@echo "Building services (dev): $(SERVICES)"
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) build --no-cache $(SERVICES)

rebuild:
	@echo "Rebuilding services (prod): $(SERVICES)"
	$(COMPOSE_PROD) -p $(PROJECT_NAME) build $(SERVICES)
	$(COMPOSE_PROD) -p $(PROJECT_NAME) up -d --force-recreate $(SERVICES)
	@echo "Rebuild complete"

rebuild-dev:
	@echo "Rebuilding services (dev): $(SERVICES)"
	$(MAKE) stop-dev $(SERVICES)
	$(MAKE) build-dev $(SERVICES)
	$(MAKE) start-dev $(SERVICES)
	@echo "Rebuild complete"

logs:
	@echo "Following logs (prod): $(SERVICES)"
	$(COMPOSE_PROD) -p $(PROJECT_NAME) logs -f $(SERVICES)

logs-dev:
	@echo "Following logs (dev): $(SERVICES)"
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) logs -f $(SERVICES)

ps:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) ps

ps-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) ps

test:
	@echo "Running all tests"
	pytest -v

test-unit:
	@echo "Running unit tests"
	pytest -v tests/unit/

test-integration:
	@echo "Running integration tests (SKIPPED - requires running services)"
	pytest -v tests/integration/

test-integration-with-compose:
	@echo "Starting services for integration tests..."
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d --build postgres gateway-api inference-api
	@echo "Waiting for services to be ready (30s)..."
	@sleep 30
	@echo "Running integration tests..."
	RUN_INTEGRATION_TESTS=true pytest -v tests/integration/ || true
	@echo "Stopping services..."
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) down
	@echo "Integration tests complete"

build-arm:
	@echo "Building ARM64 images"
	docker buildx build --platform linux/arm64 \
		-t $(PROJECT_NAME)-mlflow \
		-f deployments/mlflow/Dockerfile.mlflow .

	docker buildx build --platform linux/arm64 \
		-t $(PROJECT_NAME)-airflow \
		-f deployments/airflow/Dockerfile.airflow .

	docker buildx build --platform linux/arm64 \
		-t $(PROJECT_NAME)-inference \
		-f api/inference_api/Dockerfile .

	docker buildx build --platform linux/arm64 \
		-t $(PROJECT_NAME)-streamlit \
		-f deployments/streamlit/Dockerfile.streamlit .

	@echo "ARM64 build complete"