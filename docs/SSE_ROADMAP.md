# Race to the Crystal - Architecture Roadmap

## Overview

This document outlines the planned architecture refactoring to transition from a dual-channel (WebSocket + Mercure) system to an SSE-primary architecture where Server-Sent Events (Mercure) handles all state updates and WebSocket is reserved for commands.

---

## Motivation

### Current Architecture Issues

The current system sends game state updates via **both** WebSocket and Mercure (SSE) simultaneously:

```
Game Action Occurs
    ↓
Server broadcasts via WebSocket ──────┐
Server publishes via Mercure/SSE ─────┤──> All Clients
                                       └──> Redundant Traffic
```

**Problems:**
- ✗ Double network bandwidth usage (~100% overhead)
- ✗ Duplicate processing on client side
- ✗ Unnecessary architectural complexity
- ✗ Mercure benefits underutilized

### Why SSE-Primary?

**Benefits of Server-Sent Events (Mercure):**

1. **Better Scalability**
   - Broadcast-optimized: Server publishes once → Caddy/Mercure broadcasts to N clients
   - Stateless game server (can restart without dropping SSE connections)
   - Horizontal scaling: Multiple game servers → Single Mercure hub

2. **Superior Network Compatibility**
   - SSE is standard HTTP (works through all proxies/firewalls)
   - WebSocket often blocked by corporate firewalls
   - Better mobile browser support

3. **Built-in Reliability**
   - Native browser auto-reconnection with Last-Event-ID
   - No missed updates during brief disconnections
   - HTTP/2 multiplexing (multiple SSE connections share one TCP connection)

4. **Future-Ready Architecture**
   - Enables spectator mode (read-only SSE subscriptions)
   - Game replay/recording (record SSE stream)
   - RESTful API pattern (GET for state, POST for commands)
   - Third-party integrations (bots, stats sites)

> **✅ UPDATE (2026-01-11):** A proof-of-concept **HTTP POST + SSE architecture** has been implemented for AI clients. This demonstrates the viability of the RESTful API pattern and provides a working example of SSE + commands architecture. See the "HTTP POST + SSE Implementation" section at the end of this document for details.

---

## Target Architecture

### Message Flow

```
┌─────────────┐                                    ┌─────────────┐
│   Client    │                                    │   Server    │
│  (Browser)  │                                    │             │
└──────┬──────┘                                    └──────┬──────┘
       │                                                  │
       │  Commands (MOVE, ATTACK, DEPLOY, etc.)          │
       │────────────────WebSocket────────────────────────>│
       │                                                  │
       │  State Updates (FULL_STATE, game events)        │
       │<───────────────Mercure/SSE──────────────────────│
       │                                                  │
       │  Fallback Mode (if SSE fails)                   │
       │<───────────────WebSocket────────────────────────│
       │                                                  │
```

### Message Routing

**SSE Messages (11 types):**
- `FULL_STATE` - Complete game state synchronization
- `STATE_UPDATE` - Incremental state updates (future)
- `TURN_CHANGE` - Turn phase transitions
- `TOKEN_MOVED` - Token movement events (for animations)
- `COMBAT_RESULT` - Combat resolution events
- `GENERATOR_UPDATE` - Generator capture status changes
- `CRYSTAL_UPDATE` - Crystal occupation changes
- `MYSTERY_EVENT` - Mystery square events
- `TOKEN_DEPLOYED` - Token deployment events
- `GAME_WON` - Victory notification

**WebSocket Messages (Commands + Control):**
- **Game Commands:** `MOVE`, `ATTACK`, `DEPLOY`, `END_TURN`
- **Lobby Operations:** `CREATE_GAME`, `JOIN_GAME`, `START_GAME`, `READY`, `LIST_GAMES`, `LEAVE_GAME`
- **Connection Management:** `CONNECT`, `RECONNECT`, `DISCONNECT`, `HEARTBEAT`
- **Responses:** All `_ACK` messages, `ERROR`, `INVALID_ACTION`, `GAME_LIST`
- **Lobby Events (Phase 1):** `PLAYER_JOINED`, `PLAYER_LEFT`, `PLAYER_DISCONNECTED`, `PLAYER_RECONNECTED`

> **Alternative (Implemented for AI clients):** Commands can also be sent via **HTTP POST** with JWT authentication instead of WebSocket. This stateless approach is currently used by HTTP AI clients (`POST /api/game/{game_id}/action`).

---

## Implementation Phases

### Phase 1: Server-Side Foundation (Weeks 1-2)

**Goal:** Add infrastructure for SSE-primary mode with feature flag control.

**Tasks:**
1. Add `SSE_PRIMARY_MODE` environment variable to `server/game_server.py`
2. Add message classification constants to `network/messages.py`
3. Refactor `_broadcast_game_state()` to split SSE and WebSocket paths
4. Add individual event publishing to `server/mercure_publisher.py`
5. Track client metadata (type, version) in `server/game_coordinator.py`

