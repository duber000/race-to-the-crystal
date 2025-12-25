# Race to the Crystal - Implementation Plan

## Project Status

**Current Phase**: Phase 2 ✓ COMPLETED
**Next Phase**: Phase 3 - Network Infrastructure (OR: Arcade Migration - see MIGRATION.md)
**Overall Progress**: 40% (2 of 5 phases complete)

**Latest Milestone**: Complete Tron-style UI with local hot-seat gameplay (2,700+ lines)

**Technology Decision**: Migrating to Arcade + asyncio + GIL-free Python (see MIGRATION.md - IN PROGRESS)

### Files Completed (Phase 1)
```
race-to-the-crystal/
├── pyproject.toml          ✓ (uv project configuration)
├── GAME.md                 ✓ (game rules)
├── PLAN.md                 ✓ (this file)
├── shared/
│   ├── __init__.py         ✓
│   ├── constants.py        ✓ (game parameters)
│   └── enums.py            ✓ (type definitions)
├── game/
│   ├── __init__.py         ✓
│   ├── token.py            ✓ (token entities)
│   ├── board.py            ✓ (grid and cells)
│   ├── player.py           ✓ (player state)
│   ├── game_state.py       ✓ (central state)
│   ├── movement.py         ✓ (pathfinding)
│   ├── combat.py           ✓ (combat resolution)
│   ├── generator.py        ✓ (generator mechanics)
│   ├── crystal.py          ✓ (win conditions)
│   └── mystery_square.py   ✓ (random events)
└── tests/
    ├── __init__.py         ✓
    ├── test_token.py       ✓ (14 tests)
    ├── test_board.py       ✓ (22 tests)
    ├── test_movement.py    ✓ (17 tests)
    ├── test_combat.py      ✓ (17 tests)
    ├── test_generator.py   ✓ (19 tests)
    ├── test_crystal.py     ✓ (20 tests)
    └── test_game_state.py  ✓ (31 tests)

Total: 140 tests, 100% passing
```

### Files Completed (Phase 2)
```
race-to-the-crystal/
├── MIGRATION.md             ✓ (Arcade + PyGaSe migration plan)
├── client/
│   ├── client_main.py       ✓ (local hot-seat game entry - 338 lines)
│   ├── input_handler.py     ✓ (mouse/keyboard input - 274 lines)
│   └── ui/
│       ├── camera.py        ✓ (viewport & transforms - 154 lines)
│       ├── vector_graphics.py ✓ (glow effects - 313 lines)
│       ├── board_view.py    ✓ (board rendering - 229 lines)
│       ├── token_view.py    ✓ (token sprites - 268 lines)
│       ├── ui_elements.py   ✓ (HUD components - 363 lines)
│       └── renderer.py      ✓ (main coordinator - 250 lines)
└── game/
    └── game_state.py        ✓ (enhanced: turn_phase, get_current_player)

Total: 2,777 lines added
- Camera system with zoom/pan
- Tron-style glow effects
- Complete HUD system
- Local multiplayer ready
- 60 FPS target rendering
```

---

## Overview
Build a networked multiplayer vector graphics game for 2-4 players using Python with clean geometric Tron-style visuals.

**⚠️ Technology Stack Update**: Currently migrating from Pygame to **Arcade + asyncio + GIL-free Python 3.14** for better performance and modern architecture. See [MIGRATION.md](MIGRATION.md) for details and progress.

## Game Summary
- 4-player strategic board game on a grid
- Each player starts with 20 dice tokens (health: 10, 8, 6, 4) from corner positions
- Goal: Capture central power crystal and hold for 3 turns with 12 tokens
- 4 generators can be disabled to reduce crystal requirements
- Turn-based combat and movement
- Mystery squares with random effects

## Technical Architecture

### Network Design
- **Model**: Client-Server (server-authoritative)
- **Transport**: TCP sockets with JSON messages
- **Synchronization**: Server validates all actions, broadcasts state updates
- **Lobby**: Players join/create games, ready up, then start

