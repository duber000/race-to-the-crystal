# Web Client - Babylon.js 3D Browser Interface

The web client provides a browser-based 3D interface for Race to the Crystal using Babylon.js 8. Players can join games through their browser and play alongside desktop clients.

## Quick Start

```bash
# Start the unified server
uv run race-unified-server

# Open browser to:
http://localhost:8080
```

The web client automatically connects and displays the 3D game view.

## Architecture

### Unified Server Integration

The web client connects to the unified game server which runs both TCP and HTTP/WebSocket protocols:

```
Unified Game Server
├── TCP Handler (port 8888)
│   └── Desktop Arcade clients
├── HTTP/WebSocket Handler (port 8080)
│   ├── Static file serving (HTML/JS/CSS)
│   └── WebSocket connections for web clients
└── Game Coordinator
    └── Shared GameState for all connected clients
```

**Key advantages:**
- Desktop and web clients play together in the same game
- Single source of truth for game state
- Automatic synchronization across all clients
- Unified lobby system

### Frontend Architecture

The web client is built with modular JavaScript components:

**Main Modules:**
- `game_client.js` - Core game loop and coordination
- `game_client.renderer.js` - Babylon.js 3D rendering
- `game_client.websocket.js` - WebSocket connection and protocol
- `game_client.camera.js` - Camera system and controls
- `game_client.input.js` - Mouse and keyboard input
- `game_client.ui.js` - HUD and UI elements
- `game_client.constants.js` - Game constants and configuration

**Rendering Features:**
- Wireframe grid board with vertical pillars
- Hexagonal prism tokens with player colors
- Special cells: generators (orange cubes), crystal (magenta pyramid)
- Glow layer for Tron/Battlezone aesthetic
- ArcRotateCamera for overview perspective
- Real-time position updates via WebSocket

### Backend Integration

The server-side handler (`server/websocket_handler.py`) manages web clients:

**Key responsibilities:**
- Serve static HTML/JS/CSS files via HTTP
- Handle WebSocket connections on `/ws`
- Translate between WebSocket and internal protocol
- Authenticate and register players
- Route messages to/from game coordinator

**State synchronization:**
- Server broadcasts `FULL_STATE` on every action
- Clients update 3D scene based on received state
- Smooth animations prevent jarring updates

## Controls

- **Mouse Drag**: Rotate camera
- **Mouse Scroll**: Zoom in/out
- **WASD**: Pan camera
- **Q/E**: Rotate camera
- **Mouse Click**: Select tokens, move, attack
- **Space**: End turn
- **R**: Create new game (when not in game)

## Protocol

### WebSocket Messages

The web client uses JSON messages over WebSocket:

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
```

**Message format:**
```json
{
  "type": "MESSAGE_TYPE",
  "timestamp": 1234567890.123,
  "player_id": "uuid-string",
  "data": {
    // Message-specific data
  }
}
```

**Key message types:**
- `CONNECT` - Initial connection request
- `CONNECT_ACK` - Server assigns player_id
- `LOBBY_*` - Lobby management (create, join, ready, start)
- `FULL_STATE` - Complete game state update
- `MOVE`, `ATTACK`, `DEPLOY`, `END_TURN` - Game actions
- `CHAT` - Player chat messages
- `GAME_WON` - Victory notification

### State Synchronization

**Full state sync:**
```json
{
  "type": "FULL_STATE",
  "player_id": "uuid",
  "data": {
    "game_state": {
      "board": {...},
      "players": {...},
      "tokens": {...},
      "generators": [...],
      "crystal": {...},
      "current_turn_player_id": "player_0",
      "turn_number": 5
    },
    "your_player_id": "player_0"
  }
}
```

**When state is sent:**
- On game start
- After any action execution
- After turn changes
- On reconnect (if enabled)

## Development

### File Structure

```
web_server/
├── templates/
│   └── index.html              # Main HTML page
└── static/
    ├── game_client.js          # Core game loop
    ├── game_client.renderer.js # 3D rendering
    ├── game_client.websocket.js # WebSocket handling
    ├── game_client.camera.js   # Camera system
    ├── game_client.input.js    # Input handling
    ├── game_client.ui.js       # HUD and UI
    ├── game_client.constants.js # Constants
    └── mercure_client.js       # Mercure SSE client (optional)
```

### Adding Features

**To add a new action:**

1. **Client side** (`game_client.input.js`):
   ```javascript
   function handleClick(pickResult) {
       // Process click
       const message = {
           type: 'NEW_ACTION',
           player_id: playerId,
           data: { /* action data */ }
       };
       ws.send(JSON.stringify(message));
   }
   ```

2. **Server side** - No changes needed if using existing action types

3. **Renderer** (`game_client.renderer.js`):
   ```javascript
   function updateScene(gameState) {
       // Update 3D scene based on new state
   }
   ```

### Coordinate System

Babylon.js uses a **right-handed coordinate system** (Y-up):
- X-axis: left/right (matches board X)
- Y-axis: forward/back (matches board Y)
- Z-axis: up/down (height)

Board position (x, y) maps to 3D position (x, y, z) where z is height.

### Testing

**Manual testing:**
```bash
# Terminal 1: Start server
uv run race-unified-server --debug

# Terminal 2: Open browser
firefox http://localhost:8080

# Terminal 3: Connect desktop client
uv run race-to-the-crystal
# Join the same game
```

**Browser console:**
- Check for WebSocket connection errors
- Monitor game state updates
- Debug rendering issues

## Deployment

### Production Configuration

For production deployment, update the WebSocket URL in `game_client.websocket.js`:

```javascript
// Development
const ws = new WebSocket('ws://localhost:8080/ws');

// Production
const ws = new WebSocket(`wss://${window.location.host}/ws`);
```

### Server Configuration

The unified server supports custom ports:

```bash
# Custom HTTP port
uv run race-unified-server --http-port 3000

# Custom TCP port
uv run race-unified-server --port 9999 --http-port 8080
```

### Reverse Proxy (Nginx)

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Troubleshooting

**WebSocket connection fails:**
- Check server is running with `--unified` flag
- Verify firewall allows port 8080
- Check browser console for errors

**3D scene doesn't render:**
- Ensure browser supports WebGL
- Check Babylon.js loads correctly
- Review browser console for errors

**Game state out of sync:**
- Check WebSocket connection status in HUD
- Server is authoritative - refresh page to resync
- Check server logs with `--debug` flag

**Actions not working:**
- Verify it's your turn (check HUD)
- Ensure token is selected
- Check browser console for validation errors

## Future Enhancements

Potential improvements:

1. **Enhanced Visuals**: Particle effects, better animations, health bars
2. **Spectator Mode**: Watch games without playing
3. **Mobile Support**: Touch controls and responsive design
4. **Replay System**: Record and playback games

## Related Documentation

- [Network Protocol](NETWORK.md) - Message types and protocol details
- [Game Rules](GAME.md) - Game mechanics and rules
- [Server Architecture](../server/README.md) - Server implementation details
