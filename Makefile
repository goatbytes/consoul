.PHONY: help install test lint format type-check clean build docs

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

clean:  ## Remove build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

build:  ## Build distribution packages
	poetry build

docs:  ## Build documentation
	@echo "Documentation build not yet configured"

pre-commit:  ## Run pre-commit hooks on all files
	poetry run pre-commit run --all-files

update:  ## Update dependencies
	poetry update
