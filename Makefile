.PHONY: help install install-dev test lint format clean docker-build docker-up docker-down

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies with uv"
	@echo "  make install-dev  - Install all dependencies including dev tools"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters (flake8, mypy)"
	@echo "  make format       - Format code with black and isort"
	@echo "  make format-check - Check code formatting without changes"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start services with docker-compose"
	@echo "  make docker-down  - Stop services"

# Install dependencies using uv (faster than pip)
install:
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv..."; \
		uv pip install -r requirements.txt; \
	else \
		echo "uv not found, falling back to pip..."; \
		pip install -r requirements.txt; \
	fi

install-dev:
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv..."; \
		uv pip install -r requirements.txt -r requirements-dev.txt; \
	else \
		echo "uv not found, falling back to pip..."; \
		pip install -r requirements.txt -r requirements-dev.txt; \
	fi

# Testing
test:
	pytest tests/ -v

test-integration:
	pytest tests/integration/deployment -v -m p1

test-all:
	pytest tests/ -v --cov=. --cov-report=html

# Linting
lint:
	flake8 . --max-line-length=100 --extend-ignore=E203,W503
	mypy . --ignore-missing-imports

# Formatting
format:
	black .
	isort .

format-check:
	black --check .
	isort --check .

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Cleaning
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage htmlcov/ test-results*.json test-report*.html

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

# Database migrations
migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-down:
	alembic downgrade -1

# Development server
run:
	uvicorn app:app --reload --host 0.0.0.0 --port 8000

run-worker:
	python worker.py
