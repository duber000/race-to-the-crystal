# Network Game Integration TODO

## Goal: Enable 3D Web Client to Join Network Games

Currently the 3D web client (FastAPI + Babylon.js) runs on port 8000 and creates isolated local games, while the network game server runs on port 8888 with TCP connections for desktop clients.

## Option 3: Unified Server (Full Integration) ⭐ SELECTED

Merge both servers to support both web clients and desktop clients from a single unified game server.

### Benefits
- ✅ Single source of truth for game state
- ✅ Web and desktop clients can play together
- ✅ Consistent protocol and state management
- ✅ Eliminates duplication between servers
- ✅ Easier to maintain long-term

### Architecture

```
Unified Game Server (port 8888)
├── TCP Handler (existing)
│   └── Desktop Arcade clients (asyncio protocol)
├── WebSocket Handler (NEW)
│   └── Web browser clients (Babylon.js)
└── HTTP Handler (NEW)
    └── Serve static files (HTML/JS/CSS)
```

### Implementation Tasks

#### Phase 1: Add WebSocket Support to Game Server
- [ ] Add WebSocket endpoint to `server/game_server.py`
- [ ] Create `server/websocket_handler.py` for web client connections
- [ ] Handle WebSocket authentication and player registration
- [ ] Broadcast game state updates to WebSocket clients
- [ ] Parse WebSocket messages for game actions

#### Phase 2: Add HTTP/Static File Serving
- [ ] Add HTTP server capability (using `aiohttp` or embed FastAPI)
- [ ] Serve static files from `web_server/static/` and `web_server/templates/`
- [ ] Add `/` route to serve `index.html`
- [ ] Add `/static/` route for JavaScript/CSS files

#### Phase 3: Unify Protocol
- [ ] Create common message format for both TCP and WebSocket
- [ ] Update `shared/enums.py` with `ClientType.WEB_BROWSER`
- [ ] Ensure game state serialization works for both client types
- [ ] Handle player ID mapping (web clients use string IDs like "player_0")

#### Phase 4: Update Web Client
- [ ] Change WebSocket connection from `ws://localhost:8000` to `ws://localhost:8888`
- [ ] Implement lobby join/create UI in web client
- [ ] Add player name input and connection UI
- [ ] Handle network game lifecycle (lobby → game → end)

#### Phase 5: Update Lobby System
- [ ] Extend `server/lobby.py` to track client types (TCP vs WebSocket)
- [ ] Allow mixed lobbies (desktop + web clients)
- [ ] Update lobby state broadcasts for both protocols
- [ ] Handle ready/unready from web clients

#### Phase 6: Testing & Integration
- [ ] Test mixed games (desktop + web clients)
- [ ] Verify state synchronization across all clients
- [ ] Test reconnection handling for web clients
- [ ] Performance testing with multiple connections
- [ ] Update documentation with unified server usage

#### Phase 7: Migration & Cleanup
- [ ] Deprecate standalone FastAPI server (`web_server/main.py`)
- [ ] Update `pyproject.toml` scripts
  - `race-server` → unified server
  - Remove `race-web-server` (or alias to `race-server`)
- [ ] Update `CLAUDE.md` and `web_server/README.md`
- [ ] Migration guide for existing deployments

### Technical Decisions

#### Framework Choice
**Option A:** Add FastAPI to game server
- Pros: Modern, async-native, good WebSocket support
- Cons: Another dependency, heavier than needed

**Option B:** Use `aiohttp` for HTTP/WebSocket
- Pros: Lightweight, already async, integrates well with asyncio
- Cons: Less modern API than FastAPI

**Option C:** Manual WebSocket with `websockets` library
- Pros: Minimal dependencies, we already use it
- Cons: No built-in HTTP serving for static files

**RECOMMENDED:** Option B (`aiohttp`) - best balance of features and integration.

#### Message Protocol
Use JSON for both TCP and WebSocket (already done for TCP):
```json
{
  "type": "game_action",
  "action": {
    "type": "move",
    "token_id": 5,
    "destination": [12, 12]
  },
  "player_id": "player_0"
}
```

#### State Synchronization
- Game server maintains single `GameState`
- Broadcasts to ALL clients (TCP + WebSocket) on state changes
- No client-specific state (read-only for all)

### Dependencies to Add
```toml
dependencies = [
    "aiohttp>=3.9.0",        # For HTTP and WebSocket
    "aiohttp-cors>=0.7.0",   # For CORS if needed
]
```

### Files to Modify
- `server/game_server.py` - Add WebSocket/HTTP handlers
- `server/lobby.py` - Support ClientType.WEB_BROWSER
- `server/game_coordinator.py` - Broadcast to mixed client types
- `web_server/static/game_client.js` - Connect to port 8888
- `pyproject.toml` - Add aiohttp dependency

### Files to Create
- `server/websocket_handler.py` - WebSocket connection handler
- `server/http_handler.py` - Static file serving
- `server/static/` - Symlink to `web_server/static/`
- `server/templates/` - Symlink to `web_server/templates/`

### Backward Compatibility
- Desktop clients continue to work unchanged (TCP on port 8888)
- Existing lobby/game logic remains compatible
- Web client gets new connection UI for network games

### Future Enhancements
- [ ] Multiple game sessions on one server
- [ ] Spectator mode for web clients
- [ ] In-game chat via WebSocket
- [ ] Replays/game history
- [ ] Matchmaking system

---

## Alternative Options (Not Selected)

### Option 1: Direct TCP Connection from JavaScript
Web client connects directly to port 8888 using WebSocket-to-TCP proxy.
- **Rejected:** Requires full protocol implementation in JS, no HTTP serving

### Option 2: FastAPI Bridge
Keep FastAPI server, make it proxy to game server.
- **Rejected:** Adds unnecessary hop and complexity

---

## Notes
- Start with Phase 1 (WebSocket support) as proof of concept
- Can incrementally migrate features from `web_server/main.py`
- Keep backward compatibility throughout migration
