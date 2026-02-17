PROJECT_NAME=mlops-construction-cost-prediction
DOCKER_COMPOSE = docker compose -f deployments/compose.yaml
DOCKER_COMPOSE_PROD = docker compose -f deployments/compose.yaml -f deployments/compose.prod.yaml
.PHONY: help start stop restart logs ps prod prod-stop build-arm test

help:
	@echo "Available commands:"
	@echo "  make start        Start full stack (dev)"
	@echo "  make stop         Stop stack"
	@echo "  make restart      Restart stack"
	@echo "  make logs         Follow logs"
	@echo "  make ps           Show running services"
	@echo "  make prod         Start full stack (production / ARM64)"
	@echo "  make prod-stop    Stop production stack"
	@echo "  make build-arm    Build ARM64 images with buildx"
	@echo "  make test         Run tests"


start:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d postgres
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) run --rm airflow-init
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d mlflow airflow-webserver airflow-scheduler inference-api streamlit

stop:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) down

restart: stop start

logs:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) logs -f

ps:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) ps

prod:
	$(DOCKER_COMPOSE_PROD) -p $(PROJECT_NAME) up -d postgres
	$(DOCKER_COMPOSE_PROD) -p $(PROJECT_NAME) run --rm airflow-init
	$(DOCKER_COMPOSE_PROD) -p $(PROJECT_NAME) up -d mlflow airflow-webserver airflow-scheduler inference-api streamlit

prod-stop:
	$(DOCKER_COMPOSE_PROD) -p $(PROJECT_NAME) down

build-arm:
	docker buildx build --platform linux/arm64 -t $(PROJECT_NAME)-mlflow -f deployments/mlflow/Dockerfile.mlflow .
	docker buildx build --platform linux/arm64 -t $(PROJECT_NAME)-airflow -f deployments/airflow/Dockerfile.airflow .
	docker buildx build --platform linux/arm64 -t $(PROJECT_NAME)-inference -f api/inference_api/Dockerfile .
	docker buildx build --platform linux/arm64 -t $(PROJECT_NAME)-streamlit -f deployments/streamlit/Dockerfile.streamlit .

test:
	pytest -v tests/unit/
