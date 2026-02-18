PROJECT_NAME=mlops-construction-cost-prediction
PROJECT_NAME_DEV=$(PROJECT_NAME)-dev

COMPOSE_DEV = docker compose -f deployments/compose.yaml -f deployments/compose.dev.yaml
COMPOSE_PROD = docker compose -f deployments/compose.yaml -f deployments/compose.prod.yaml

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
	$(COMPOSE_PROD) -p $(PROJECT_NAME) up -d mlflow airflow-webserver airflow-scheduler inference-api streamlit

start-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d --build postgres
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) run --rm airflow-init
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d mlflow airflow-webserver airflow-scheduler inference-api gateway-api streamlit

stop:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) down

stop-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) down

restart:
	$(MAKE) stop
	$(MAKE) start

restart-dev:
	$(MAKE) stop-dev
	$(MAKE) start-dev

clean:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) down -v

clean-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) down -v

build:
	$(COMPOSE_PROD) -p $(PROJECT_NAME) build --no-cache

build-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) build --no-cache

rebuild:
	$(MAKE) stop
	$(MAKE) build
	$(MAKE) start

rebuild-dev:
	$(MAKE) stop-dev
	$(MAKE) build-dev
	$(MAKE) start-dev

bootstrap:
	$(MAKE) clean
	$(MAKE) build
	$(MAKE) start

bootstrap-dev:
	$(MAKE) clean-dev
	$(MAKE) build-dev
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



# ----------------------------
# Service-level rebuild
# ----------------------------

rebuild-inference-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) build --no-cache inference-api
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d --force-recreate inference-api

rebuild-gateway-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) build --no-cache gateway-api
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d --force-recreate gateway-api

rebuild-streamlit-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) build --no-cache streamlit
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d --force-recreate streamlit
	

# ----------------------------
# Service-level logs
# ----------------------------

logs-inference-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) logs -f inference-api

logs-streamlit-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) logs -f streamlit

logs-mlflow-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) logs -f mlflow

logs-airflow-webserver-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) logs -f airflow-webserver

logs-airflow-scheduler-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) logs -f airflow-scheduler


# restart

restart-inference-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) restart inference-api

restart-streamlit-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) restart streamlit

restart-frontend-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) restart inference-api streamlit

start-frontend-dev:
	$(COMPOSE_DEV) -p $(PROJECT_NAME_DEV) up -d inference-api gateway-api streamlit