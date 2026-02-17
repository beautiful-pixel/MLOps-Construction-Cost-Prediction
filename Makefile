PROJECT_NAME=mlops-construction-cost-prediction
PROJECT_NAME_DEV=$(PROJECT_NAME)-dev

COMPOSE_PROD = docker compose -f deployments/compose.yaml
COMPOSE_DEV  = docker compose -f deployments/compose.yaml -f deployments/compose.dev.yaml

.PHONY: help \
	start start-dev \
	stop stop-dev \
	restart restart-dev \
	clean clean-dev \
	rebuild rebuild-dev \
	logs logs-dev \
	ps ps-dev \
	build-arm \
	test

help:
	@echo "Available commands:"
	@echo "  make start        Start full stack (prod-like)"
	@echo "  make start-dev    Start stack in dev mode"
	@echo "  make stop         Stop prod stack"
	@echo "  make stop-dev     Stop dev stack"
	@echo "  make restart      Restart prod stack"
	@echo "  make restart-dev  Restart dev stack"
	@echo "  make clean        Stop and remove prod volumes"
	@echo "  make clean-dev    Stop and remove dev volumes"
	@echo "  make rebuild      Full rebuild prod stack"
	@echo "  make rebuild-dev  Full rebuild dev stack"
	@echo "  make logs         Follow prod logs"
	@echo "  make logs-dev     Follow dev logs"
	@echo "  make ps           Show prod services"
	@echo "  make ps-dev       Show dev services"
	@echo "  make build-arm    Build ARM64 images with buildx"
	@echo "  make test         Run unit tests"

start:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) up -d --build postgres
	$(COMPOSE_PROD) -p $(PROJECT_NAME) run --rm airflow-init
	$(COMPOSE_PROD) -p $(PROJECT_NAME) up -d mlflow airflow-webserver airflow-scheduler

start-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d --build postgres
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) run --rm airflow-init
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d mlflow airflow-webserver airflow-scheduler

stop:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) down

stop-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) down

restart: stop start

restart-dev: stop-dev start-dev

clean:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) down -v

clean-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) down -v

rebuild:
	$(MAKE) clean
	$(COMPOSE_PROD) -p $(PROJECT_NAME) build --no-cache
	$(MAKE) start

rebuild-dev:
	$(MAKE) clean-dev
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) build --no-cache
	$(MAKE) start-dev

logs:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) logs -f

logs-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) logs -f

ps:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) ps

ps-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) ps


build-arm:
	docker buildx build --platform linux/arm64 -t $(PROJECT_NAME)-mlflow -f deployments/mlflow/Dockerfile.mlflow .
	docker buildx build --platform linux/arm64 -t $(PROJECT_NAME)-airflow -f deployments/airflow/Dockerfile.airflow .
	docker buildx build --platform linux/arm64 -t $(PROJECT_NAME)-inference -f api/inference_api/Dockerfile .
	docker buildx build --platform linux/arm64 -t $(PROJECT_NAME)-streamlit -f deployments/streamlit/Dockerfile.streamlit .

test:
	pytest -v tests/unit/


