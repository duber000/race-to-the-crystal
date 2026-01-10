# Mercure Integration

**Mercure documentation has moved to:**

**[deployment/docs/MERCURE.md](../deployment/docs/MERCURE.md)**

## Quick Reference

Mercure is a protocol for real-time updates using Server-Sent Events (SSE). It's integrated into the unified server via the embedded Caddy Mercure hub.

### Key Points

- **Embedded Hub**: Mercure runs inside Caddy (no separate service needed)
- **Configuration**: See `deployment/production/Caddyfile` or `deployment/development/caddy.container`
- **JWT Secrets**: Required for publishing (game server) and subscribing (web clients)
- **Fallback**: Web client automatically falls back to WebSocket if Mercure unavailable

### Documentation

- **[deployment/docs/MERCURE.md](../deployment/docs/MERCURE.md)** - Complete Mercure documentation
- **[deployment/docs/DEPLOYMENT.md](../deployment/docs/DEPLOYMENT.md)** - Deployment guide

### Quick Start

Mercure is automatically configured when you deploy using the unified server:

```bash
# Development
uv run race-unified-server

# Production (with quadlets)
# See deployment/docs/DEPLOYMENT.md
```

No additional setup required - Mercure works out of the box!
