.PHONY: help check build desktop desktop-run test test-verbose test-specific clean lint format

PKG_CONFIG_LIBS = x11 xrandr xcursor xinerama xi xrender gl xxf86vm
CGO_CFLAGS ?= $(shell pkg-config --cflags $(PKG_CONFIG_LIBS) 2>/dev/null)
CGO_LDFLAGS ?= $(shell pkg-config --libs $(PKG_CONFIG_LIBS) 2>/dev/null)

help: ## Show this help message
	@echo "Race to the Crystal - Available Commands:"
	@echo ""

check: ## Validate all Kukicha syntax
	kukicha check ./...

build: ## Transpile and build all Kukicha packages
	kukicha build ./...

desktop: ## Build the desktop client
	kukicha build ./client/desktop/
	CGO_CFLAGS="$(CGO_CFLAGS)" CGO_LDFLAGS="$(CGO_LDFLAGS)" go build -o race-desktop ./client/desktop/

desktop-run: ## Build and run the desktop client
	$(MAKE) desktop
	./race-desktop

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
	find . -type f -path '*/desktop/*.go' ! -name 'adapter.go' ! -name 'desktop_main.go' -delete
	find . -type f -name '*.go' ! -path './.kukicha/*' ! -path '*/desktop/*' -delete
	rm -f race-desktop

lint: ## Check formatting
	kukicha fmt -w --check .

format: ## Auto-format all Kukicha files
	kukicha fmt -w .
