.PHONY: help install build up down ps logs test migrate seed clean

help:
	@echo "NeuroSleepNet Makefile"
	@echo "-----------------------"
	@echo "install      - Install dependencies on host (for local development)"
	@echo "build        - Build Docker images"
	@echo "up           - Start development stack"
	@echo "down         - Stop development stack"
	@echo "ps           - Show running containers"
	@echo "logs         - Tail logs from all containers"
	@echo "test         - Run backend tests"
	@echo "migrate      - Run database migrations"
	@echo "seed         - Seed demo data"
	@echo "clean        - Remove .venv, volumes and objects"

install:
	cd backend && uv sync

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

ps:
	docker compose ps

logs:
	docker compose logs -f

test:
	cd backend && uv run pytest

migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python infra/scripts/seed_demo.py

clean:
	rm -rf backend/.venv
	docker compose down -v
