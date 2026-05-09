.PHONY: help install install-dev test lint format clean build publish docker docker-run security

# Default target
help:
	@echo "Available commands:"
	@echo "  install      Install the package"
	@echo "  install-dev  Install in development mode"
	@echo "  test         Run tests"
	@echo "  lint         Run linting"
	@echo "  format       Format code"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  publish      Publish to PyPI"
	@echo "  docker       Build Docker image"
	@echo "  docker-run   Run Docker container"
	@echo "  security     Run security checks"

# Installation
install:
	pip install .

install-dev:
	pip install -e ".[dev]"

# Testing
test:
	pytest tests/ --cov=neurosleepnet --cov-report=html --cov-report=term

test-fast:
	pytest tests/ -x --ff

test-unit:
	pytest tests/unit/ --cov=neurosleepnet

test-integration:
	pytest tests/integration/

test-e2e:
	pytest tests/e2e/

# Code quality
lint:
	ruff check neurosleepnet/
	black --check neurosleepnet/
	mypy neurosleepnet/
	bandit -r neurosleepnet/

format:
	ruff format neurosleepnet/
	black neurosleepnet/
	isort neurosleepnet/

# Security
security:
	safety check
	bandit -r neurosleepnet/
	pip-audit

# Build and distribution
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

build: clean
	python -m build

publish: build
	twine upload dist/*

# Docker
docker:
	docker build -t neurosleepnet:latest .

docker-run:
	docker run -d \
		--name neurosleepnet \
		-p 8000:8000 \
		-p 3000:3000 \
		-e NSN_MODE=self-host \
		-e NSN_API_KEY=${NSN_API_KEY} \
		neurosleepnet:latest

# Development helpers
dev-setup:
	pip install -e ".[dev]"
	pre-commit install

docs:
	cd docs && mkdocs serve

docs-build:
	cd docs && mkdocs build

# Performance
benchmark:
	python benchmarks/run_benchmarks.py

profile:
	python -m cProfile -o profile.stats -m neurosleepnet.cli

# Database
db-migrate:
	alembic upgrade head

db-downgrade:
	alembic downgrade base

db-reset:
	alembic downgrade base
	alembic upgrade head

# Utilities
check-deps:
	pip list --outdated

freeze-deps:
	pip freeze > requirements.txt

backup-data:
	tar -czf backup-$(shell date +%Y%m%d).tar.gz ~/.neurosleepnet/

# CI/CD
ci: install-dev lint test security

ci-fast: install-dev lint test-fast

# Production
deploy-staging:
	@echo "Deploying to staging..."
	# Add staging deployment commands here

deploy-prod:
	@echo "Deploying to production..."
	# Add production deployment commands here
