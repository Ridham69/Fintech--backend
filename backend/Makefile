.PHONY: run test lint migrate clean install dev

# Development
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

# Testing
test:
	pytest --asyncio-mode=auto -v

test-cov:
	pytest --asyncio-mode=auto -v --cov=app --cov-report=term-missing

# Code Quality
lint:
	ruff check .
	ruff format . --check

format:
	ruff format .

# Database
migrate:
	alembic upgrade head

migrate-rollback:
	alembic downgrade -1

migrate-create:
	alembic revision --autogenerate -m "$(message)"

# Dependencies
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +
	find . -type d -name ".coverage" -exec rm -r {} +
	find . -type d -name "dist" -exec rm -r {} +
	find . -type d -name "build" -exec rm -r {} +

# Help
help:
	@echo "Available commands:"
	@echo "  make run          - Run the application in development mode"
	@echo "  make dev          - Run with debug logging"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make migrate      - Run database migrations"
	@echo "  make install      - Install dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make clean        - Clean up cache files" 