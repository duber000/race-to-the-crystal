.PHONY: help check build test test-verbose test-specific clean lint format

help: ## Show this help message
	@echo "Race to the Crystal - Available Commands:"
	@echo ""

check: ## Validate all Kukicha syntax
	kukicha check ./...

build: ## Transpile and build all Kukicha packages
	kukicha build ./...

test: ## Run all tests
	kukicha build ./...
	go test ./...

test-verbose: ## Run tests with verbose output
	kukicha build ./...
	go test -v ./...

test-specific: ## Run specific test (usage: make test-specific PKG=./game/...)
	kukicha build $(PKG)
	go test $(PKG)

clean: ## Remove build artifacts
	find . -type f -name '*.go' ! -path './.kukicha/*' -delete

lint: ## Check formatting
	kukicha fmt -w --check .

format: ## Auto-format all Kukicha files
	kukicha fmt -w .
