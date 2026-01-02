![Race to the Crystal Logo](logo.png)

# Race to the Crystal

A networked multiplayer vector graphics game for 2-4 players with Tron/Battlezone-style visuals featuring both **2D top-down** and **3D first-person** views.

> **AI Disclosure**: This project was created with AI assistance for both code and assets.

## About

Race to the Crystal is a strategy game where players compete to capture a central crystal by deploying tokens across a 24x24 grid. The game features:

- **Dual rendering modes**: 2D top-down and 3D first-person views
- **Tron-style vector graphics** with glow effects and GPU acceleration
- **Strategic gameplay** with generators, mystery squares, and combat mechanics
- **Local hot-seat multiplayer** for 2-4 players on the same computer
- **Network multiplayer** with server-client architecture
- **AI players** with multiple strategy modes (random, aggressive, defensive)
- **Visual generator connections**: Flowing animated lines connect active generators to the crystal, disappearing when captured

## Tech Stack

- **Python** with **Arcade** for GPU-accelerated rendering
- **OpenGL** for 3D wireframe graphics and shaders
- **BFS pathfinding** for token movement
- **JSON serialization** for game state management
- **199 unit tests** using pytest with 100% pass rate

## How to Play

### Installation & Running

```bash
# Install dependencies
uv sync
```

#### Option 1: Local Hot-Seat Game (Human Players Only)

```bash
# Run the game via main menu
uv run race-to-the-crystal
# Click "Play Local Hot-Seat Game"

# Or run directly (2D mode)
uv run race-direct

# Run in 3D mode (direct startup)
uv run race-direct --3d

# Run with custom player count (2-4)
uv run race-direct 2
uv run race-direct --3d 2
```

#### Option 2: Network Multiplayer (Human + AI Players)

**Start the server first (required):**
```bash
# Terminal 1: Start the server
uv run race-server
```

**Then connect clients:**

```bash
# Human player via GUI
uv run race-to-the-crystal
# Click "Host Network Game" or "Join Network Game"

# AI player (creates a game and waits)
uv run race-ai-client --create "My Game" --name "AI_Alice"

# Another AI player (joins existing game)
uv run race-ai-client --join <game-id> --name "AI_Bob" --strategy aggressive
```

**AI Strategies:**
- `random` - Random action selection (default)
- `aggressive` - Prioritizes attacks and forward movement
- `defensive` - Prioritizes deployment and safe moves

**Complete Example - Mixed Human/AI Game:**
```bash
# Terminal 1: Start server
uv run race-server

# Terminal 2: Human hosts game via GUI
uv run race-to-the-crystal
# Click "Host Network Game", create "Mixed Game"

# Terminal 3: AI joins
uv run race-ai-client --join <game-id> --name "Bot1" --strategy aggressive

# Terminal 4: Another AI joins
uv run race-ai-client --join <game-id> --name "Bot2"
```

See [NETWORK.md](docs/NETWORK.md) for complete network multiplayer documentation.

### Controls

#### 2D Mode Controls
- **Arrow Keys / WASD**: Pan camera view
- **+/-** or **Mouse Scroll**: Zoom in/out
- **Mouse Click**: Select tokens, move, attack, deploy

#### 3D Mode Controls
- **Right Mouse Button + Move**: Mouse-look (free camera rotation)
- **Q/E**: Rotate camera left/right
- **TAB**: Cycle through your tokens
- **Arrow Keys / WASD**: Pan camera position
- **+/-** or **Mouse Scroll**: Adjust field of view
- **Mouse Click**: Select tokens, move, attack, deploy

#### Common Controls (Both Modes)
- **V**: Toggle between 2D and 3D view modes
- **Space/Enter**: End turn
- **Escape**: Cancel action
- **M**: Toggle background music on/off
- **Ctrl+Q**: Quit game

### Music

The game automatically generates a simple techno beat on startup if no music file is found. The generated track includes bass drums, hi-hats, and synth elements.

If you want to use custom music, place your music file named `techno.mp3` in `client/assets/music/`. Supported formats include MP3, WAV, OGG, and FLAC. The music loops automatically during gameplay.

### Deploying Tokens

Players start with **3 tokens already deployed** in their starting corner, ready to move immediately!

To deploy additional tokens from your reserve (17 remaining):
1. Click your starting corner position (the corner cell)
2. Select a token type from the menu (10hp, 8hp, 6hp, or 4hp)
3. Click any empty cell in your corner area to deploy
4. Press ESC to cancel at any time

**Note:** The camera automatically zooms to fit the entire 24x24 board in view at startup. Use +/- to zoom further if needed.

### Game Rules

1. **Objective**: Capture the central crystal by holding it with 12 tokens for 3 turns
2. **Movement**: Each token can move 1-2 spaces per turn depending on its health
3. **Combat**: Attack adjacent enemies (damage = attacker health / 2)
4. **Generators**: Capture to reduce crystal requirement
5. **Mystery Squares**: Random events (heal or teleport)

See [GAME.md](GAME.md) for complete rules.

## Development

### Project Structure

```
race-to-the-crystal/
├── game/          # Core game logic (rendering-independent)
├── client/        # Rendering, UI, and AI client
├── server/        # Network game server
├── network/       # Protocol and connection handling
├── shared/        # Constants and enums
├── tests/         # Unit tests (199 tests)
└── docs/          # Documentation (NETWORK.md, GAME.md)
```

For detailed documentation:
- **Game Rules**: [docs/GAME.md](docs/GAME.md)
- **Network Multiplayer**: [docs/NETWORK.md](docs/NETWORK.md)
- **Development Guide**: [CLAUDE.md](CLAUDE.md)

### Running Tests

```bash
# Run all tests
make test

# Run specific test
make test-specific FILE=tests/test_token.py

# See all test commands
make help
```

### Dependencies

```bash
# Install all dependencies
uv sync --group dev

# Install only production dependencies
uv sync
```

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE.md) file for details.
