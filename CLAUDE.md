# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Race to the Crystal is a Python-based multiplayer strategy game with GPU-accelerated vector graphics. Players compete on a 24x24 grid to capture a central crystal while managing tokens, generators, and strategic resources. The game features:
- **2D Desktop Client**: Top-down view using Arcade/OpenGL rendering
- **3D Web Client**: Browser-based 3D view using FastAPI backend and Babylon.js rendering

## Development Commands

### Running the Game

#### Local Single-Player (2D/3D Desktop)
```bash
# Install dependencies
uv sync

# Run game (2D mode)
uv run race-to-the-crystal

# Run game in 3D mode
uv run race-to-the-crystal --3d

# Run with custom player count
uv run race-to-the-crystal 2
uv run race-to-the-crystal --3d 2
```

#### Network Multiplayer (Desktop Clients)
```bash
# Terminal 1: Start the TCP game server
uv run race-server

# Terminal 2+: Start desktop clients connecting to server
uv run race-direct
```

#### Unified Server (Desktop + Web Clients)
```bash
# Start unified server (TCP for desktop clients, HTTP/WebSocket for web clients)
uv run race-unified-server

# Or with explicit flag:
uv run race-server --unified

# Custom ports:
uv run race-server --unified --port 8888 --http-port 8080

# Then in browser: open http://localhost:8080
# Desktop clients connect to: localhost:8888
```

#### Web-Only (Legacy FastAPI Mode - Deprecated)
```bash
# Deprecated: Use unified server instead
uv run race-web-server
# Then open http://localhost:8000 in your browser
```

**Game Controls:**
- **Arrow Keys / WASD**: Pan camera view
- **+/-** or **Mouse Scroll**: Zoom in/out
- **Mouse Click**: Select tokens, move, attack, deploy
- **R**: Open Deployment Menu
- **Space/Enter**: End turn
- **Escape**: Cancel action
- **Ctrl+Q**: Quit game

**Token Deployment:**
1. Click your starting corner position (corner cell with tokens)
2. Select a token type from the menu (10hp, 8hp, 6hp, or 4hp)
3. Click any empty cell in your corner area (9 cells total) to deploy
4. Press ESC to cancel at any time

**Note:** Players start with 3 tokens already deployed in their corner, ready to move immediately!

**Note:** The camera automatically zooms to fit the entire 24x24 board in view at startup. Use +/- to zoom further if needed.

### Testing
```bash
# Run all tests
make test

# Run specific test file
make test-specific FILE=tests/test_token.py

# Run tests with verbose output
make test-verbose

# Run tests with coverage
make test-coverage

# Run only previously failed tests
make test-failed

# Quick test run (minimal output)
make test-fast
```

### Code Quality
```bash
# Lint code
make lint

# Format code
make format

# Clean Python cache files
make clean

# Sync dependencies
make sync
```

## Architecture Overview

### Core Design Principle: Separation of Game Logic and Rendering

The codebase strictly separates game mechanics from visual presentation:

