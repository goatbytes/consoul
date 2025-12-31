.PHONY: help install test lint format type-check clean build docs openapi

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	poetry install

install-dev:  ## Install with all dev dependencies
	poetry install --with dev,docs,security

test:  ## Run tests with coverage
	poetry run pytest -v --cov

test-fast:  ## Run tests without coverage
	poetry run pytest -v

lint:  ## Run linting checks
	poetry run ruff check src/ tests/

lint-fix:  ## Run linting with auto-fix
	poetry run ruff check --fix src/ tests/

format:  ## Format code with ruff
	poetry run ruff format src/ tests/

format-check:  ## Check code formatting
	poetry run ruff format --check src/ tests/

type-check:  ## Run type checking with mypy
	poetry run mypy src/

quality:  ## Run all quality checks (lint, format-check, type-check)
	poetry run ruff check src/ tests/
	poetry run ruff format --check src/ tests/
	poetry run mypy src/

security:  ## Run security checks (bandit, safety)
	poetry run bandit -r src/ -c pyproject.toml
	poetry run safety check --json

security-audit:  ## Run comprehensive security audit
	poetry run bandit -r src/ -c pyproject.toml -f json -o bandit-report.json
	poetry run safety check --save-json safety-report.json
	@echo "Security reports generated: bandit-report.json, safety-report.json"

clean:  ## Remove build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf bandit-report.json
	rm -rf safety-report.json
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

build:  ## Build distribution packages
	poetry build

docs:  ## Build documentation with MkDocs
	.venv/bin/mkdocs build

docs-serve:  ## Serve documentation locally
	.venv/bin/mkdocs serve

pre-commit:  ## Run pre-commit hooks on all files
	poetry run pre-commit run --all-files

update:  ## Update dependencies
	poetry update

openapi:  ## Export OpenAPI spec to docs/api/openapi.json
	poetry run python scripts/generate_openapi_clients.py
