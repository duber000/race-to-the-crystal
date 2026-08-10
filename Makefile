.PHONY: help check build desktop desktop-run web-server web-server-run test test-verbose test-specific clean lint format learn learn-run learn-check learn-test

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

ai-client: ## Build the AI client
	kukicha build ./client/ai/
	go build -o race-ai-client ./client/ai/

ai-client-run: ## Build and run the AI client
	$(MAKE) ai-client
	./race-ai-client

web-server: ## Build the web server
	kukicha build ./web_server

web-server-run: ## Build and run the web server
	$(MAKE) web-server
	./web_server

learn: ## List learner example scripts
	@ls learn/examples/

learn-run: ## Run a learner example (usage: make learn-run NAME=02-formation)
	kukicha run ./learn/examples/$(NAME)/

learn-check: ## Type-check the learn package and every learner example
	kukicha check ./learn/
	@for d in learn/examples/*/; do kukicha check "$$d"; done

learn-test: ## Brew and run the learn package tests
	kukicha brew ./learn/
	go test ./learn/

test: ## Run all tests
	kukicha build ./...
	go test ./...

test-verbose: ## Run tests with verbose output
	kukicha build ./...
	go test -v ./...

test-specific: ## Run specific test (usage: make test-specific PKG=./game/...)
	kukicha build $(PKG)
	go test $(PKG)

clean: ## Remove build artifacts and empty dirs
	find client/desktop client/ai -name '*.go' -delete
	find . -type f -name '*.go' ! -path './.kukicha/*' ! -path './client/desktop/*' ! -path './client/ai/*' -delete
	rm -f race-desktop race-ai-client web_server/web_server
	find . -type d -empty -delete 2>/dev/null; true

lint: ## Check formatting
	kukicha fmt -w --check .

format: ## Auto-format all Kukicha files
	kukicha fmt -w .
