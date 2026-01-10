# Race to the Crystal - Web 3D Client

This module provides a web-based 3D client for Race to the Crystal using Babylon.js 8.

## Migration Notice

**The standalone FastAPI server is now deprecated.** Use the unified game server instead, which supports both desktop and web clients:

```bash
# Old (deprecated):
uv run race-web-server

# New (recommended):
uv run race-unified-server
# Then open http://localhost:8080 in your browser
```

The unified server provides the same web client functionality with added benefits:
- Desktop and web clients can play together in the same game
- Single source of truth for game state
- Better resource efficiency
- Unified deployment

See the [Unified Server Architecture](#unified-server-architecture) section below.

## Unified Server Architecture

The unified server (`server/game_server.py`) combines the HTTP/WebSocket server with the TCP game server on a single process:

```
Unified Game Server (started with --unified flag)
├── TCP Handler (port 8888)
│   └── Desktop Arcade clients
├── HTTP/WebSocket Handler (port 8080)
│   ├── Static file serving (HTML/JS/CSS)
│   └── WebSocket connections for web clients
└── Game Coordinator
    └── Shared GameState for all connected clients
```

### Starting the Unified Server

```bash
# Default: TCP on 8888, HTTP/WebSocket on 8080
uv run race-unified-server

# Or explicitly:
uv run race-server --unified

# Custom ports:
uv run race-server --unified --port 8888 --http-port 8080

# With debug logging:
uv run race-server --unified --debug
```

### Advantages Over Standalone FastAPI Server

1. **Mixed Client Support**: Desktop clients connecting via TCP and web clients connecting via WebSocket can play in the same game
2. **Single GameState**: No duplication - one source of truth for game state
3. **Automatic Synchronization**: All clients receive updates via their respective protocols
4. **Easier Deployment**: Single server process instead of two separate services
5. **Resource Efficiency**: Shared game sessions and elimination of redundant broadcasts

### Web Client Connection

When using the unified server, the web client's WebSocket connects to:
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
```

The server handles the protocol translation internally, so the web client works identically to the standalone FastAPI version.

## Architecture

### Backend (FastAPI)

The FastAPI server (`web_server/main.py`) provides:

- **REST API Endpoints:**
  - `GET /` - Serves the main game HTML page
  - `GET /api/game/state` - Returns current game state as JSON
  - `POST /api/game/new?num_players=2` - Creates a new game
  - `POST /api/game/action` - Executes a game action (move, attack, deploy, end turn)

- **WebSocket Endpoint:**
  - `WS /ws/game` - Real-time bidirectional game state updates
    - Server broadcasts game state changes to all connected clients
    - Clients can send actions via WebSocket for immediate execution

- **Game State Management:**
  - Uses existing `GameState` class from `game/game_state.py`
  - Leverages built-in serialization (`to_dict()`, `to_json()`)
  - Executes actions via `AIActionExecutor` from `game/ai_actions.py`

### Frontend (Babylon.js 8)

The web client (`web_server/static/game_client.js`) implements:

- **3D Rendering:**
  - Wireframe grid board with vertical pillars and horizontal connectors
  - Hexagonal prism tokens with player colors
  - Special cells: generators (orange cubes), crystal (magenta pyramid)
  - Glow effects matching the Tron/Battlezone aesthetic

- **Camera System:**
  - ArcRotateCamera for overview perspective
  - Mouse controls: drag to rotate, scroll to zoom
  - Keyboard controls: WASD for pan, Q/E for rotation

- **Real-time Updates:**
  - WebSocket connection for instant game state synchronization
  - Automatic reconnection on disconnect
  - Smooth token movement animations

- **HUD Display:**
  - Current turn number and game phase
  - Active player indicator
  - Player list with token counts
  - Control instructions

## Installation

1. Install dependencies:
   ```bash
   uv sync
   ```

2. The following packages are required:
   - `fastapi>=0.115.0`
   - `uvicorn[standard]>=0.32.0`
   - `websockets>=13.0`

## Running the Web Client

### Recommended: Unified Server (Supports Desktop + Web Clients)

```bash
uv run race-unified-server
# Open http://localhost:8080 in your browser
```

### Deprecated: Standalone FastAPI Server

```bash
# Old method - not recommended
uv run race-web-server
# Open http://localhost:8000 in your browser

# Or directly with uvicorn
uv run uvicorn web_server.main:app --host 0.0.0.0 --port 8000 --reload
```

The standalone server will start on `http://localhost:8000`, but it cannot support desktop clients.

## Usage

1. Open your browser to `http://localhost:8000`
2. The game will automatically connect via WebSocket
3. View the 3D board with tokens and special cells
4. Use keyboard controls:
   - **Space**: End turn
   - **R**: Create new game
   - **Mouse drag**: Rotate camera
   - **Mouse scroll**: Zoom in/out

## API Examples

### Get Game State (REST)

```bash
curl http://localhost:8000/api/game/state
```

### Create New Game (REST)

```bash
curl -X POST http://localhost:8000/api/game/new?num_players=2
```

### Execute Action (REST)

```bash
curl -X POST http://localhost:8000/api/game/action \
  -H "Content-Type: application/json" \
  -d '{
    "type": "move",
    "player_id": 0,
    "token_id": 5,
    "destination": [12, 12]
  }'
```

### WebSocket Connection (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/game');

ws.onopen = () => {
    console.log('Connected');
};

ws.onmessage = (event) => {
    const gameState = JSON.parse(event.data);
    console.log('Game state updated:', gameState);
};

// Send action via WebSocket
ws.send(JSON.stringify({
    type: 'end_turn',
    player_id: 0
}));
```

## File Structure

```
web_server/
├── __init__.py           # Module initialization
├── main.py               # FastAPI application and game manager
├── README.md             # This file
├── templates/
│   └── index.html        # Main game HTML page
└── static/
    └── game_client.js    # Babylon.js 3D client
```

## Integration with Existing Codebase

The web server integrates seamlessly with the existing game logic:

- **Game Logic:** Uses `game/` modules (no modifications needed)
- **Serialization:** Uses existing `to_dict()` and `from_dict()` methods
- **Actions:** Uses `AIActionExecutor` for consistent action validation/execution
- **Separation:** No rendering dependencies - pure game state management

## Future Enhancements

Potential improvements:

1. **Player Input:** Click to select tokens and move them
2. **Hover Effects:** Highlight cells under mouse cursor
3. **Valid Moves:** Show green wireframes for valid destinations
4. **Deployment Menu:** UI for deploying tokens from reserve
5. **Camera Modes:** Switch between overview and first-person views
6. **Generator Lines:** Animated flowing lines from generators to crystal
7. **Mystery Square Animation:** Coin-flip rotation effect
8. **Health Display:** Show token health values as text labels
9. **Sound Effects:** Add audio for moves, attacks, captures
10. **Multiplayer:** Support multiple human players with different views

## Technical Details

### Coordinate System

Babylon.js uses a **right-handed coordinate system** (Y-up):
- X-axis: left/right (matches board X)
- Y-axis: forward/back (matches board Y)
- Z-axis: up/down (height)

The Python client uses screen coordinates (Y-down), so conversions may be needed for advanced features.

### Rendering Performance

- Wireframe rendering is efficient with Babylon.js
- Glow layer adds minimal overhead
- ~1000 line meshes render at 60 FPS

### State Synchronization

- WebSocket broadcasts on every game state change
- Clients maintain local copy of game state
- Animations prevent jarring visual updates

## Troubleshooting

**Problem:** WebSocket connection fails
- **Solution:** Ensure server is running and check firewall settings

**Problem:** 3D scene doesn't render
- **Solution:** Check browser console for Babylon.js errors, ensure WebGL is supported

**Problem:** Game state doesn't update
- **Solution:** Check WebSocket connection status in HUD, refresh page to reconnect

**Problem:** Dependencies fail to install
- **Solution:** Run `uv sync` to ensure all packages are installed
