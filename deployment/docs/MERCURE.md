# Mercure Integration

This document explains Mercure configuration for deployed Race to the Crystal servers.

## Overview

**Mercure** is a protocol for pushing real-time updates to web browsers using Server-Sent Events (SSE). It provides an alternative to WebSockets with better firewall/proxy compatibility and built-in auto-reconnection.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Caddy Server (race-caddy)                      │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  Embedded Mercure Hub                      │ │
│  │  - Receives publish requests from API      │ │
│  │  - Broadcasts SSE to connected clients     │ │
│  │  - Endpoint: /.well-known/mercure          │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  Reverse Proxy                             │ │
│  │  - Proxies HTTP requests to game API       │ │
│  │  - Serves static files                     │ │
│  └────────────────────────────────────────────┘ │
└───────────────┬──────────────────────────────▲──┘
                │                              │
        Proxy   │                              │ Publish
                │                              │
                ▼                              │
┌──────────────────────────────────┐          │
│  Game API (race-game-api)        │          │
│                                   │          │
│  ┌─────────────────────────────┐ │          │
│  │  Mercure Publisher          │ ├──────────┘
│  │  - Publishes game updates   │ │
│  │  - Uses JWT authentication  │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘

┌─────────────────┐
│  Web Browser    │
│                 │
│  ┌──────────┐   │      HTTP/REST
│  │Babylon.js│◄──┼────────────► Caddy ─────► Game API
│  │  Client  │   │
│  └────┬─────┘   │
│       │         │      Mercure SSE
│  ┌────▼─────┐   │  ◄───────────────────── Caddy
│  │ Mercure  │   │                         (hub)
│  │EventSource│  │
│  └──────────┘   │
└─────────────────┘
```

## Configuration

### JWT Secrets

Mercure requires two JWT secrets:

- **Publisher JWT**: Allows game server to publish updates
- **Subscriber JWT**: Allows web clients to subscribe (set to anonymous for public access)

**Generate secrets:**

```bash
PUBLISHER_JWT=$(openssl rand -base64 32)
SUBSCRIBER_JWT=$(openssl rand -base64 32)
```

### Environment Variables

**Game API** (`game-api.container`):

```ini
# Internal hub URL (container-to-container)
Environment=MERCURE_HUB_URL=http://race-caddy/.well-known/mercure

# Public hub URL (client-facing)
Environment=MERCURE_PUBLIC_URL=https://your-domain.com/.well-known/mercure

# Topic prefix for game updates
Environment=MERCURE_TOPIC_PREFIX=https://your-domain.com/game

# Publisher JWT (from secrets file)
EnvironmentFile=/path/to/race-secrets.env
```

**Caddy** (`caddy.container`):

```ini
# JWT secrets (from secrets file)
EnvironmentFile=/path/to/race-secrets.env
```

### Caddyfile Configuration

**Development:**

```caddyfile
{
    order mercure before respond
}

http://:80 {
    # Embedded Mercure Hub
    mercure {
        publisher_jwt {env.MERCURE_PUBLISHER_JWT}
        subscriber_jwt {env.MERCURE_SUBSCRIBER_JWT}
        anonymous  # Allow unauthenticated subscriptions
        cors_origins *
    }

    # Proxy to game API
    reverse_proxy race-game-api:8080
}
```

**Production:**

```caddyfile
{
    order mercure before respond
}

your-domain.com {
    # Caddy automatically provisions Let's Encrypt HTTPS

    # Embedded Mercure Hub
    mercure {
        publisher_jwt {env.MERCURE_PUBLISHER_JWT}
        subscriber_jwt {env.MERCURE_SUBSCRIBER_JWT}
        anonymous  # Public game, no auth required
        cors_origins https://your-domain.com  # Restrict to domain
    }

    # Proxy to game API
    reverse_proxy race-game-api:8080 {
        header_up Host {http.request.header.Host}
        header_up X-Real-IP {http.request.remote.host}
        header_up X-Forwarded-For {http.request.remote.host}
        header_up X-Forwarded-Proto {http.request.proto}
    }
}
```

## How It Works

### Publishing Updates

When a game action occurs, the game server publishes an update:

```python
# server/mercure_publisher.py
async def publish_game_state(game_id: str, state_data: dict):
    topic = f"{MERCURE_TOPIC_PREFIX}/{game_id}"

    response = await client.post(
        MERCURE_HUB_URL,
        data={
            "topic": topic,
            "data": json.dumps(state_data),
        },
        headers={"Authorization": f"Bearer {MERCURE_PUBLISHER_JWT}"},
    )
```

### Subscribing to Updates

Web clients subscribe via EventSource:

```javascript
// web_server/static/mercure_client.js
const url = new URL('https://your-domain.com/.well-known/mercure');
url.searchParams.append('topic', 'https://your-domain.com/game/123');