**Key Files:**
- `server/game_server.py` (lines 44-83, 775-809)
- `server/mercure_publisher.py` (lines 91-173)
- `server/game_coordinator.py`
- `network/messages.py` (after line 62)

**Feature Flag Behavior:**
- `SSE_PRIMARY_MODE=false` (default): Both channels active (current behavior)
- `SSE_PRIMARY_MODE=true`: SSE for web clients, WebSocket for desktop only

### Phase 2: Web Client Updates (Weeks 2-3)

**Goal:** Update web client to use SSE as primary channel with WebSocket fallback.

**Tasks:**
1. Enhance `mercure_client.js` with event routing and exponential backoff reconnection
2. Update `game_client.websocket.js` to conditionally handle FULL_STATE
3. Add SSE failure detection (30-second timeout triggers WebSocket fallback)
4. Implement event-based animations in `game_client.js`
5. Expand `/api/config` endpoint to include SSE mode information

**Key Files:**
- `web_server/static/mercure_client.js` (lines 50-98)
- `web_server/static/game_client.websocket.js` (lines 257-259, 278-314)
- `web_server/static/game_client.js`
- `server/http_handler.py` (lines 106-126)

**Client Behavior:**
- Attempt SSE connection on game start
- Log "✓ Using SSE for state updates" on success
- Log "⚠ Using WebSocket for state updates (fallback)" on failure
- Automatic fallback if SSE silent for 30 seconds

### Phase 3: Testing & Validation (Weeks 3-4)

**Goal:** Comprehensive testing to ensure no regressions or message loss.

#### 3.1 Unit Tests
**New file:** `tests/test_sse_primary_mode.py`

Test cases:
- Feature flag controls broadcast routing
- Web clients receive via SSE in primary mode
- Desktop clients always receive via WebSocket
- Mercure publish failure triggers fallback
- Client type detection from CONNECT message

#### 3.2 Integration Tests
**File:** `tests/test_network_multiplayer_integration.py`

Test cases:
- Mixed client games (web SSE + desktop WebSocket)
- SSE reconnection and state resynchronization
- Individual game events delivered correctly
- High-frequency action handling

#### 3.3 Manual Testing Checklist
- [ ] Dual-channel mode (`SSE_PRIMARY_MODE=false`)
- [ ] SSE-primary mode (`SSE_PRIMARY_MODE=true`)
- [ ] Desktop client compatibility in both modes
- [ ] SSE failure → WebSocket fallback
- [ ] Player reconnection with SSE
- [ ] Event-driven animations
- [ ] High-frequency action spam test
- [ ] Multiple concurrent games

### Phase 4: Deployment & Monitoring (Weeks 4-5)

**Goal:** Gradual rollout with monitoring and rollback capability.

#### Week 1: Staging Environment
- Deploy with `SSE_PRIMARY_MODE=false` (dual-channel)
- Verify Mercure publishes correctly
- Establish baseline metrics

#### Week 2: SSE-Primary Testing
- Enable `SSE_PRIMARY_MODE=true`
- Monitor for 48 hours:
  - Message delivery success rate (target: >99%)
  - SSE connection success rate (target: >95%)
  - WebSocket fallback rate (target: <5%)
  - State desynchronization reports (target: 0)

#### Week 3: Production Rollout
- Deploy to production with `SSE_PRIMARY_MODE=true`
- Monitor for 1 week
- Document as default if stable

#### Rollback Plan
**Triggers:**
- Mercure hub downtime >5 minutes
- Message delivery failure >2%
- User-reported state desync >3 incidents
- SSE connection failure >10%

**Procedure:**
1. Set `SSE_PRIMARY_MODE=false` (environment variable only)
2. Restart game server
3. All clients automatically revert to dual-channel mode
4. Investigate issues in staging environment

---

## Phase 5: Future Enhancements

### 5.1 Desktop Client SSE Migration
**Timeline:** Post-Phase 4 (optional)

- Add SSE support to `client/network_client.py`
- Use Python `sseclient-py` library for EventSource
- Unified architecture across all client types

**Benefits:**
- Consistent state update mechanism
- Better network compatibility for desktop users
- Enables headless spectator/recording mode

### 5.2 Lobby Events via SSE
**Timeline:** Post-Phase 4

- Subscribe to lobby topic immediately on CONNECT
- Move `PLAYER_JOINED`, `PLAYER_LEFT` events to SSE
- Enable lobby spectators (view lobby without joining)

### 5.3 Performance Optimization
**Timeline:** Post-Phase 4

- **Delta Updates:** Implement `STATE_UPDATE` with incremental changes instead of full state
- **Event Batching:** Batch rapid events into single messages
- **SSE Compression:** Enable gzip compression for SSE streams
- **CDN Integration:** Deploy Mercure hub at edge for lower latency