### Project Structure
```
race-to-the-crystal/
├── main.py                    # Launcher (choose client/server)
├── requirements.txt
├── GAME.md                    # Game rules
├── PLAN.md                    # This file
├── client/                    # Game client and rendering
│   ├── __init__.py
│   ├── client_main.py
│   ├── game_client.py        # Network client
│   ├── input_handler.py
│   └── ui/                    # All rendering code
│       ├── __init__.py
│       ├── renderer.py
│       ├── vector_graphics.py
│       ├── board_view.py
│       ├── token_view.py
│       ├── ui_elements.py
│       └── camera.py
├── server/                    # Game server
│   ├── __init__.py
│   ├── server_main.py
│   ├── game_server.py        # TCP server
│   ├── lobby.py
│   └── game_coordinator.py
├── game/                      # Core game logic (network-agnostic)
│   ├── __init__.py
│   ├── game_state.py         # Central state management
│   ├── board.py              # Grid representation
│   ├── token.py              # Token entities
│   ├── player.py
│   ├── rules.py              # Validation
│   ├── movement.py           # Pathfinding
│   ├── combat.py
│   ├── generator.py
│   ├── crystal.py
│   └── mystery_square.py
├── network/                   # Networking utilities
│   ├── __init__.py
│   ├── protocol.py           # Message definitions
│   ├── connection.py         # TCP wrapper
│   └── messages.py
├── shared/                    # Constants and utilities
│   ├── __init__.py
│   ├── constants.py          # Game configuration
│   ├── enums.py
│   └── utils.py
└── tests/                     # Unit tests
    ├── __init__.py
    ├── test_game_logic.py
    ├── test_movement.py
    ├── test_combat.py
    └── test_network.py
```

### Key Design Decisions

**Turn-Based System**
- Each player's turn: Movement → Action (Attack/Capture) → End Turn
- Server validates moves before applying
- 30-second timer per turn
- No client-side prediction needed (turn-based allows waiting for server)

**State Management**
- Server maintains single authoritative GameState
- Full state sync on join/reconnect
- Delta updates for actions during gameplay
- GameState serializes to JSON for network transmission

**Movement**
- All tokens move 2 spaces per turn
- 8-directional movement (including diagonals)
- BFS pathfinding to calculate valid destinations
- Cannot move through other tokens

**Combat**
- Adjacent attacks only
- Damage = attacker.health // 2 (no damage to attacker)
- If defender health ≤ 0, token is removed

**Generators**
- Hold with 2+ tokens for 2 consecutive turns to disable
- Each disabled generator reduces crystal requirement by 2 tokens
- 4 generators total (one per quadrant)

**Crystal Capture & Win**
- Base requirement: 12 tokens for 3 turns
- Adjusted by disabled generators: 12 - (disabled_count * 2)
- First player to meet requirement wins

**Mystery Squares**
- Random coin flip when token lands on square
- Heads: Heal to full health
- Tails: Teleport back to starting position
- 8-12 total (2-3 per quadrant)