const eventSource = new EventSource(url);
eventSource.onmessage = (event) => {
    const update = JSON.parse(event.data);
    updateGameState(update.state);
};
```

## Verification

### Check Hub is Running

```bash
# Development
curl http://localhost:8880/.well-known/mercure

# Production
curl https://your-domain.com:8880/.well-known/mercure
```

### Test Publishing

```bash
# From inside game-api container
curl -X POST http://race-caddy/.well-known/mercure \
  -H "Authorization: Bearer $MERCURE_PUBLISHER_JWT" \
  -d "topic=https://your-domain.com/game/test" \
  -d "data=hello"
```

### Monitor Logs

```bash
# Watch for Mercure-related messages
journalctl --user -u caddy.service -f | grep -i mercure
journalctl --user -u game-api.service -f | grep -i mercure
```

### Browser Console

Open browser console and check for:

```
✓ Mercure config loaded
✓ Mercure EventSource connected
✓ Mercure Update Received: {...}
```

## Security

### Production Checklist

- ✅ Use HTTPS for Mercure endpoint
- ✅ Strong random JWT secrets (32+ bytes)
- ✅ Secrets stored in environment file (not inline)
- ✅ File permissions on secrets (600)
- ✅ CORS restricted to production domain
- ✅ Publisher JWT kept secret (never sent to client)
- ✅ Subscriber JWT can be public (anonymous mode)

### JWT Token Rotation

If secrets are compromised:

```bash
# Generate new secrets
NEW_PUBLISHER_JWT=$(openssl rand -base64 32)
NEW_SUBSCRIBER_JWT=$(openssl rand -base64 32)

# Update secrets file
cat > ~/.config/containers/systemd/race-secrets.env <<EOF
MERCURE_PUBLISHER_JWT=$NEW_PUBLISHER_JWT
MERCURE_SUBSCRIBER_JWT=$NEW_SUBSCRIBER_JWT
EOF

# Restart both services (must use matching secrets)
systemctl --user restart game-api.service caddy.service
```

## Troubleshooting

### Mercure Not Connecting

**Check hub availability:**

```bash
curl -I https://your-domain.com:8880/.well-known/mercure
# Should return: 200 OK
```

**Check CORS headers:**

```bash
curl -I https://your-domain.com:8880/.well-known/mercure \
  -H "Origin: https://your-domain.com"
# Should include: Access-Control-Allow-Origin
```

**Check browser console:**
- Look for CORS errors
- Verify EventSource connection established
- Check for 401 Unauthorized (JWT issue)

### Publishing Fails

**Verify JWT secret:**

```bash
# Check secret is set
echo $MERCURE_PUBLISHER_JWT

# Verify it matches Caddy's configuration
cat ~/.config/containers/systemd/race-secrets.env
```

**Check game API can reach hub:**

```bash
# From inside container
podman exec race-game-api curl http://race-caddy/.well-known/mercure
```

### Connection Drops

Mercure has built-in auto-reconnect. If connections frequently drop:

- Check network stability
- Review Caddy resource limits
- Check for timeout configurations
- Monitor Caddy logs for errors

## Benefits vs WebSocket

| Feature | Mercure (SSE) | WebSocket |
|---------|---------------|-----------|
| Browser Support | Universal | Good |
| Auto-Reconnect | Built-in | Manual |
| HTTP/2 Multiplexing | Yes | No |
| Firewall/Proxy | Very compatible | Sometimes blocked |
| Setup Complexity | Low | Medium |
| Server Resources | Lower | Higher |

## Fallback Strategy

The web client implements automatic fallback:

1. **Try Mercure first**: Attempts to connect to Mercure hub
2. **Fall back to WebSocket**: If Mercure unavailable, uses WebSocket
3. **Graceful degradation**: Both provide real-time updates

To force WebSocket mode (disable Mercure):

```bash
# In game-api.container, remove or comment out:
# Environment=MERCURE_HUB_URL=...
# Environment=MERCURE_PUBLIC_URL=...
```

## Performance

**Mercure is optimized for:**
- Many clients subscribing to same topic
- Broadcast-heavy workloads (game state updates)
- HTTP/2 connection reuse

**Connection limits:**
- Development: ~100 concurrent connections (sufficient for testing)
- Production: Scales with Caddy resource limits

**Monitor connections:**

```bash
# Check active connections
podman stats race-caddy
```

## References

- [Mercure Protocol](https://mercure.rocks/)
- [Caddy Mercure Module](https://caddyserver.com/docs/modules/mercure)
- [Server-Sent Events (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Deployment Guide](DEPLOYMENT.md) - Main deployment documentation
