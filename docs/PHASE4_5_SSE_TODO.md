# SSE-Primary Mode: Phase 4-5 TODO

**Status as of 2026-01-13:**
- ✅ Phase 1 (Server-Side Foundation): COMPLETED
- ✅ Phase 2 (Web Client Updates): COMPLETED
- ⏸️ Phase 3 (Testing & Validation): PARTIALLY COMPLETED (unit tests done)
- ⏳ Phase 4 (Deployment & Monitoring): **NEXT UP**
- ⏳ Phase 5 (Future Enhancements): FUTURE

---

## Phase 4: Deployment & Monitoring

### 4.1 Pre-Deployment Testing ⏳

**Goal:** Validate SSE-primary mode works correctly before production deployment

#### Integration Tests
- [ ] Create `tests/test_sse_integration.py` with:
  - Mixed client game (web browser + desktop client)
  - SSE reconnection after network interruption
  - WebSocket fallback when Mercure hub is down
  - High-frequency action spam (rapid moves/attacks)
  - Multiple concurrent games with SSE-primary mode

#### Manual Testing Checklist
- [ ] **Dual-Channel Mode** (`SSE_PRIMARY_MODE=false`):
  - [ ] Start unified server with default settings
  - [ ] Connect 2 web browser clients
  - [ ] Verify both receive updates via WebSocket AND SSE
  - [ ] Check logs show: `[WebSocket] Sending state to...` AND `[Mercure] Successfully published`

- [ ] **SSE-Primary Mode** (`SSE_PRIMARY_MODE=true`):
  - [ ] Start unified server with `export SSE_PRIMARY_MODE=true`
  - [ ] Connect 2 web browser clients
  - [ ] Verify game works normally (moves, attacks, turn changes)
  - [ ] Check browser console shows: `✓ Using SSE for state updates`
  - [ ] Check server logs show: `Skipping FULL_STATE for ... (WEB_BROWSER) - using SSE`
  - [ ] Verify NO `[WebSocket] Sending state to...` for web clients

- [ ] **Mixed Client Compatibility**:
  - [ ] Start unified server with `SSE_PRIMARY_MODE=true`
  - [ ] Connect 1 web browser client + 1 desktop client
  - [ ] Verify web client uses SSE (logs show "Skipping FULL_STATE")
  - [ ] Verify desktop client uses WebSocket (logs show "Sending FULL_STATE")
  - [ ] Both clients stay synchronized throughout game

- [ ] **SSE Failure → WebSocket Fallback**:
  - [ ] Start game with SSE-primary mode
  - [ ] Stop Mercure hub: `systemctl --user stop caddy` (or equivalent)
  - [ ] Verify browser console shows: `⚠ Using WebSocket for state updates (fallback)`
  - [ ] Verify game continues working via WebSocket
  - [ ] Restart Mercure hub
  - [ ] New games should use SSE again

- [ ] **Player Reconnection with SSE**:
  - [ ] Start game with SSE-primary mode
  - [ ] Disconnect one player's browser (close tab)
  - [ ] Reconnect within 5 minutes
  - [ ] Verify SSE reconnects with Last-Event-ID
  - [ ] Verify game state synchronizes correctly

- [ ] **Event-Driven State Updates**:
  - [ ] Open browser DevTools console during gameplay
  - [ ] Make a move
  - [ ] Verify Mercure update received with correct message format
  - [ ] Check update includes `game_state`, `last_action` fields

- [ ] **High-Frequency Actions**:
  - [ ] Rapidly execute 20+ actions in 10 seconds
  - [ ] Verify all updates received correctly
  - [ ] Check for message loss or state desync
  - [ ] Monitor server logs for errors

- [ ] **Multiple Concurrent Games**:
  - [ ] Create 3 games simultaneously
  - [ ] Each game has 2 web browser clients
  - [ ] Verify each game receives correct isolated state
  - [ ] Check no cross-game state leakage
  - [ ] Monitor Mercure publish success rate

#### Performance Baseline Metrics
Collect metrics with `SSE_PRIMARY_MODE=false` (dual-channel) for comparison:

