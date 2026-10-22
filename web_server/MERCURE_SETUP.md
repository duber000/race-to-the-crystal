# Mercure Integration

> **Status: not a working state path.** The publisher is never called, and
> the client no longer uses SSE for state. The WebSocket carries the game
> state and the event stream. This document describes what Mercure *would*
> need before it could be used again.

**Mercure documentation has moved to:**

**[deployment/docs/MERCURE.md](../deployment/docs/MERCURE.md)**

## Quick Reference

Mercure is a protocol for real-time updates using Server-Sent Events (SSE). It's integrated into the unified server via the embedded Caddy Mercure hub.

### Key Points

- **Embedded Hub**: Mercure runs inside Caddy (no separate service needed)
- **Configuration**: See `deployment/production/Caddyfile` or `deployment/development/caddy.container`
- **JWT Secrets**: Required for publishing (game server) and subscribing (web clients)

### What works today

- `server/mercure_publisher.kuki` can publish to a topic, and
  `web_server/static/mercure_client.js` can subscribe to one.
- The browser client can subscribe to the event feed with **`?sse=1`** on the
  page URL. Fine-grained events (token moves, combat) are passed through.

### What does not work, and why

1. **Nothing is published.** `MercurePublisher.Publish*` is never called, so
   a subscribed topic is silent. The AI client's `sse` subcommand now falls
   back to polling for this reason.
2. **A topic cannot carry the state.** The publisher's topics are per
   *game* (`{prefix}/{gameId}`), but the game state is now per *player*:
   every client receives a different, fog-filtered view. Publishing one
   state per game would hand every subscriber the wrong perspective.
   Per-player topics (`{prefix}/{gameId}/{playerId}`) and per-player
   subscriber JWTs would be needed first.
3. **The client ignores state over SSE.** Even with a publisher, a state
   frame arriving over SSE is discarded: the WebSocket is the state path.

### If you want to wire it up

- Publish per player, to `{prefix}/{gameId}/{playerId}`, with the same
  `VisibleStateDict` the WebSocket path uses.
- Authorise each subscriber for its own topic (the current publisher JWT
  grants `["*"]` — far too broad).
- Only then flip the client back to reading state from SSE; the opt-in flag
  and the "ignore SSE state" branch in `network_manager.js` are the two
  places to change.

### Documentation

- **[deployment/docs/MERCURE.md](../deployment/docs/MERCURE.md)** - Complete Mercure documentation
- **[deployment/docs/DEPLOYMENT.md](../deployment/docs/DEPLOYMENT.md)** - Deployment guide
