PROJECT_NAME=mlops-construction-cost-prediction
DOCKER_COMPOSE = docker compose -f deployments/compose.yaml
.PHONY: help start stop restart logs ps

help:
	@echo "Available commands:"
	@echo "  make start        Start full stack"
	@echo "  make stop         Stop stack"
	@echo "  make restart      Restart stack"
	@echo "  make logs         Follow logs"
	@echo "  make ps           Show running services"
	@echo "  make test         Run tests"


start:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d postgres
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) run --rm airflow-init
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d mlflow airflow-webserver airflow-scheduler

stop:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) down

restart: stop start

logs:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) logs -f

ps:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) ps

test:
	pytest -v tests/unit/