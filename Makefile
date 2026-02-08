.PHONY: help build up down restart logs ps clean test

help:
	@echo "Job Scrapper - Docker Commands"
	@echo "================================"
	@echo "make build       - Build Docker images"
	@echo "make up          - Start all services"
	@echo "make down        - Stop all services"
	@echo "make restart     - Restart all services"
	@echo "make logs        - View logs (all services)"
	@echo "make logs-api    - View API logs"
	@echo "make logs-worker - View worker logs"
	@echo "make ps          - Show running containers"
	@echo "make clean       - Remove containers, volumes, and images"
	@echo "make test        - Run tests in container"
	@echo "make shell-api   - Shell into API container"
	@echo "make shell-worker- Shell into worker container"
	@echo "make redis-cli   - Open Redis CLI"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo ""
	@echo "✅ Services started!"
	@echo "📊 API: http://localhost:8000"
	@echo "📚 API Docs: http://localhost:8000/api/docs"
	@echo "📈 RQ Dashboard: http://localhost:9181"
	@echo ""
	@echo "View logs: make logs"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-worker:
	docker-compose logs -f worker

ps:
	docker-compose ps

clean:
	docker-compose down -v --rmi all
	@echo "✅ Cleaned up containers, volumes, and images"

test:
	docker-compose run --rm api pytest

shell-api:
	docker-compose exec api /bin/bash

shell-worker:
	docker-compose exec worker /bin/bash

redis-cli:
	docker-compose exec redis redis-cli

# Development shortcuts
dev-up:
	docker-compose up redis rq-dashboard -d
	@echo "✅ Redis and RQ Dashboard started"
	@echo "📈 RQ Dashboard: http://localhost:9181"
	@echo ""
	@echo "Run locally:"
	@echo "  python -m uvicorn src.api.main:app --reload"
	@echo "  python worker.py"

init-db:
	docker-compose exec api python -c "from src.database.connection import init_db; init_db(); print('✅ Database initialized')"