---

## Configuration

### Environment Variables

**Server (`game-api.container`):**
```bash
# SSE Primary Mode (feature flag)
SSE_PRIMARY_MODE=false  # Set to 'true' to enable SSE-primary mode

# Mercure Configuration
MERCURE_HUB_URL=http://race-caddy/.well-known/mercure
MERCURE_PUBLIC_URL=https://your-domain.com:8880/.well-known/mercure
MERCURE_TOPIC_PREFIX=https://your-domain.com/game

# JWT Secrets (in race-secrets.env)
MERCURE_PUBLISHER_JWT=<secret>
MERCURE_SUBSCRIBER_JWT=<secret>
```

**Caddy (`caddy.container`):**
```caddyfile
{
    order mercure before respond
}

your-domain.com:8880 {
    mercure {
        publisher_jwt {env.MERCURE_PUBLISHER_JWT}
        subscriber_jwt {env.MERCURE_SUBSCRIBER_JWT}
        anonymous
        cors_origins https://your-domain.com:8880
    }

    reverse_proxy race-game-api:8080
}
```

---

## Success Metrics

**Primary Metrics:**
- ✅ Web clients receive FULL_STATE via SSE only (not WebSocket)
- ✅ Desktop clients continue receiving via WebSocket
- ✅ Individual game events enable smooth animations
- ✅ SSE failure triggers automatic WebSocket fallback
- ✅ No message loss or state desync issues

**Performance Targets:**
- WebSocket bandwidth reduced by >50%
- Message delivery success rate >99%
- SSE connection success rate >95%
- WebSocket fallback rate <5%

**Quality Metrics:**
- All existing tests pass
- New SSE-specific tests pass
- Zero critical bugs in production
- No user-reported state desynchronization

---

## Verification Procedures

### End-to-End Testing

**1. SSE-Primary Mode Verification**
```bash
# Set environment variable
export SSE_PRIMARY_MODE=true

# Start server
uv run race-server --unified

# Open browser console at https://your-domain.com:8880/
# Check for: "✓ Using SSE for state updates"
# Verify: No FULL_STATE messages in WebSocket (Network tab)
# Verify: EventSource connection active (Network tab)
```

**2. Event Animation Testing**
- Make a move → verify smooth animation
- Attack a token → verify combat animation
- Capture generator → verify visual update
- Check console for individual event logs

**3. Fallback Testing**
```bash
# Stop Mercure hub
systemctl --user stop caddy

# Verify client logs: "⚠ Using WebSocket for state updates (fallback)"
# Verify game still works
# Restart hub
systemctl --user restart caddy
```

**4. Mixed Client Testing**
```bash
# Start web client (SSE)
# Start desktop client: uv run race-client
# Play game together
# Verify both clients stay synchronized
```

**5. Performance Monitoring**
```bash
# Monitor server logs
journalctl --user -u game-api.service -f | grep -i mercure

# Check WebSocket traffic (should be ~50% lower)
# Verify no "Mercure publish failed" errors
# Check for state desync errors (should be 0)
```

---

## Risk Assessment

### High Risk Areas
1. **Message Loss During Transition**
   - Mitigation: Dual-channel mode during rollout, client-side deduplication
2. **Mercure Hub Availability**
   - Mitigation: Automatic WebSocket fallback, health monitoring, hub redundancy

### Medium Risk Areas
1. **Message Ordering**
   - Mitigation: Timestamps and sequence numbers
2. **Reconnection Race Conditions**
   - Mitigation: Grace period for SSE connection, retry logic

### Low Risk Areas
1. **Browser Compatibility**
   - Impact: Low (automatic WebSocket fallback)
2. **CORS Configuration**
   - Impact: Low (detected early in testing)

---

## Documentation Updates

**Files to Update Post-Implementation:**
- [ ] `README.md` - Update architecture diagram
- [ ] `docs/NETWORK.md` - Update message routing documentation
- [ ] `docs/MERCURE.md` - Update with SSE-primary architecture details
- [ ] `docs/WEB.md` - Update web client SSE usage
- [ ] `docs/DEPLOYMENT.md` - Add SSE_PRIMARY_MODE configuration

---

## References

