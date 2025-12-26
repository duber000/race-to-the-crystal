# Race to the Crystal

A networked multiplayer vector graphics game for 2-4 players with Tron/Battlezone-style visuals featuring both **2D top-down** and **3D first-person** views.

## Project Status

**Phase 1: Core Game Logic** ✓ **COMPLETED**
- 140 unit tests, 100% passing
- All game mechanics implemented and tested

**Phase 2: Graphics & UI** ✓ **COMPLETED**
- Arcade-based GPU-accelerated rendering
- Tron-style wireframe vector graphics with glow effects
- **NEW**: First-person 3D maze view with transparent walls
- Dual rendering modes (2D/3D) with seamless switching
- Fully playable local hot-seat game

**Next**: Phase 3 - Network Infrastructure

## Quick Start

### Playing the Game

```bash
# Install dependencies
uv sync

# Run the game (starts in 2D mode)
uv run race-to-the-crystal

# In-game controls:
# - Click token: Select it
# - Click cell: Move selected token (ends your turn)
# - Click enemy: Attack with selected token (ends your turn)
# - Space/Enter: End turn
# - Escape: Cancel selection
# - V: Toggle between 2D and 3D views
# - TAB: Switch between tokens (3D mode)
# - Q/E: Rotate camera (3D mode)
```

### Running Tests

The project uses `uv` for dependency management and includes a Makefile for convenient testing.

```bash
# Run all tests
make test

# Run tests with verbose output
make test-verbose

# Run tests with minimal output
make test-fast

# Run only failed tests from last run
make test-failed

# Run specific test file
make test-specific FILE=tests/test_token.py

# Show all available commands
make help
```

### Alternative: Direct pytest commands

```bash
# Using the venv directly
.venv/bin/pytest

# Using uv run (if venv not set up)
uv run --group dev pytest

# With verbose output
.venv/bin/pytest -v

# Run specific test
.venv/bin/pytest tests/test_combat.py -v
```

### Dependencies

```bash
# Sync all dependencies including dev dependencies
uv sync --group dev

# Or just sync production dependencies
uv sync
```

## Development

### Project Structure

```
race-to-the-crystal/
├── game/              # Core game logic (network-agnostic)
│   ├── board.py       # 24x24 grid with special cells
│   ├── token.py       # Token entities (health: 10, 8, 6, 4)
│   ├── player.py      # Player state management
│   ├── game_state.py  # Central game state
│   ├── movement.py    # BFS pathfinding (8-directional)
│   ├── combat.py      # Combat resolution
│   ├── generator.py   # Generator capture mechanics
│   ├── crystal.py     # Crystal capture & win conditions
│   └── mystery_square.py  # Random events
├── client/            # Rendering and UI (Arcade-based)
│   ├── game_window.py     # Main window with dual 2D/3D modes
│   ├── camera_3d.py       # First-person perspective camera
│   ├── board_3d.py        # 3D wireframe grid renderer
│   ├── token_3d.py        # 3D hexagonal token geometry
│   ├── shaders/           # GLSL shaders for glow effects
│   └── sprites/           # 2D sprite rendering
├── shared/            # Constants and enumerations
│   ├── constants.py   # Game parameters (2D & 3D)
│   └── enums.py       # Type definitions
└── tests/             # Unit tests (140 tests)
    ├── test_token.py       # 14 tests
    ├── test_board.py       # 22 tests
    ├── test_movement.py    # 17 tests
    ├── test_combat.py      # 17 tests
    ├── test_generator.py   # 19 tests
    ├── test_crystal.py     # 20 tests
    └── test_game_state.py  # 31 tests
```

### Game Rules

See [GAME.md](GAME.md) for complete game rules and mechanics.

### Implementation Plan

See [PLAN.md](PLAN.md) for the full implementation roadmap.

## Features (Implemented ✓)

### Game Mechanics
- ✓ **Board**: 24x24 grid with 4 starting corners, 1 crystal, 4 generators, 8-12 mystery squares
- ✓ **Tokens**: 20 per player (5×10hp, 5×8hp, 5×6hp, 5×4hp)
- ✓ **Movement**: Fast tokens (6hp, 4hp) move 2 spaces; slow tokens (8hp, 10hp) move 1 space; 8-directional with BFS pathfinding
- ✓ **Turn Actions**: Each turn you can either move OR attack, but not both
- ✓ **Combat**: Adjacent attacks, damage = attacker.health // 2, attacker takes no damage
- ✓ **Generators**: Hold with 2 tokens for 2 turns to disable, reduces crystal requirement by 2
- ✓ **Crystal**: Win by holding with 12 tokens (or less if generators disabled) for 3 turns
- ✓ **Mystery Squares**: Coin flip - heal to full or teleport to start
- ✓ **Serialization**: Full JSON serialization for network transmission

### Rendering & Graphics
- ✓ **Dual View Modes**: Toggle between 2D top-down and 3D first-person
- ✓ **Vector Aesthetics**: Tron/Battlezone-style wireframe graphics with glow
- ✓ **3D Perspective**: First-person camera with token switching and rotation
- ✓ **Transparent Walls**: See-through wireframe maze in 3D mode
- ✓ **GPU Acceleration**: OpenGL-based rendering via Arcade
- ✓ **Ray Casting**: 3D mouse picking for token selection

## Testing

All game logic is thoroughly tested with 140 unit tests covering:
- Token mechanics (creation, damage, healing, movement)
- Board generation and special cell placement
- Movement validation and pathfinding
- Combat resolution and damage calculation
- Generator capture mechanics
- Crystal capture and win conditions
- Game state management and serialization

Run tests to verify everything works:

```bash
make test
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