- **game/**: Pure game logic with NO rendering dependencies - all logic is testable without graphics
- **client/**: All rendering and UI code using Arcade framework
- **shared/**: Constants and enums used by both game and client

### Module Structure

#### `game/` - Core Game Logic
Contains all game mechanics, rules, and state management. These modules have NO dependencies on rendering libraries.

**Key files:**
- `game_state.py`: Central state container managing all entities and game phase
- `ai_actions.py`: Action classes (Move, Attack, Deploy, EndTurn) with validation/execution
  - Returns `ActionResult` and `ValidationResult` dataclasses (not tuples)
- `ai_observation.py`: Converts game state to text descriptions for AI players (enables headless AI gameplay)
- `board.py`: 24x24 grid with cell types (normal, generator, crystal, mystery)
  - Uses `shared/corner_layout.py` for deployment position calculations
- `token.py`: Token entities with health, position, movement range
- `player.py`: Player state and token ownership
- `movement.py`: BFS pathfinding for token movement
- `combat.py`: Combat resolution (damage = attacker.health // 2)
  - Clean, self-documenting code without redundant comments
- `generator.py`: Generator capture mechanics (2 tokens for 2 turns)
  - Uses helper methods: `_count_tokens_by_player()`, `_find_dominant_player()`, `_process_capture_logic()`
  - Self-documenting method names eliminate need for "what" comments
- `crystal.py`: Win condition tracking (12 tokens for 3 turns, reduced by disabled generators)
  - Uses helper methods: `_count_tokens_by_player()`, `_find_dominant_player()`, `_process_win_logic()`
  - Self-documenting method names eliminate need for "what" comments
- `mystery_square.py`: Random events (heal or teleport)

**Critical architectural detail:** The `ai_observation.py` and `ai_actions.py` modules provide a complete text-based API for interacting with the game. This enables:
1. AI players to play without rendering
2. Automated testing of game mechanics
3. Network multiplayer (future)
4. Headless game simulations

#### `client/` - Rendering and UI
All Arcade/OpenGL rendering code. Consumes `GameState` but never modifies game logic.

**Architecture:** The client uses a **delegation pattern** with specialized controllers to manage different responsibilities. The main `GameView` class (515 lines) delegates to focused controllers rather than handling everything itself.

**Key files:**
- `game_window.py`: Main Arcade window coordinating rendering loop and delegating to controllers
- **Controllers** (delegation pattern):
  - `audio_manager.py`: Background music and generator hum management
  - `camera_controller.py`: 2D/3D camera systems and coordinate conversion
  - `deployment_menu_controller.py`: Deployment UI (R hexagon indicator and menu)
  - `input_handler.py`: Mouse/keyboard input routing and selection state
  - `game_action_handler.py`: Game action execution (move, attack, deploy, end turn)
  - `renderer_2d.py`: 2D sprite rendering and animations
  - `renderer_3d.py`: 3D model rendering and OpenGL shaders
- **3D Rendering:**
  - `board_3d.py`: 3D wireframe board with OpenGL shaders
  - `camera_3d.py`: First-person camera system
  - `token_3d.py`: 3D hexagonal prism token models
- **2D Rendering:**
  - `sprites/`: 2D sprite implementations for tokens and board elements
- **UI:**
  - `ui/arcade_ui.py`: UIManager with player panels, generator status, and interactive buttons

**Dual rendering modes:**
- **2D**: Top-down Tron-style vector graphics with glow effects
- **3D**: First-person Battlezone-style wireframe graphics with dual camera modes
- Toggle between modes with 'V' key during gameplay
- Start in 3D mode directly with `--3d` command-line flag

**3D Camera System:**
The 3D mode features two distinct camera perspectives:

- **Overview Mode** (initial state):
  - Position: 150 units above board center
  - Pitch: -60° (looking steeply down)
  - Provides bird's-eye strategic view of entire battlefield

- **First-Person Mode** (after TAB):
  - Position: 20 units behind token, 30 units above ground
  - Pitch: -15° (looking forward/slightly down)
  - Immersive token eye-level perspective
  - Press TAB to cycle through your tokens
  - Q/E to rotate camera, Right-click+drag for mouse-look

**3D Visual Feedback:**
- **Hover Indicator**: White glowing wireframe on cell under mouse (ray casting)
- **Valid Moves**: Green glowing wireframes show valid move destinations
- **Real-time Updates**: Both indicators update every frame for responsive feedback
- **Layered Rendering**: Hover (height=2.0) renders above valid moves (height=1.0)

**2D/3D Common Visual features:**
- Flowing animated lines connect active generators to the crystal
- Enhanced generator glow effects
- Lines automatically disappear when generators are captured

See [docs/3D.md](docs/3D.md) for complete 3D mode documentation including camera architecture, controls, and development guide.

#### `shared/` - Shared Definitions
Constants, enums, and configuration objects shared between game logic and rendering.

**Key files:**
- `enums.py`: GamePhase, TurnPhase, PlayerColor, CellType, etc.
- `constants.py`: All numeric constants (board size, token counts, capture requirements, colors)
  - **3D Camera Constants**: `CAMERA_OVERVIEW_PITCH`, `CAMERA_FIRST_PERSON_PITCH`, `CAMERA_OVERVIEW_HEIGHT`, `CAMERA_FIRST_PERSON_HEIGHT`, `CAMERA_FIRST_PERSON_OFFSET`
  - **Camera Behavior**: `CAMERA_ROTATION_INCREMENT` (15°), `MOUSE_LOOK_SENSITIVITY` (0.3)
  - **Projection**: `CAMERA_FOV` (75°), `CAMERA_NEAR_PLANE`, `CAMERA_FAR_PLANE`
- `corner_layout.py`: Corner position configurations for player deployment areas
  - `BoardCornerConfig`: Board-space corner deployment logic (3x3 deployment zones)
  - `UICornerConfig`: UI-space corner indicator and menu positioning
  - Data-driven approach eliminates if-elif chains for player-specific positioning
- `ui_config.py`: UI parameter objects to improve method signatures
  - `ViewportConfig`: Window and viewport dimensions (window_width, window_height, hud_height)
  - `UIStyleConfig`: UI styling parameters (margin, indicator_size, spacing)
- `logging_config.py`: Centralized logging configuration

**Important:** When changing game rules, update constants in `shared/constants.py` rather than hardcoding values.

#### `server/` - Unified Game Server (TCP + HTTP/WebSocket)
Central multiplayer game server supporting both desktop and web clients.

**Architecture:**
The unified server runs on a single process with dual protocol support:
- **TCP Server** (port 8888): Desktop Arcade clients using asyncio protocol
- **HTTP/WebSocket Server** (port 8080): Web browser clients using aiohttp
- **Single GameState**: All clients share one authoritative game state

**Key modules:**
- `game_server.py`: Main server handling all connections, routing, and coordination
  - `_handle_new_connection()`: TCP connection handler with CONNECT/RECONNECT protocol
  - `_handle_message()`: Routes incoming messages to appropriate handlers
  - `_broadcast_game_state()`: Sends updates to all connected clients
  - Reconnection support with 5-minute timeout window
  
- `lobby.py`: Lobby management for game creation/joining
  - `LobbyManager`: Tracks available games and player readiness
  - `GameStatus`: Enum for lobby, playing, and finished states
  - Supports mixed lobbies (desktop + web clients simultaneously)
  
- `game_coordinator.py`: Active game session management
  - `GameCoordinator`: Manages all running games
  - `GameSession`: Per-game state wrapping `GameState`
  - `AIActionExecutor`: Validates and executes player actions
  
- `websocket_handler.py`: WebSocket connection handler for web clients
  - `WebSocketHandler`: Manages client connections and message routing
  - Protocol translation between WebSocket and internal formats
  - Handles authentication and player registration
  
- `http_handler.py`: HTTP server for static file serving
  - Serves HTML/CSS/JS frontend from `web_server/static/`
  - Serves `/static/*` assets
  - Serves root `/` to load game client
  
- `ai_spawner.py`: AI player management
  - Spawns AI processes for automated players
  - Manages AI process lifecycle and cleanup
  - Enables AI testing and demonstration games

**Network Protocol:**
Uses JSON-based binary protocol with message types:
- `CONNECT`: New client joins (includes player name, client type)
- `RECONNECT`: Returning client resumes session
- `LOBBY_*`: Lobby state management (list, create, join, ready, start)
- `FULL_STATE`: Complete game state (sent after actions, broadcasts to all)
- `MOVE`, `ATTACK`, `DEPLOY`, `END_TURN`: Game actions
- `GAME_WON`: Win condition met
- `CHAT`: Player chat messages

**Running the unified server:**
```bash
# Run unified server (TCP on 8888, HTTP/WebSocket on 8080)
uv run race-unified-server

# Or explicitly:
uv run race-server --unified

# Custom ports:
uv run race-server --unified --port 8888 --http-port 8080

# With debug logging:
uv run race-server --unified --debug
```

**Mixed Client Support:**
- Desktop clients connect via TCP to port 8888
- Web clients connect via WebSocket to port 8080
- Both client types can play in the same game simultaneously
- All state updates broadcast to all connected clients automatically

#### `network/` - Network Protocol Layer
Low-level networking implementation for TCP and binary message handling.

**Key modules:**
- `connection.py`: TCP connection wrapper with async message I/O
- `protocol.py`: Binary protocol encoding/decoding and message factories
- `messages.py`: Message type enums and client type tracking

#### `web_server/` - Web Client (FastAPI + Babylon.js - Deprecated)
Alternative 3D rendering using web technologies. Provides browser-based multiplayer viewing.

**Architecture:**
- **FastAPI Backend** (`main.py`): REST API and WebSocket server for game state management
  - REST endpoints: `/api/game/state`, `/api/game/new`, `/api/game/action`
  - WebSocket: `/ws/game` for real-time bidirectional updates
  - Uses existing `GameState` serialization (`to_dict()`, `to_json()`)
  - Executes actions via `AIActionExecutor` for consistency
- **Babylon.js Frontend** (`static/game_client.js`): Browser-based 3D renderer
  - Wireframe graphics matching Tron/Battlezone aesthetic
  - Hexagonal prism tokens with player colors
  - Special cells: generators (cubes), crystal (pyramid)
  - Glow layer for visual effects
  - ArcRotateCamera for overview perspective
  - WebSocket client for real-time synchronization

**Key features:**
- No modifications to game logic required
- Browser-based multiplayer viewing capability
- Real-time game state synchronization
- Smooth animations for token movement
- HUD with turn info and player status

**Running the web server (Deprecated):**
```bash
# DEPRECATED: Use unified server instead
uv run race-web-server
# Open http://localhost:8000 in browser
```

**Migration to Unified Server:**
The standalone FastAPI server is now deprecated. Instead, use the unified server:
```bash
# Instead of:
uv run race-web-server

# Use:
uv run race-unified-server
# Open http://localhost:8080 in browser
```

The unified server provides the same web client functionality but also supports desktop clients connecting simultaneously.

See `web_server/README.md` for migration notes and detailed web client documentation.

#### `tests/` - Unit Tests
276 pytest tests covering all game mechanics. Tests use pure game logic without rendering.

### Game State Flow

1. **GameState** is the single source of truth containing:
   - Board (24x24 grid)
   - Players (dict of player_id → Player)
   - Tokens (dict of token_id → Token)
   - Generators (list of 4 generators)
   - Crystal (single central crystal)
   - Turn tracking (current_turn_player_id, turn_number, phase)

2. **Turn Phases** (in `shared.enums.TurnPhase`):
   - **MOVEMENT**: Player can move or deploy a token
   - **ACTION**: Player can attack or end turn
   - Transitions: MOVEMENT → ACTION (after move/deploy) → MOVEMENT (after end turn)

3. **Game Phases** (in `shared.enums.GamePhase`):
   - **SETUP**: Players joining
   - **PLAYING**: Active game
   - **ENDED**: Game finished

4. **Token Management**:
   - Each player has 20 tokens: 5×10hp, 5×8hp, 5×6hp, 5×4hp
   - At game start, 3 tokens are **automatically deployed** to starting corner positions
   - Remaining 17 tokens start in **reserve** (is_deployed=False)
   - Deploy tokens to board via `game_state.deploy_token()`
   - Deployed tokens can move/attack
   - Movement range: **Dynamic based on current health** - tokens with 7+ HP move 1 space, 6 or less HP move 2 spaces
   - Combat: Damage = attacker.health // 2, attacker takes no damage

5. **Win Condition**:
   - Hold crystal with N tokens for 3 consecutive turns
   - Base requirement: 12 tokens
   - Each disabled generator reduces requirement by 2
   - Generators disabled by holding with 2 tokens for 2 turns

### AI Integration Architecture

The game is designed to be playable by AI without visual rendering:

1. **Observation** (`ai_observation.py`):
   - `AIObserver.describe_game_state()`: Full text description of game state
   - `AIObserver.get_board_map()`: ASCII art map
   - `AIObserver.list_available_actions()`: All valid actions for current phase
   - `AIObserver.get_situation_report()`: Complete report combining all above

2. **Actions** (`ai_actions.py`):
   - Action classes: `MoveAction`, `AttackAction`, `DeployAction`, `EndTurnAction`
   - `AIActionExecutor.validate_action()`: Check if action is valid
   - `AIActionExecutor.execute_action()`: Execute action and return result
   - All validation includes detailed error messages for AI debugging

3. **Example AI Play Loop**:
   ```python
   from game.ai_observation import AIObserver
   from game.ai_actions import AIActionExecutor, MoveAction

   # Get game state as text
   report = AIObserver.get_situation_report(game_state, player_id)

   # List valid actions
   actions = AIObserver.list_available_actions(game_state, player_id)

   # Execute action
   executor = AIActionExecutor()
   action = MoveAction(token_id=5, destination=(12, 12))
   success, message, data = executor.execute_action(action, game_state, player_id)
   ```

### Testing Strategy

The project has 276 unit tests organized by game system:

- `test_board.py`: Grid and cell management
- `test_token.py`: Token state and behavior
- `test_movement.py`: Movement validation and pathfinding
- `test_combat.py`: Combat resolution
- `test_generator.py`: Generator capture mechanics
- `test_crystal.py`: Win condition logic
- `test_game_state.py`: State management and turn flow
- `test_ai_observation.py`: AI observation API
- `test_ai_actions.py`: AI action execution

**Playtesting:** Use the `/playtesting` skill or `test_gameplay_flaws.py` to run automated AI playtests. This is especially useful after implementing new features to verify end-to-end gameplay.

## Important Conventions

### Code Quality Standards

This codebase follows strict quality standards to maintain readability and maintainability:

1. **Self-Documenting Code**:
   - Use descriptive method and variable names
   - Extract complex logic into well-named helper methods
   - Only comment "why", never "what" (the code should show what it does)
   - Example: Instead of `# Count tokens by player`, use `player_token_counts = self._count_tokens_by_player(tokens)`

2. **Parameter Objects Over Long Parameter Lists**:
   - Use dataclasses to group related parameters
   - Example: `ViewportConfig(window_width, window_height, hud_height)` instead of passing 3+ individual parameters
   - Makes code self-documenting and easier to extend

3. **Data-Driven Configuration**:
   - Use configuration objects and dictionaries instead of if-elif chains
   - Example: `corner_layout.py` uses `BOARD_CORNER_CONFIGS` dict instead of player_index conditionals
   - Single source of truth for configuration data

4. **Return Value Objects**:
   - Use dataclasses for complex return types instead of tuples
   - Example: `ActionResult(success, message, data)` instead of `tuple[bool, str, dict | None]`
   - Self-documenting and prevents positional argument errors

5. **Delegation Pattern**:
   - Delegate responsibilities to focused, single-purpose classes
   - Example: `GameView` delegates to `CameraController`, `InputHandler`, `Renderer2D`, etc.
   - Each controller has a clear, focused responsibility

6. **Modern Python Features** (Python 3.9-3.14):
   - **Type Hints** (PEP 604, PEP 585): Use `T | None` instead of `Optional[T]`, `tuple[int, int]` instead of `Tuple[int, int]`
   - **Self Type** (PEP 673): Use `Self` for classmethod returns instead of forward references
   - **Pattern Matching** (PEP 634): Use `match-case` for action dispatching instead of if-elif chains
   - **Walrus Operator** (PEP 572): Use `:=` for cleaner conditional assignments
   - **TypeAlias** (PEP 613): Explicit type alias annotations for better IDE support

   **Examples:**
   ```python
   # Modern type hints (Python 3.9+)
   def get_token(token_id: int) -> Token | None:  # Not Optional[Token]
       return self.tokens.get(token_id)

   def get_position(self) -> tuple[int, int]:  # Not Tuple[int, int]
       return (self.x, self.y)

   # Self type for classmethods (Python 3.11+)
   from typing import Self

   @classmethod
   def from_dict(cls, data: dict) -> Self:  # Not "GameState"
       return cls(**data)

   # Pattern matching (Python 3.10+)
   match action:
       case MoveAction():
           return self._validate_move(action, game_state, player_id)
       case AttackAction():
           return self._validate_attack(action, game_state, player_id)
       case _:
           return ValidationResult(False, "Unknown action type")

   # Walrus operator (Python 3.8+)
   if token := game_state.tokens.get(token_id):
       return token.health
   ```

### Game Logic Modifications

When modifying game mechanics:

1. **Update game logic** in `game/` modules
2. **Update tests** in `tests/` to match new behavior
3. **Update constants** in `shared/constants.py` if rules changed
4. **Run full test suite** to ensure nothing broke
5. **Run playtesting** to verify mechanics work in actual gameplay
6. Client rendering (`client/`) should automatically reflect changes since it reads from `GameState`

### Token State Management

Tokens have two key boolean flags:
- `is_deployed`: Whether token is on the board (False = in reserve)
- `is_alive`: Whether token is active (False = destroyed)

**Critical:** Always use `game_state.deploy_token()` to move tokens from reserve to board. Never manually set `is_deployed=True` without also updating the board occupancy grid.

### Board Occupancy

The board maintains an occupancy grid tracking tokens at each position. **Multiple tokens can stack on generator and crystal cells** to enable capture mechanics:

- Use `board.set_occupant(position, token_id)` to add a token to a cell
- Use `board.clear_occupant(position, token_id)` to remove a specific token from a cell
- Use `board.clear_occupant(position)` to clear all tokens from a cell
- Use `board.get_cell_at(position).is_occupied()` to check if any tokens are present
- Use `board.get_cell_at(position).occupants` to get list of token IDs at that cell
- **Critical:** Keep occupancy grid in sync with token positions

**Token Stacking Rules:**
- Multiple friendly tokens can occupy the same **generator** or **crystal** cell
- Tokens cannot stack on normal cells (only one token per normal cell)
- Enemy tokens always block movement (cannot stack with enemies)

### Generator and Crystal Updates

Generator capture and crystal win conditions are checked at **end of turn** in `GameState.end_turn()`:
1. Call `GeneratorManager.update_all_generators()` to check captures
2. Call `CrystalManager.check_win_condition()` to check for winner
3. If winner found, call `game_state.set_winner(player_id)`

This means changes to token positions don't immediately affect capture/win status until turn ends.

## Python Version and Dependencies

- **Python 3.14** required (see `.python-version`)
- **uv** package manager (replaces pip/venv)
- **arcade** for rendering (GPU-accelerated)
- **numpy** for vector math
- **pytest** for testing

## Common Gotchas

1. **Movement range is dynamic**: Movement range is based on **current health**, not max health. Tokens with 7+ HP move 1 space, while tokens with 6 or less HP move 2 spaces. This means damaged tokens become more mobile - an 8hp token that takes 4 damage becomes 4hp and gains the ability to move 2 spaces.

2. **Phase transitions**: Moving or deploying automatically changes phase to ACTION. You cannot move twice in one turn.

3. **Reserve vs Deployed**: Tokens in reserve cannot move or attack. They must be deployed first via `deploy_token()`.

4. **Generator capture reset**: If a different player's tokens occupy a generator, capture progress resets for the previous player.

5. **Rendering independence**: The client can be completely ignored when testing game logic. Use `AIObserver` for headless testing.

6. **Turn end timing**: Generators and crystal are checked AFTER end turn, not during token actions. This means you can't win mid-turn.

## Skills Available

This repository has custom Claude Code skills:

- `/playtesting`: Automated AI gameplay testing to find bugs and verify mechanics
- `/python`: Python package management using uv
- `/testing-graphics`: Test 2D/3D rendering via screenshots
- `/testing-python`: Run pytest tests

Use these skills for specialized testing and development tasks.
