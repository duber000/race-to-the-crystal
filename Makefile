.PHONY: test test-verbose test-watch clean help

help: ## Show this help message
	@echo "Race to the Crystal - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

test: ## Run all tests
	@if [ -f .venv/bin/pytest ]; then \
		.venv/bin/pytest; \
	else \
		uv run --group dev pytest; \
	fi

test-verbose: ## Run tests with verbose output
	@if [ -f .venv/bin/pytest ]; then \
		.venv/bin/pytest -vv; \
	else \
		uv run --group dev pytest -vv; \
	fi

test-coverage: ## Run tests with coverage report
	uv run --group dev --with pytest-cov pytest --cov=game --cov=shared --cov-report=term-missing

test-watch: ## Run tests in watch mode (requires pytest-watch)
	uv run --group dev --with pytest-watch ptw

test-fast: ## Run tests with minimal output
	@if [ -f .venv/bin/pytest ]; then \
		.venv/bin/pytest -q; \
	else \
		uv run --group dev pytest -q; \
	fi

test-failed: ## Run only previously failed tests
	@if [ -f .venv/bin/pytest ]; then \
		.venv/bin/pytest --lf; \
	else \
		uv run --group dev pytest --lf; \
	fi

test-specific: ## Run specific test file (usage: make test-specific FILE=tests/test_token.py)
	@if [ -f .venv/bin/pytest ]; then \
		.venv/bin/pytest $(FILE); \
	else \
		uv run --group dev pytest $(FILE); \
	fi

clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .coverage -exec rm -rf {} +

lint: ## Run code formatting checks (requires ruff)
	uv run --with ruff ruff check .

format: ## Auto-format code (requires ruff)
	uv run --with ruff ruff format .

sync: ## Sync dependencies
	uv sync --group dev