- [ ] **Network Traffic**:
  - [ ] Measure WebSocket message count over 5-minute game
  - [ ] Measure total bytes sent via WebSocket
  - [ ] Record baseline for comparison

- [ ] **Server Resources**:
  - [ ] CPU usage during 3 concurrent games
  - [ ] Memory usage during 3 concurrent games
  - [ ] Network bandwidth usage

- [ ] **Client Resources**:
  - [ ] Browser memory usage during 5-minute game
  - [ ] Number of EventSource reconnections
  - [ ] WebSocket reconnections

### 4.2 Staging Environment Deployment ⏳

**Week 1: Dual-Channel Validation**

- [ ] Deploy code to staging with `SSE_PRIMARY_MODE=false`
- [ ] Configure Mercure hub (Caddy) with proper JWT secrets
- [ ] Set environment variables:
  ```bash
  SSE_PRIMARY_MODE=false
  MERCURE_HUB_URL=http://race-caddy/.well-known/mercure
  MERCURE_PUBLIC_URL=https://staging.example.com/.well-known/mercure
  MERCURE_TOPIC_PREFIX=https://staging.example.com/game
  MERCURE_PUBLISHER_JWT=<staging-secret>
  MERCURE_SUBSCRIBER_JWT=<staging-secret>
  ```
- [ ] Verify Mercure publishes correctly (check logs)
- [ ] Run full manual testing checklist
- [ ] Establish baseline metrics (traffic, CPU, memory)
- [ ] Document any issues found

**Week 2: SSE-Primary Testing**

- [ ] Enable SSE-primary mode: `export SSE_PRIMARY_MODE=true`
- [ ] Restart unified server
- [ ] Monitor for 48 hours continuously
- [ ] Collect and compare metrics:

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Message delivery success rate | >99% | ___ | ⏳ |
| SSE connection success rate | >95% | ___ | ⏳ |
| WebSocket fallback rate | <5% | ___ | ⏳ |
| State desynchronization reports | 0 | ___ | ⏳ |
| WebSocket bandwidth reduction | ~50% | ___ | ⏳ |
| CPU usage change | ±10% | ___ | ⏳ |
| Memory usage change | ±10% | ___ | ⏳ |

- [ ] Review server logs for errors:
  ```bash
  journalctl --user -u game-api.service --since "2 days ago" | grep -i "error\|warning\|mercure"
  ```
- [ ] Check for Mercure publish failures
- [ ] Verify no state desync reports from users
- [ ] Document findings and recommendations

### 4.3 Production Rollout ⏳

**Week 3: Production Deployment**

- [ ] Deploy to production with `SSE_PRIMARY_MODE=true`
- [ ] Configure production Mercure hub with strong secrets
- [ ] Set production environment variables
- [ ] Enable monitoring dashboards
- [ ] Monitor for 1 week continuously

**Monitoring Checklist:**
- [ ] Set up alerts for:
  - [ ] Mercure hub downtime >5 minutes
  - [ ] Message delivery failure >2%
  - [ ] SSE connection failure >10%
  - [ ] State desync reports >3 incidents
  - [ ] CPU usage increase >25%
  - [ ] Memory leak detection

- [ ] Daily monitoring tasks:
  - [ ] Check error logs for Mercure failures
  - [ ] Review WebSocket fallback rate
  - [ ] Verify SSE connection success rate
  - [ ] Check for user-reported issues
  - [ ] Monitor server resource usage

**Week 4: Stability Validation**

- [ ] Collect 7-day metrics summary
- [ ] Compare against targets
- [ ] Document as production-ready if stable
- [ ] Update README.md with SSE-primary mode as default
- [ ] Close Phase 4

### 4.4 Rollback Plan ⏳

**Triggers for Rollback:**
- ❌ Mercure hub downtime >5 minutes
- ❌ Message delivery failure >2%
- ❌ User-reported state desync >3 incidents
- ❌ SSE connection failure >10%
- ❌ Critical bug in SSE path

**Rollback Procedure:**
1. [ ] Set `SSE_PRIMARY_MODE=false` in environment
2. [ ] Restart game server: `systemctl --user restart game-api.service`
3. [ ] Verify clients automatically revert to dual-channel mode
4. [ ] Monitor for 30 minutes to ensure stability
5. [ ] Investigate issues in staging environment
6. [ ] Document root cause and fixes needed
7. [ ] Plan re-deployment timeline

