# Race to the Crystal - Web 3D View

This module provides a web-based 3D viewer for Race to the Crystal using FastAPI and Babylon.js 8.

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

## Running the Server

Start the FastAPI server:

```bash
# Using the installed script
uv run race-web-server

# Or directly with uvicorn
uv run uvicorn web_server.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

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
