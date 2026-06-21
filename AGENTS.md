# Race to the Crystal

## Commands

```bash
# Validate all Kukicha syntax
kukicha check ./...

# Build all packages
kukicha build ./...

# Run all tests
make test
# or
kukicha build ./... && go test ./...

# Run tests with verbose output
make test-verbose

# Run a specific test package
make test-specific PKG=./game/...

# Lint (check formatting)
make lint
# or
kukicha fmt -w --check .

# Auto-format
make format
# or
kukicha fmt -w .

# Build and run the desktop client
make desktop-run

# Build and run the AI client
make ai-client-run

# Build and run the web server
make web-server-run

# Clean build artifacts
make clean
```

## Architecture

The project is split into strictly separated layers:

- **`game/`** – Pure game logic with zero rendering or network dependencies. `GameState` (struct in `game/game_state.kuki`) is the central state container. `GameAPI` (`game/api.kuki`) is the high-level façade used by AI clients and the server coordinator. `schemas.kuki` defines all action/response types.
- **`shared/`** – Cross-cutting primitives: `enums/` (all game enums), `constants/` (all numeric constants), `types/` (`TokenID`, `PlayerID`, `Position` type aliases), `errs/` (standardized error definitions).
- **`server/`** – Server built on Go net/http + gorilla/websocket. `GameCoordinator` manages `GameSession` instances, each wrapping a `GameState`. JWT auth for the HTTP API is in `server/auth.kuki`. Mercure SSE publishing is in `server/mercure_publisher.kuki`.
- **`client/`** – Desktop client using Ebitengine. `renderer_2d.kuki` and UI views in `ui/` implement the game views. `ai/ai_client.kuki` and `ai/http_ai_client.kuki` are AI player implementations.
- **`web_server/`** – Serves the Babylon.js web frontend. Web clients receive state via Mercure SSE and send actions over WebSocket.
- **Test files** – `*_test.kuki` files co-located with the modules they test (e.g., `game/game_state_test.kuki`, `game/combat_test.kuki`).

### Network topology

Desktop clients connect via **TCP (port 5555)**. Web clients connect via **WebSocket (port 8080)** and receive state via **Mercure SSE**. Both converge in the unified server. The AI clients can use either transport.

## Key Conventions

### Error handling
Use the standardized error values from `shared/errs/`, not panic or plain strings:
- `GameError` – for game logic failures (`CANNOT MOVE: not_in_range | ...`)
- `ValidationError` – for input validation failures
- `ActionError` – for action execution failures after validation passes
- `ServerError` – for internal server errors
- Use string constants from `ErrorCode` for the `reason`/`code` fields

### Type aliases
Always use `TokenID`, `PlayerID`, and `Position` from `shared/types/` rather than bare `int`, `string`, or `struct`. They are `type` aliases for type-checker enforcement.

### Constants and enums
All numeric game constants live in `shared/constants/`. All enums live in `shared/enums/`. Do not hardcode magic numbers; import from these packages.

### Game logic entry points
- To modify or extend game rules: work inside `game/` (no rendering or network imports allowed)
- To expose a new action to AI/server: add it to `game/ai_actions.kuki`, then expose via `GameAPI` in `game/api.kuki`
- To add a new network message: add to `MessageType` and handle in the server message routing

### Testing
- Tests use Go's `testing` package with `func Test...` functions
- `*_test.kuki` files are co-located with the modules they test
- `GameState.create_game(num_players)` followed by `game_state.start_game()` is the standard setup for integration-level tests

### Go version
Requires Go 1.26+. See `go.mod` for the current version.