**Testing Rollback:**
- [ ] Practice rollback in staging
- [ ] Time the rollback procedure
- [ ] Verify no data loss during rollback
- [ ] Document rollback time: ___ minutes

---

## Phase 5: Future Enhancements

### 5.1 Desktop Client SSE Migration (Optional) ⏳

**Timeline:** Post-Phase 4

**Goal:** Migrate desktop clients to use SSE for state updates instead of TCP

**Benefits:**
- Consistent state update mechanism across all client types
- Better network compatibility (SSE works through more firewalls than TCP)
- Enables headless spectator/recording mode
- Simplified server architecture (no separate TCP and WebSocket paths)

**Tasks:**
- [ ] Add SSE support to `client/network_client.py`
- [ ] Use Python `sseclient-py` library for EventSource
- [ ] Create `client/sse_client.py` module
- [ ] Keep TCP for commands, use SSE for state updates
- [ ] Update client CLI to support `--use-sse` flag
- [ ] Test desktop client with SSE + TCP commands
- [ ] Document migration guide for users

**Implementation Sketch:**
```python
# client/sse_client.py
import sseclient
import requests

class SSEStateReceiver:
    def __init__(self, mercure_url: str, game_id: str):
        self.mercure_url = mercure_url
        self.game_id = game_id
        self.on_state_update = None

    def subscribe(self):
        url = f"{self.mercure_url}?topic={self.game_id}"
        response = requests.get(url, stream=True)
        client = sseclient.SSEClient(response)

        for event in client.events():
            if self.on_state_update:
                self.on_state_update(json.loads(event.data))
```

### 5.2 Lobby Events via SSE ⏳

**Timeline:** Post-Phase 4

**Goal:** Move lobby events (PLAYER_JOINED, PLAYER_LEFT) to SSE channel

**Benefits:**
- Lobby spectators (view lobby without joining)
- Reduced WebSocket traffic for lobby operations
- Real-time lobby updates for all viewers

**Tasks:**
- [ ] Subscribe to lobby topic immediately on CONNECT
- [ ] Move `PLAYER_JOINED`, `PLAYER_LEFT` to SSE messages
- [ ] Add lobby SSE topic: `{topic_prefix}/lobby/{lobby_id}`
- [ ] Update message classification in `network/messages.py`
- [ ] Create lobby spectator mode (read-only SSE subscription)
- [ ] Test lobby events via SSE
- [ ] Document lobby SSE API

**Message Flow:**
```
Client connects → Subscribe to /lobby/{lobby_id} via SSE
Player joins → Server publishes PLAYER_JOINED to SSE
Client receives update → Updates lobby UI
```

### 5.3 Delta State Updates (STATE_UPDATE) ⏳

**Timeline:** Post-Phase 4, when bandwidth optimization needed

**Goal:** Send incremental state changes instead of full state on every update

**Benefits:**
- Reduced bandwidth (send only changed fields)
- Faster updates (smaller payloads)
- Better mobile experience

**Tasks:**
- [ ] Design delta format (JSON Patch or custom format)
- [ ] Implement `GameState.get_delta_from(previous_state)` method
- [ ] Add `MessageType.STATE_UPDATE` handling
- [ ] Update Mercure publisher to support delta updates
- [ ] Add client-side delta application logic
- [ ] Add fallback to FULL_STATE if delta fails
- [ ] Test delta updates don't cause state desync
- [ ] Measure bandwidth savings

**Delta Format Example:**
```json
{
  "type": "STATE_UPDATE",
  "sequence": 42,
  "delta": {
    "tokens": {
      "5": {"position": [12, 13], "health": 6}
    },
    "turn_phase": "ACTION"
  }
}
```

### 5.4 Event Batching ⏳

**Timeline:** When handling high-frequency actions

**Goal:** Batch rapid events into single messages to reduce overhead

