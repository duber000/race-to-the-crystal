# Mercure Integration Guide

This document explains how to use Mercure with the Race to the Crystal web server for real-time updates.

## Overview

**Mercure** is a protocol for pushing data updates to web browsers using Server-Sent Events (SSE). It enables real-time game state updates without the overhead of WebSockets.

## Architecture

```
┌─────────────────┐
│  Web Browser    │
│                 │
│  ┌──────────┐   │      HTTP/REST         ┌──────────────────┐
│  │Babylon.js│◄──┼────────────────────────┤  FastAPI Server  │
│  │  Client  │   │                        │                  │
│  └────┬─────┘   │                        │  ┌─────────────┐ │
│       │         │      Mercure SSE       │  │   Mercure   │ │
│       │         │  ◄─────────────────────┼──│  Publisher  │ │
│  ┌────▼─────┐   │                        │  └─────────────┘ │
│  │ Mercure  │   │                        └──────────────────┘
│  │EventSource│  │                                 │
│  └──────────┘   │                                 │ Publish
│                 │                                 ▼
└─────────────────┘                        ┌──────────────────┐
                                           │   Mercure Hub    │
                                           │  (External or    │
                                           │   Embedded)      │
                                           └──────────────────┘
```

## Installation

### 1. Install Dependencies

The required dependencies are already in `pyproject.toml`:

```bash
uv sync
```

This installs:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - HTTP client for Mercure publishing
- `pyjwt` - JWT token generation (optional, for Mercure security)

### 2. Set Up Mercure Hub

You have two options for running a Mercure hub:

#### Option A: Use Official Mercure Hub (Recommended)

Download and run the official Mercure hub:

```bash
# Download Mercure (Linux)
wget https://github.com/dunglas/mercure/releases/download/v0.15.8/mercure_0.15.8_Linux_x86_64.tar.gz
tar -xzf mercure_0.15.8_Linux_x86_64.tar.gz

# Run Mercure hub
MERCURE_PUBLISHER_JWT_KEY='!ChangeThisMercureHubJWTSecretKey!' \
MERCURE_SUBSCRIBER_JWT_KEY='!ChangeThisMercureHubJWTSecretKey!' \
./mercure run --config Caddyfile.dev
```

The hub will run on `http://localhost:3000` by default.

#### Option B: Use Mercure.rocks (Testing Only)

For testing, you can use the public Mercure hub at `https://mercure.rocks/.well-known/mercure`.

**⚠️ Warning:** Do not use this in production! It's public and not secure.

### 3. Configure Environment Variables

Create a `.env` file in the `web_server/` directory:

```bash
# Mercure Configuration
MERCURE_HUB_URL=http://localhost:3000/.well-known/mercure
MERCURE_PUBLISHER_JWT=your-publisher-jwt-token
MERCURE_TOPIC_PREFIX=https://api.game.com/game

# Optional: Disable Mercure if you want to use WebSocket only
# MERCURE_PUBLISHER_JWT=
```

### 4. Generate Publisher JWT

If using the official Mercure hub, generate a publisher JWT:

```python
import jwt
import datetime

secret = "!ChangeThisMercureHubJWTSecretKey!"  # Same as MERCURE_PUBLISHER_JWT_KEY

payload = {
    "mercure": {
        "publish": ["*"],  # Allow publishing to all topics
    },
    "exp": datetime.datetime.utcnow() + datetime.timedelta(days=365)
}

token = jwt.encode(payload, secret, algorithm="HS256")
print(f"MERCURE_PUBLISHER_JWT={token}")
```

Add this token to your `.env` file.

## Running the Server

### Start the Web Server

```bash
# From the project root
uv run python -m web_server.main

# Or if you have the entry point configured
uv run race-web-server
```

The server will start on `http://localhost:8000`.

### Test the Integration

1. **Open the game in your browser:**
   ```
   http://localhost:8000/
   ```

2. **Test Mercure connection:**

   Open browser console and check for:
   ```
   ✓ Mercure config loaded: {...}
   ✓ Mercure EventSource connected
   ```

3. **Test real-time updates:**

   Make a move in the game. You should see:
   ```
   ✓ Mercure Update Received: {type: "state_update", last_action: "move", ...}
   ```

## Using the Mercure Client

### Basic Usage

The `mercure_client.js` provides a simple interface:

```javascript
// Initialize Mercure client
const mercure = new MercureClient();
const ready = await mercure.init();

if (ready) {
    // Subscribe to real-time updates
    mercure.subscribe((update) => {
        console.log('Game state updated:', update.state);

        // Update your game rendering
        updateGameState(update.state);

        // Handle action notifications
        if (update.last_action === 'move') {
            playSound('move');
        }
    });
} else {
    // Fall back to WebSocket
    connectWebSocket();
}
```

### Integration with Existing Client

To integrate with the existing Babylon.js client in `game_client.js`:

1. **Load the Mercure client script:**
   ```html
   <script src="/static/mercure_client.js"></script>
   <script src="/static/game_client.js"></script>
   ```

2. **Add Mercure init to GameClient:**
   ```javascript
   class GameClient {
       async init() {
           // Try Mercure first
           this.mercure = new MercureClient();
           const mercureReady = await this.mercure.init();

           if (mercureReady) {
               this.mercure.subscribe((update) => {
                   this.handleStateUpdate(update.state);
               });
           } else {
               // Fall back to WebSocket
               this.connectWebSocket();
           }
       }
   }
   ```

## How It Works

### Mercure Real-Time Updates

1. **Game action occurs:**
   - Player makes a move via REST API: `POST /api/game/action`

2. **Server processes action:**
   - FastAPI executes the game action
   - Updates game state

3. **Server publishes to Mercure:**
   ```python
   await mercure.publish_game_state(
       game_id,
       {"type": "state_update", "last_action": "move", "state": game_state}
   )
   ```

4. **Mercure hub broadcasts:**
   - All connected clients receive the update via EventSource

5. **Client updates UI:**
   - JavaScript processes the update
   - Babylon.js re-renders the game state

## Benefits

### Mercure vs WebSocket

| Feature | Mercure (SSE) | WebSocket |
|---------|---------------|-----------|
| Browser Support | Universal | Good |
| Auto-Reconnect | Built-in | Manual |
| HTTP/2 Multiplexing | Yes | No |
| Firewall/Proxy Friendly | Yes | Sometimes blocked |
| Fallback | Easy | Complex |
| Server Resources | Lower | Higher |

## Troubleshooting

### Mercure Not Connecting

1. **Check if Mercure hub is running:**
   ```bash
   curl http://localhost:3000/.well-known/mercure
   ```

2. **Verify JWT token:**
   ```bash
   echo $MERCURE_PUBLISHER_JWT
   ```

3. **Check browser console for errors:**
   - CORS issues: Make sure Mercure hub allows your origin
   - Network errors: Check firewall/proxy settings

### Falling Back to WebSocket

If Mercure is not available, the client automatically falls back to WebSocket. To force WebSocket mode, set:

```bash
MERCURE_PUBLISHER_JWT=
```

## Production Deployment

For production, consider:

1. **Use HTTPS for Mercure hub**
2. **Set up proper JWT authentication**
3. **Configure CORS properly**
4. **Set up monitoring for Mercure connection health**
5. **Use Redis for multi-instance Mercure coordination**

## Further Reading

- [Mercure Protocol](https://mercure.rocks/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Server-Sent Events (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

## License

Same as the main project.
