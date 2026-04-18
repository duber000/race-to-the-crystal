# Race to the Crystal – Copilot Instructions

## Commands

```bash
# Install dependencies
uv sync --group dev

# Run all tests
make test
# or
uv run --group dev pytest

# Run a single test file
uv run --group dev pytest tests/test_game_state.py

# Run a single test by name
uv run --group dev pytest tests/test_game_state.py::TestGameState::test_add_player

# Run tests with coverage
make test-coverage

# Lint (ruff)
make lint

# Auto-format
make format

# Start the unified server (TCP :5555 + HTTP/WebSocket :8080)
uv run race-unified-server

# Start the desktop client
uv run race-to-the-crystal
```

## Architecture

The project is split into strictly separated layers:

- **`game/`** – Pure game logic with zero rendering or network dependencies. `GameState` (dataclass in `game/game_state.py`) is the central state container. `GameAPI` (`game/api.py`) is the high-level façade used by AI clients and the server coordinator.
- **`shared/`** – Cross-cutting primitives: `enums.py` (all game enums), `constants.py` (all numeric constants), `types.py` (`TokenID`, `PlayerID`, `Position` type aliases), `errors.py` (standardized error dataclasses).
- **`network/`** – Protocol layer. `NetworkMessage` (JSON over TCP), `MessageType` enum covering all client-server message types.
- **`server/`** – Async server built on asyncio + FastAPI. `GameServer` accepts TCP and HTTP/WebSocket connections; `GameCoordinator` manages `GameSession` instances, each wrapping a `GameState`. JWT auth for the HTTP API is in `server/auth.py`.
- **`client/`** – Desktop client using Python Arcade with OpenGL shaders. `renderer_2d.py` and `renderer_3d.py` implement the two view modes. `ai_client.py` and `http_ai_client.py` are AI player implementations.
- **`web_server/`** – Serves the Babylon.js web frontend. Web clients receive state via Mercure SSE and send actions over WebSocket.
- **`tests/`** – 475+ pytest tests. All tests are in the top-level `tests/` directory, mirroring module names (`test_game_state.py`, `test_combat.py`, etc.).

### Network topology

Desktop clients connect via **TCP (port 5555)**. Web clients connect via **WebSocket (port 8080)** and receive state via **Mercure SSE**. Both converge in the unified server. The AI clients can use either transport.

## Key Conventions

### Error handling
Use the standardized error dataclasses from `shared/errors.py`, not plain exceptions or strings:
- `GameError` – for game logic failures (`CANNOT MOVE: not_in_range | ...`)
- `ValidationError` – for input validation failures
- `ActionError` – for action execution failures after validation passes
- `ServerError` – for internal server errors
- Use string constants from `ErrorCode` for the `reason`/`code` fields

### Type aliases
Always use `TokenID`, `PlayerID`, and `Position` from `shared/types.py` rather than bare `int`, `str`, or `tuple`. They are `NewType` wrappers for type-checker enforcement.

### Constants and enums
All numeric game constants live in `shared/constants.py`. All enums live in `shared/enums.py`. Do not hardcode magic numbers; import from these modules.

### Game logic entry points
- To modify or extend game rules: work inside `game/` (no rendering or network imports allowed)
- To expose a new action to AI/server: add it to `game/ai_actions.py`, then expose via `GameAPI` in `game/api.py`
- To add a new network message: add to `MessageType` in `network/messages.py` and handle in `server/message_router.py`

### Testing
- Tests use `pytest` with `class Test*` containers and `def test_*` methods
- `pytest-asyncio` is available for async tests
- `GameState.create_game(num_players)` followed by `game_state.start_game()` is the standard setup for integration-level tests

### Python version
Requires Python 3.14+. Use modern type annotations (e.g., `X | Y` unions, `list[T]`, `dict[K, V]`).