**Tasks:**
- [ ] Implement event queue with 50ms batching window
- [ ] Group events by game_id
- [ ] Publish batched events as single SSE message
- [ ] Add `BATCH_UPDATE` message type
- [ ] Test batching doesn't cause perceived lag
- [ ] Document batching behavior

**Batched Message Example:**
```json
{
  "type": "BATCH_UPDATE",
  "events": [
    {"type": "TOKEN_MOVED", "token_id": 5, ...},
    {"type": "COMBAT_RESULT", "attacker_id": 5, ...},
    {"type": "TOKEN_MOVED", "token_id": 7, ...}
  ]
}
```

### 5.5 SSE Compression ⏳

**Timeline:** When bandwidth is a concern

**Goal:** Enable gzip compression for SSE streams

**Tasks:**
- [ ] Configure Mercure hub to enable compression
- [ ] Add `Accept-Encoding: gzip` to SSE requests
- [ ] Test compression works with EventSource
- [ ] Measure bandwidth savings
- [ ] Document compression setup in deployment guide

**Caddy Configuration:**
```caddyfile
encode gzip {
    match {
        path /.well-known/mercure
    }
}
```

### 5.6 Event-Based Animations ⏳

**Timeline:** Post-Phase 4

**Goal:** Use individual SSE events to trigger smooth animations

**Current:** Full state updates, client diffs to determine what changed
**Future:** Individual events trigger specific animations

**Tasks:**
- [ ] Update `game_client.js` to register event handlers:
  ```javascript
  mercureClient.on('TOKEN_MOVED', (event) => {
      animateTokenMovement(event.token_id, event.from, event.to);
  });

  mercureClient.on('COMBAT_RESULT', (event) => {
      playCombatAnimation(event.attacker_id, event.defender_id);
  });
  ```
- [ ] Create animation functions in `game_client.js`
- [ ] Use Babylon.js animations for smooth transitions
- [ ] Test animations don't block game state updates
- [ ] Add animation queue for rapid events

### 5.7 CDN Integration ⏳

**Timeline:** When serving global audience

**Goal:** Deploy Mercure hub at edge for lower latency

**Tasks:**
- [ ] Research CDN with SSE support (Cloudflare, Fastly)
- [ ] Deploy Mercure hub at multiple edge locations
- [ ] Configure DNS for edge routing
- [ ] Test latency improvements
- [ ] Document CDN setup

### 5.8 GraphQL API ⏳

**Timeline:** If complex client requirements emerge

**Goal:** Provide flexible query API for game state

**Tasks:**
- [ ] Design GraphQL schema for game state
- [ ] Implement GraphQL server (Python graphene)
- [ ] Add GraphQL subscriptions for real-time updates
- [ ] Create example queries
- [ ] Document GraphQL API

**Example Query:**
```graphql
query GameState($gameId: ID!) {
  game(id: $gameId) {
    turnNumber
    currentPlayer {
      name
      tokens {
        position
        health
      }
    }
    board {
      generators {
        position
        owner
      }
    }
  }
}
```

---

## Success Criteria Summary

### Phase 4 Exit Criteria:
- ✅ All manual tests pass in staging and production
- ✅ 7 days of stable operation in production
- ✅ All metrics meet targets (>99% delivery, >95% SSE success)
- ✅ Zero critical bugs reported
- ✅ Documentation updated and complete
- ✅ Rollback plan tested and documented

### Phase 5 Completion Criteria:
- ✅ Desktop client SSE migration (if pursued)
- ✅ Lobby events via SSE implemented
- ✅ Delta updates reduce bandwidth by >30%
- ✅ Event-based animations working smoothly
- ✅ At least 2 future enhancements implemented and tested

---

## Progress Tracking

Update this section as you complete tasks:

**Last Updated:** 2026-01-13

**Current Focus:** Phase 4.1 - Pre-Deployment Testing

**Blockers:** None

**Next Steps:**
1. Complete manual testing checklist with SSE_PRIMARY_MODE=true
2. Create integration tests in `tests/test_sse_integration.py`
3. Collect performance baseline metrics
4. Deploy to staging for 48-hour monitoring

**Notes:**
- WebSocket handler fix applied 2026-01-13 (commit b8013fd)
- Ready for comprehensive testing
