# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Race to the Crystal is a Python-based multiplayer strategy game with GPU-accelerated vector graphics. Players compete on a 24x24 grid to capture a central crystal while managing tokens, generators, and strategic resources. The game features both 2D top-down and 3D first-person views using Arcade/OpenGL rendering.

## Development Commands

### Running the Game
```bash
# Install dependencies
uv sync

# Run game
uv run race-to-the-crystal
```

**Game Controls:**
- **Arrow Keys**: Pan camera view
- **+/-** or **Mouse Scroll**: Zoom in/out
- **V**: Toggle between 2D and 3D view modes
- **Tab** (3D mode): Cycle between controlled tokens
- **A/D** (3D mode): Rotate camera left/right
- **Space/Enter**: End turn
- **Escape**: Cancel action
- **Mouse Click**: Select tokens, move, attack, deploy

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
- `ai_actions.py`: Action classes (Move, Attack, Deploy, EndTurn) and validation/execution
- `ai_observation.py`: Converts game state to text descriptions for AI players (enables headless AI gameplay)
- `board.py`: 24x24 grid with cell types (normal, generator, crystal, mystery)
- `token.py`: Token entities with health, position, movement range
- `player.py`: Player state and token ownership
- `movement.py`: BFS pathfinding for token movement
- `combat.py`: Combat resolution (damage = attacker.health // 2)
- `generator.py`: Generator capture mechanics (2 tokens for 2 turns)
- `crystal.py`: Win condition tracking (12 tokens for 3 turns, reduced by disabled generators)
- `mystery_square.py`: Random events (heal or teleport)

**Critical architectural detail:** The `ai_observation.py` and `ai_actions.py` modules provide a complete text-based API for interacting with the game. This enables:
1. AI players to play without rendering
2. Automated testing of game mechanics
3. Network multiplayer (future)
4. Headless game simulations

#### `client/` - Rendering and UI
All Arcade/OpenGL rendering code. Consumes `GameState` but never modifies game logic.

**Key files:**
- `game_window.py`: Main Arcade window handling rendering loop and input
- `board_3d.py`: 3D wireframe board rendering with OpenGL shaders
- `camera_3d.py`: First-person camera system for 3D mode
- `token_3d.py`: 3D hexagonal prism token rendering
- `sprites/`: 2D sprite implementations for tokens and board elements
- `ui/arcade_ui.py`: UIManager with player panels, generator status, and interactive buttons

**Dual rendering modes:**
- **2D**: Top-down Tron-style vector graphics with glow effects
- **3D**: First-person Battlezone-style wireframe graphics
- Toggle between modes with 'V' key

#### `shared/` - Shared Definitions
Constants and enums shared between game logic and rendering.

- `enums.py`: GamePhase, TurnPhase, PlayerColor, CellType, etc.
- `constants.py`: All numeric constants (board size, token counts, capture requirements, colors)

**Important:** When changing game rules, update constants in `shared/constants.py` rather than hardcoding values.

#### `tests/` - Unit Tests
140+ pytest tests covering all game mechanics. Tests use pure game logic without rendering.

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
   - Tokens start in **reserve** (is_deployed=False)
   - Deploy tokens to board via `game_state.deploy_token()`
   - Deployed tokens can move/attack
   - Movement range: 6hp and 4hp tokens move 2 spaces, others move 1 space
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

The project has 140+ unit tests organized by game system:

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

The board maintains an occupancy grid tracking which token is at each position:
- Use `board.set_occupant(position, token_id)` when placing token
- Use `board.clear_occupant(position)` when removing token
- Use `board.get_cell_at(position).is_occupied()` to check occupancy
- **Critical:** Keep occupancy grid in sync with token positions

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

1. **Movement range confusion**: Only 6hp and 4hp tokens move 2 spaces; 10hp and 8hp move 1 space. This is counter-intuitive (lower health = more speed) but matches game design.

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