### Visual Style (Tron-Inspired)
- Dark background (#0a0a0f)
- Neon glow effects on all elements
- Player colors: Cyan, Magenta, Yellow, Green
- Smooth animations for movement and combat
- Vector graphics using pygame.draw primitives

### Network Protocol

**Message Types**:
- Connection: CONNECT, DISCONNECT, HEARTBEAT
- Lobby: JOIN_LOBBY, READY, START_GAME
- Actions: MOVE_TOKEN, ATTACK, CAPTURE_GENERATOR, CAPTURE_CRYSTAL
- Updates: FULL_STATE, STATE_UPDATE, TURN_CHANGE
- Events: COMBAT_RESULT, MYSTERY_EVENT, GAME_WON

**Message Format** (JSON):
```json
{
  "type": "MOVE_TOKEN",
  "timestamp": 1234567890,
  "player_id": "uuid-string",
  "data": {
    "token_id": 5,
    "from": [2, 3],
    "to": [4, 3]
  }
}
```

### Dependencies

**Current (Pygame Implementation)**:
```
pygame>=2.5.0              # Graphics and game loop (requires SDL2 system libs)
pytest>=8.0.0              # Testing framework
```

**New Stack (Migration In Progress)** - See MIGRATION.md:
```
arcade>=2.6.17             # Modern OpenGL game framework
pytest>=8.0.0              # Testing framework
Python 3.14 (free-threaded)# With GIL disabled by default
# asyncio + sockets: Built-in to Python (no external dependency)
```

## Implementation Phases

### Phase 1: Core Game Logic (Local/Hot-Seat) ✓ COMPLETED
**Goal**: Playable game with all mechanics working locally

**Tasks**:
1. ✓ Create project structure and shared utilities
2. ✓ Implement core entities: Token, Board, Player, GameState
3. ✓ Build movement system with pathfinding
4. ✓ Implement combat resolution
5. ✓ Add generator capture mechanics
6. ✓ Add crystal capture and win condition checking
7. ✓ Implement mystery square effects
8. ✓ Unit tests for all game logic (140 tests, 100% passing)

**Deliverable**: Console-based or minimal UI hot-seat game for 2-4 players

**Files Created**:
- ✓ `shared/constants.py` - Game parameters (board size, token values, timings)
- ✓ `shared/enums.py` - Type definitions (CellType, GamePhase, PlayerColor)
- ✓ `game/token.py` - Token entity with health, position, actions
- ✓ `game/board.py` - Grid structure with cells and special squares
- ✓ `game/player.py` - Player state and token management
- ✓ `game/game_state.py` - Central state management
- ✓ `game/movement.py` - Movement validation and pathfinding
- ✓ `game/combat.py` - Combat resolution
- ✓ `game/generator.py` - Generator capture mechanics
- ✓ `game/crystal.py` - Crystal capture and win conditions
- ✓ `game/mystery_square.py` - Random event handling
- ✓ `pyproject.toml` - Python dependencies (using uv)

**Tests Created**:
- ✓ `tests/test_token.py` - 14 tests for token mechanics
- ✓ `tests/test_board.py` - 22 tests for board and cells
- ✓ `tests/test_movement.py` - 17 tests for pathfinding
- ✓ `tests/test_combat.py` - 17 tests for combat system
- ✓ `tests/test_generator.py` - 19 tests for generator capture
- ✓ `tests/test_crystal.py` - 20 tests for win conditions
- ✓ `tests/test_game_state.py` - 31 tests for state management

### Phase 2: Vector Graphics & UI ✓ COMPLETED
**Goal**: Beautiful Tron-style visualization

**Tasks**:
1. ✓ Set up Pygame window and main loop
2. ✓ Implement camera/viewport system (zoom, pan, screen transforms)
3. ✓ Create vector drawing utilities (glow effects, anti-aliasing)
4. ✓ Render board grid with special squares highlighted
5. ✓ Render tokens as glowing hexagons/circles with health numbers
6. ✓ Build HUD (turn indicator, player info, action buttons)
7. ✓ Implement input handling (mouse selection, keyboard shortcuts)
8. ✓ Add animations (smooth movement, combat flashes, particles)

**Deliverable**: Fully playable local game with polished graphics ✓

**Files Created**:
- ✓ `client/ui/camera.py` - Viewport management (154 lines)
- ✓ `client/ui/vector_graphics.py` - Drawing utilities with glow effects (313 lines)
- ✓ `client/ui/board_view.py` - Board rendering (229 lines)
- ✓ `client/ui/token_view.py` - Token visualization (268 lines)
- ✓ `client/ui/ui_elements.py` - HUD components (363 lines)
- ✓ `client/ui/renderer.py` - Main rendering coordinator (250 lines)
- ✓ `client/input_handler.py` - Keyboard/mouse input processing (274 lines)
- ✓ `client/client_main.py` - Client application entry (local mode) (338 lines)
- ✓ `MIGRATION.md` - Comprehensive Arcade + PyGaSe migration plan (568 lines)

**Game State Enhancements**:
- ✓ Added `turn_phase` tracking (MOVEMENT/ACTION/END_TURN)
- ✓ Added `get_current_player()` helper method
- ✓ Added `current_player_id` and `game_phase` properties

**Controls Implemented**:
- ✓ Mouse click - Select tokens and move
- ✓ Arrow Keys/WASD - Pan camera
- ✓ +/- or Mouse Wheel - Zoom in/out
- ✓ Right Mouse Drag - Pan camera
- ✓ Space/Enter - End turn
- ✓ Escape - Cancel selection
- ✓ Ctrl+Q - Quit game

**Note**: Migration to Arcade + asyncio + GIL-free Python 3.14 is IN PROGRESS. See MIGRATION.md for details.

**Migration Progress**:
- ✅ Python 3.14 free-threaded installed and verified
- ✅ Arcade installed
- ✅ Basic Arcade window structure created
- ✅ Token sprite rendering implemented
- ✅ Board rendering implemented
- ⏸️ UI/HUD migration pending
- ⏸️ Input handling migration pending
- ⏸️ Networking (using asyncio instead of PyGaSe)

### Phase 3: Network Infrastructure
**Goal**: Multiplayer over LAN/Internet

**Tasks**:
1. Design and implement JSON message protocol
2. Create TCP server with client connection management
3. Build lobby system (create/join games, ready status)
4. Implement game coordinator for multiple concurrent sessions
5. Create network client for server communication
6. Implement state synchronization (full state + deltas)
7. Add heartbeat and disconnection handling
8. Test with multiple clients on LAN

**Deliverable**: Networked multiplayer with lobby working on LAN

**Files to Create**:
- `network/protocol.py` - Message definitions and serialization
- `network/connection.py` - TCP connection wrapper
- `network/messages.py` - Message type enumerations
- `server/game_server.py` - TCP server and client handling
- `server/lobby.py` - Lobby management
- `server/game_coordinator.py` - Game session orchestration
- `server/server_main.py` - Server application entry
- `client/game_client.py` - Network client (update client_main.py)
- `main.py` - Application launcher (choose client/server mode)

### Phase 4: Polish & Features
**Goal**: Production-ready game

**Tasks**:
1. Add reconnection support (save game state, allow rejoin)
2. Implement turn timer with auto-forfeit
3. Add in-game chat
4. Create main menu and settings screen
5. Add victory screen with statistics
6. Implement spectator mode
7. Handle all edge cases (simultaneous disconnects, invalid moves)
8. Performance optimization (60 FPS, <100ms server response)
9. Comprehensive testing (integration, stress tests, playtesting)

**Deliverable**: Polished, release-ready game

### Phase 5: Deployment
**Goal**: Ready for distribution

**Tasks**:
1. Write user documentation (setup, gameplay, controls)
2. Create installation/setup scripts
3. Package game for distribution
4. Bug fixes from playtesting
5. Balance adjustments based on feedback

## Key Implementation Notes

### Separation of Concerns
- Game logic (game/) is completely independent of rendering and networking
- Enables thorough unit testing
- Client and server share game logic code

### Server-Authoritative Model
- Server validates ALL actions before applying
- Prevents cheating and ensures consistency
- Clients never modify state directly

### Testing Strategy
- Unit tests for all game logic (movement, combat, win conditions)
- Integration tests for network message handling
- Playtesting: 2-player, 4-player, 2v2 team scenarios
- Stress testing: disconnects, latency simulation, concurrent games

### Performance Targets
- 60 FPS rendering (smooth animations)
- <100ms server response time
- Support 4 concurrent games per server instance

## Risks & Mitigations

**Network sync complexity** → Turn-based design simplifies synchronization (or PyGaSe auto-sync)
**Rendering performance** → Migrating to Arcade (GPU-accelerated) for 60+ FPS
**Python GIL limitations** → Python 3.14 with GIL disabled for true parallelism
**Runaway leader** → Mystery squares can reset leading players
**Games too long** → Turn timers and automatic forfeit
**Spawn camping** → Can add spawn protection if needed during playtesting
**Migration risk** → Phased approach available; Pygame implementation complete as fallback

## Current Status & Next Steps

**Completed** (Phases 1 & 2):
1. ✅ Core game logic with 140 passing unit tests
2. ✅ Complete Tron-style UI with local hot-seat gameplay
3. ✅ 2,700+ lines of rendering code
4. ✅ Full camera, input, and HUD systems

**Next Steps**:

**Migration to Modern Stack IN PROGRESS** (see MIGRATION.md):
- ✅ Python 3.14 free-threaded installed and verified (3.53x speedup confirmed)
- ✅ Arcade installed and basic window structure created
- ✅ Token and board sprites implemented
- 🔄 UI/HUD migration (next priority)
- 🔄 Input handling migration
- ⏸️ Network implementation with **asyncio + sockets** (not PyGaSe - unmaintained)
- ⏸️ Multi-threading integration
- ⏸️ Testing and optimization

**Technology Change**: Using **asyncio + sockets** instead of PyGaSe for networking:
- PyGaSe is not actively maintained
- asyncio is Python standard library (always maintained)
- Full control over protocol
- Better long-term sustainability

**Estimated Remaining Time**: 1-2 days