- [Mercure Protocol Specification](https://mercure.rocks/)
- [Server-Sent Events (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Caddy Mercure Module](https://caddyserver.com/docs/modules/mercure)

---

## HTTP POST + SSE Implementation (Completed - 2026-01-11)

### Overview

As a parallel implementation to the planned SSE-primary architecture, we have implemented a **HTTP POST + SSE architecture specifically for AI clients**. This provides a simpler, stateless alternative to WebSocket for AI agents.

### Architecture

```
┌─────────────┐                                    ┌─────────────┐
│  HTTP AI    │                                    │   Server    │
│   Client    │                                    │             │
└──────┬──────┘                                    └──────┬──────┘
       │                                                  │
       │  Commands (MOVE, ATTACK, DEPLOY, END_TURN)      │
       │────────────────HTTP POST────────────────────────>│
       │    (JWT Bearer token authentication)            │
       │                                                  │
       │  State Updates (FULL_STATE, GAME_WON)           │
       │<───────────────Mercure/SSE──────────────────────│
       │                                                  │
```

### Implemented Components

**Server-Side:**
1. **JWT Authentication** (`server/auth.py`)
   - Token creation/verification with HS256 algorithm
   - 24-hour token expiration
   - Stateless authentication via `Authorization: Bearer {token}` header

2. **REST API Endpoints** (`server/http_handler.py`)
   - `POST /api/game/{game_id}/join` - Join existing game, auto-ready, receive JWT token
   - `POST /api/game/{game_id}/action` - Execute game actions with JWT authentication
   - Full error handling: 400, 401, 403, 404, 410, 422, 500

3. **Client Type** (`network/messages.py`)
   - Added `ClientType.HTTP_AI` enum for tracking HTTP AI clients

**Client-Side:**
4. **HTTP AI Client** (`client/http_ai_client.py`)
   - SSE connection for state updates via Mercure
   - HTTP POST for actions (MOVE, ATTACK, DEPLOY, END_TURN)
   - Three strategies: random, aggressive, defensive
   - CLI tool: `uv run race-http-ai-client --join <game_id>`

**Testing:**
5. **Unit Tests** (`tests/test_http_api.py`)
   - 9 tests for JWT authentication (all passing)
   - Token creation, verification, expiration, header extraction

### Design Decisions

**Why HTTP POST instead of WebSocket for AI?**
- Simpler for AI clients (no connection management)
- Works anywhere HTTP works (serverless functions, simple scripts)
- Easier to test and debug (curl, postman)
- Stateless architecture (no session storage)

**Limitations:**
- HTTP AI clients can only **join** games (not create)
- HTTP AI clients auto-ready immediately on join
- SSE required for state updates (no polling fallback)

### Integration with Existing Architecture

This HTTP POST + SSE implementation **complements** the existing architecture:
- **Desktop clients**: Continue using TCP/WebSocket
- **Web browser clients**: Continue using WebSocket (SSE planned for future)
- **HTTP AI clients**: NEW - Use HTTP POST + SSE

All three client types can play together in the same game. The server broadcasts state via:
1. **WebSocket/TCP** → Desktop and web browser clients
2. **Mercure/SSE** → Web browser clients (if configured) AND HTTP AI clients

### Production Deployment

**Environment Variables:**
```bash
# Required for HTTP AI authentication
JWT_SECRET_KEY="your-secure-random-secret"  # CRITICAL: Change in production!

# Mercure (already configured)
MERCURE_HUB_URL=http://race-caddy/.well-known/mercure
MERCURE_PUBLIC_URL=https://your-domain.com/.well-known/mercure
MERCURE_PUBLISHER_JWT=<secret>
```

**Security Notes:**
- Default JWT secret is `dev-secret-key-CHANGE-IN-PRODUCTION`
- Server logs warning if default secret is used
- Generate secure key: `uv run python -c "from server.auth import generate_secret_key; print(generate_secret_key())"`
- Tokens expire after 24 hours
- HTTPS required in production (JWT in Authorization header)

### Example Usage

```bash
# 1. Start unified server
uv run race-unified-server

# 2. Create game via desktop/web client
# Note the game_id from lobby

# 3. Join via HTTP AI client
uv run race-http-ai-client --join <game_id> --name "Bot" --strategy aggressive

# 4. Start game - HTTP AI plays automatically via HTTP POST actions
```

### Future Enhancements

This HTTP POST + SSE implementation demonstrates the viability of the **RESTful API pattern** mentioned in the original roadmap. Potential extensions:

1. **HTTP API for all clients** (not just AI)
   - Allow human clients to use HTTP POST for actions
   - Enables mobile apps, third-party clients, etc.

2. **Expand REST endpoints**
   - `POST /api/game/create` - Create games via HTTP
   - `GET /api/game/{game_id}/state` - Polling fallback for SSE
   - `POST /api/game/{game_id}/ready` - Manual ready control

3. **Webhook support**
   - Server can POST events to external URLs
   - Enables Discord bots, stat tracking, etc.

4. **GraphQL API**
   - Single endpoint for flexible queries
   - Better for complex client requirements

---

**Last Updated:** 2026-01-11
**Status:**
- **Planning Phase**: SSE-primary architecture for all clients (Phase 1-5)
- **✅ IMPLEMENTED**: HTTP POST + SSE for AI clients (parallel architecture)
