PROJECT_NAME=mlops

.PHONY: help start stop restart logs ps

help:
	@echo "Available commands:"
	@echo "  make start        Start full stack"
	@echo "  make stop         Stop stack"
	@echo "  make restart      Restart stack"
	@echo "  make logs         Follow logs"
	@echo "  make ps           Show running services"

start:
	docker compose -p $(PROJECT_NAME) up -d --build

stop:
	docker compose -p $(PROJECT_NAME) down

restart: stop start

logs:
	docker compose -p $(PROJECT_NAME) logs -f

ps:
	docker compose -p $(PROJECT_NAME) ps
