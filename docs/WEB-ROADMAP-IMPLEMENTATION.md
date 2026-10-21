---
type: Implementation Plan
title: Battle Drones-Inspired Roadmap — Implementation Plan for Race to the Crystal
description: Concrete, sequenced plan for implementing BATTLEDRONE-INSPIRED-ROADPLAN.md against the real codebase, including a blocking Phase 0 baseline repair and unconditional fog-of-war.
tags: [roadmap, web, babylonjs, websocket, mcp, replay, touch, fog-of-war]
generated: { by: opencode/minimax-m3.1-flash, at: 2026-10-21T00:00:00-04:00 }
verified:
stale_after: 2026-12-21T00:00:00Z
status: draft
decisions:
  - D1: full Phase 0 baseline repair (Mercure/SSE kept, client made WS-primary)
  - D2: server-side EVENT stream (no client-side diffing)
  - D3: acoustic P2P modem is a stretch goal after Phase 4
  - D4: fog-of-war applies to everyone, unconditionally
sources:
  - id: roadmap
    resource: BATTLEDRONE-INSPIRED-ROADPLAN.md
    title: Battle Drones-Inspired Roadmap
---

# Battle Drones-Inspired Roadmap — Implementation Plan

This document turns [`BATTLEDRONE-INSPIRED-ROADPLAN.md`](../BATTLEDRONE-INSPIRED-ROADPLAN.md) into an
executable plan grounded in the *actual* state of this repository.

**Headline finding:** the roadmap assumes a working 3D web client that receives a live game-event
stream. Neither is true today. The web client's input pipeline is inert, the HUD never updates, and
the server emits only whole-state snapshots — so there is no signal for screen shake, camera
choreography, combat text, replays, or an agent seat to hang off. **A Phase 0 baseline repair is a
hard prerequisite**, and the plan below leads with it.

---

## 1. Roadmap audit — what holds, what doesn't

| Roadmap item | Verdict | Correction needed |
|---|---|---|
| §1.1 Dynamic camera choreography | **Sound**, blocked | Needs an event stream to know *when* a generator is overloaded or a crystal is extracted. Blocked on Phase 0.4. |
| §1.2 Screen shake, particles, floating combat text | **Sound**, blocked | `renderer.animations.js` already has `animateCombat` / `triggerExplosion` hooks, but nothing calls them — the server never emits `COMBAT_RESULT`. |
| §1.3 Audio punch + ducking | **Sound**, needs groundwork | `audio_manager.js` has **no master bus** — every gain node connects straight to `destination`. Ducking is impossible until a master bus exists. |
| §1.4 Tactical telegraphing | **Sound**, self-contained | Pure client-side rendering over state the client already receives. Cheapest high-value win. |
| §2.1 Agent seat (MCP/HTTP/WS) | **Sound**, wrong file targets | Roadmap names `game/api.kuki` and `learn/learn_api.kuki`. The seat belongs in `server/`; `game/` only supplies the *observation* payload. `ClientType.HTTP_AI` already exists in `server/lobby.kuki` but is unused. Fog-of-war is required for the seat — and per **D4** it now applies to everyone, so it moves into Phase 0 (§0.11). |
| §2.2 Radio chatter + agent HUD | **Sound**, blocked | Needs a `RADIO_CHAT` message type and a spectator channel. |
| §2.3 Replay scrubber | **Sound**, wrong file target | Roadmap names `state_manager.js`. The client only ever receives the *latest* state; the server computes no deltas and keeps no history. **The log must be built server-side**; `state_manager.js` is only the playback surface. |
| §3.1 Acoustic P2P modem | **High risk** | See §7.1 — real hardware constraints. Recommend a calibration-gated design at 15–17 kHz with an audible fallback, and an explicit stretch goal. |
| §3.2 Stateless relay | **Sound**, but needs a WASM spike | The `game` package has **zero external dependencies** and is pure logic → it is a clean `GOOS=js GOARCH=wasm` target. That is the real enabler, and it is worth an explicit spike. |
| §3.3–3.4 Mobile touch | **Partially done already** | `game_client.device.js` detects touch, `index.css` has responsive breakpoints, and `#mobile-action-bar` exists. The genuine gaps are the **radial palette**, hitbox sizing, and gesture arbitration. Do not "implement mobile-first" — implement the *missing 20%*. |
| §4 Success metrics | Partially measurable | M1/M4 are fine. M2/M3/M5 need the Phase 0 groundwork before they can even be *defined* pass/fail. |

---

## 2. Current-state findings (the blockers)

Everything below is verified against the working tree at commit `e0dfc97`.

### 2.1 The client's input pipeline is inert — no gameplay is possible

`web_server/static/game_client.js:42` sets `this.inputController = null` and **nothing ever
assigns it**. `InputController` is imported in `game_client.modules.js` but never instantiated.

Consequences:
- `UIController.setupInputHandlers()` (`game_client.modules.js:1089`) is guarded by
  `if (this.gameClient.inputController)` → **never subscribes**. No `click`, no `hover`, no `keydown`
  handler is ever registered. Tokens cannot be selected, moved, or attacked from the browser.
- `GameClient.handleKeyDown` (`game_client.js:89`) short-circuits on a null controller.
- `index.page.js:65` (`window.gameClient.inputController?.resetToOverview()`) is a no-op.
- `GameClient.handleStateChanged` → `this.inputController?.refreshFPIndicators()` is a permanent no-op.

### 2.2 The HUD writes to DOM ids that do not exist

`ui_manager.js#updateHUD` writes `#player-name`, `#player-tokens`, `#player-health`, `#turn-player`,
`#turn-phase`, `#crystal-status`. **None of these exist** in `web_server/templates/index.html`.

The template *does* contain `#turnNumber`, `#gamePhase`, `#turnPhase`, `#currentPlayer`,
`#playersList`, and `#crystal-effects-indicator` — but the only code that writes them lives in
`web_server/static/game_client.ui.js`, which is **dead code**: no `export`, no importer, not
referenced by `index.html`. It is a superseded 690-line duplicate of `ui_manager.js`.

Net effect: the visible HUD never updates at runtime, and the crystal-effects panel is never
populated.

### 2.3 `game_client.crystal_effects.js` reads undefined globals

It is a classic script that never imports the constants module, but it reads `CELL_SIZE`,
`CRYSTAL_FOG_SPREAD_SPEED`, `CRYSTAL_GHOST_COUNT`, `CRYSTAL_EFFECT_ANIMATION_DURATION`,
`CRYSTAL_WHIRLWIND_COUNT`, `CRYSTAL_LIGHTNING_FLASH_DURATION`. All are `undefined` → crystal-effect
animations throw on start.

### 2.4 The server emits no fine-grained events

The client already subscribes to nine fine-grained events (`game_client.modules.js:90-124`):
`token_moved`, `combat_result`, `token_deployed`, `generator_update`, `crystal_update`,
`mystery_event`, `turn_change`, `game_won`, `invalid_action`.

**The server emits none of them.** `server/ws_endpoint.kuki` broadcasts only `FULL_STATE`,
`GAME_WON`, `ERROR`, `INVALID_ACTION` and lobby messages. `MercurePublisher.PublishTurnChange` exists
but is never called. `Renderer3D.animateCombat`, `animateTokenMove`, `animateGeneratorUpdate`,
`animateCrystalUpdate`, `animateMysteryEvent` are therefore **dead code paths**.

This is the single most important structural gap: every "juice" feature in Phase 1 is a
*reaction to an event*, and there are no events.

### 2.5 There is no history anywhere — replay has no substrate

- `GameSession.lastState` is declared and never written.
- `StateManager` keeps exactly one `gameState` object.
- The server computes no deltas; `mergeDelta` in `state_manager.js` is a client-side utility with no
  producer.

### 2.6 There is no fog of war

`ClientStateDict(perspective)` (`game/state_serializer.kuki`) returns the **entire** board, tokens,
generators, crystal and enemy positions to every player. The `perspective` argument only appends
`perspective_player_id` / `your_player_id`. `CrystalEffectsManager.hasFogOfWar` is never consulted.

Roadmap §2.1 explicitly requires fog-of-war-compliant payloads for agent seats.

> **Decision: fog-of-war applies to everyone, unconditionally** (not agent-only). This makes it a
> *core game rule*, not an agent feature — which moves it into Phase 0 (§0.11) and has a real
> blast radius: the base serializer, the renderer, the in-process AI, and the `learn/` teaching
> layer. See §3.3 for the full spec and §3.3.1 for the deliberate boundary around `learn/`.

### 2.7 The WebSocket and HTTP state paths are inconsistent

| Path | Payload | Includes board? | Client expects |
|---|---|---|---|
| WS `FULL_STATE` | `ClientStateDict(gamePid)` | Yes | ✅ |
| WS `STATE_UPDATE` (broadcast from `handleGameAction`) | `ClientStateDict(gamePid)` | Yes | ✅ |
| HTTP `GET /api/game/{id}/state` | `GameState.ToDict()` (slim) | **No** | n/a |
| HTTP `POST /api/game/{id}/action` → broadcast | `GameState.ToDict()` (slim), under key `"state"` | **No** | ❌ client reads `data.data \|\| data` |

### 2.8 HTTP-joined players never receive pushed state

`HTTPHandler.HandleJoinGame` calls `wsHandler.UpdateClientPlayerID(playerId, playerId, playerName)`
with a **fresh random** `playerId` that is not a live `WSClient` (its `conn` is empty).
`BroadcastToGame` skips clients with no `conn` → HTTP/SSE clients must poll. This blocks the
"AI seat over HTTP" design until fixed.

### 2.9 Supporting gaps

| Gap | Location | Impact |
|---|---|---|
| `color_index` is non-deterministic (Go map iteration order) | `game/state_serializer.kuki` | Player colors shuffle between broadcasts. Visible bug. |
| No session mutex | `server/game_coordinator.kuki` | Two concurrent actions can interleave on one `GameState`. |
| WS is unauthenticated and unrate-limited | `server/ws_endpoint.kuki`, `server/rate_limiter.kuki` | `MAX_MESSAGE_SIZE` declared, never enforced via `SetReadLimit`. `CheckOrigin` always `true`. Rate limiter only wired into the HTTP path. |
| No turn timer / auto-pass | `shared/constants` defines `TURN_TIMEOUT_SECONDS = 30`; nothing reads it | A stalled agent seat blocks the game forever. **Required for Phase 2.** |
| No master audio bus | `web_server/static/audio_manager.js` | §1.3 ducking impossible. |
| `Renderer3D.updateGeneratorHums()` never called | `renderer.base.js:417` | Generator hums never play. |
| `renderer.animations.js` pulses meshes named `"crystal"` / `"crystal_glow_1..6"` | crystal mesh is now `"nlo_hub"` | Dead animation block. |
| `shared/errs` is entirely unused by the server | `shared/errs/errors.kuki` | Error codes are ad-hoc (`"MISSING_FIELD"` vs `"missing_field"`). A new agent-facing API needs consistent codes. |
| `server/ai_spawner.kuki` is dead | never instantiated; spawns `uv run race-ai-client` | The real AI lives in `client/ai/`. |

### 2.10 The client compared the turn phase against the wrong type

The server serialises `"turn_phase": "MOVEMENT"` (the enum *name*, a string —
`game/state_serializer.kuki` interpolates the enum). The client's
`GAME_PHASE` constants were **numbers** (`MOVEMENT: 1`).

Every phase-gated behaviour therefore never fired: `turnPhase === TurnPhase.MOVEMENT`
was never true, so the client never showed move indicators during movement,
never allowed attacks during action, and the deploy menu was gated shut. The
server's ordinals are also offset (`TurnPhase.MOVEMENT = 0` in
`shared/enums/enums.kuki`), so a numeric mapping would have been wrong too.

**Fix:** the constants are now the wire strings, with the mapping documented
at the definition site.

### 2.11 Board decoration was pickable, so clicks resolved to the wrong cell

`createBoard()` left `gridVertical` and `gridCage` pickable, and the crystal's
`inner_frame` / generator pillars / health labels were pickable too. A click on
an empty cell resolved to the **cage wireframe**, landing one cell off
(clicking grid `(12,12)` picked `(13,13)`). Moves to empty cells were therefore
rejected as illegal destinations, and the hover indicator tracked the wrong
cell. Clicking a *token* happened to work because the token mesh is closer to
the camera.

**Fix:** all decoration is `isPickable = false`, and `InputHandler` picks
through a predicate that only accepts `boardGround` and token meshes.

### 2.12 The WebSocket action path rejected every numeric field

`server/action_validation.kuki` checked `data["token_id"] is int`. JSON numbers
decode to **float64**, so that check was never true for a decoded message —
every `MOVE`, `ATTACK` and `DEPLOY` from the browser was refused with
`token_id must be an integer`. The HTTP path was unaffected because
`http_handler.kuki#getIntField` uses `cast.ToInt`, which handles float64. That
is why the AI client worked and the browser did not.

**Fix:** `isIntegerValue` accepts any numeric kind whose value is a whole
number.

### 2.13 `handleStateChanged` recursed infinitely when it was not your turn

`handleStateChanged` → `stateManager.clearSelection()` → `_notifyStateChange()`
→ `handleStateChanged` → … The client threw
`RangeError: Maximum call stack size exceeded` on every state update where the
current turn belonged to the other player — i.e. most of the time.

**Fix:** a re-entrancy guard on the façade, and `clearSelection()` only
notifies when something was actually selected.

### 2.14 Lobby seats, colours and names were unstable

`GameLobby.players` is a Go map, and three places iterated it directly:
`initializePlayers` (seat assignment), `reassignColors` (colour assignment) and
`getPlayerList` (the waiting-room roster order). The result: a player's seat
and colour **shuffled between games**, and the lobby's display names were
dropped entirely — every player was called "Player 1".."Player 4" in the match.

**Fix:** `GameLobby.orderedPlayers()` sorts by the join-order colour index;
seats and colours derive from it, and the lobby name is carried into the match
via `Player.SetName`.

### 2.15 `make test` ran stale test artifacts

`kukicha build` skips `*_test.kuki`, so the `*_test.go` files that `go test`
compiles were whatever was last transpiled by `kukicha brew`. Editing a
`*_test.kuki` file changed nothing until someone remembered to brew. Worse,
`kukicha build` and `kukicha brew` fight over the same output file: build
stamps a `// Generated by Kukicha` header and refuses to overwrite a file
without it, while brew writes the file without one.

**Fix:** `make test` runs `kukicha brew ./...` (which transpiles the test
sources), and `make build` runs `make clean-generated` first so the two never
block each other.

---

## 3. Target architecture

The keystone is a **server-side game-event stream**. One log serves live FX, the replay scrubber,
spectator mode, and the agent comms feed — and it is the only way to make the roadmap's Phase 1
and Phase 2 features implementable at all.

```
                    ┌──────────────────────────────────────────────┐
   action  ────────▶│ server/ws_endpoint.kuki  handleGameAction   │
   (WS | HTTP)      │   └─▶ game.ExecuteAction ─▶ ActionResult     │
                    │        └─▶ GameEvent log (append)           │
                    │             ├─▶ broadcast EVENT frames      │
                    │             ├─▶ per-player state snapshot   │
                    │             └─▶ BattleLog (JSON)             │
                    └──────────────────────────────────────────────┘
                                          │ EVENT frames
                                          ▼
                    ┌──────────────────────────────────────────────┐
                    │ client event bus (network_manager.js)        │
                    │   ├─▶ renderer.fx.js      (shake/particles/FCT)│
                    │   ├─▶ camera_controller  (focus choreography) │
                    │   ├─▶ audio_manager      (impacts/ducking)    │
                    │   ├─▶ ui_manager         (HUD, comms)         │
                    │   └─▶ replay_controller  (scrubber)           │
                    └──────────────────────────────────────────────┘
```

### 3.1 New: `game/game_events.kuki` — the event vocabulary

A single variant enum, serialized once, consumed by every surface.

```kukicha
petiole game

import "shared/types"

enum GameEvent
    TokenMoved
        TokenID: types.TokenID
        OldPosition: list of int
        NewPosition: list of int
    CombatResolved
        AttackerID: types.TokenID
        DefenderID: types.TokenID
        Damage: int
        DefenderKilled: bool
    TokenDeployed
        TokenID: types.TokenID
        HealthValue: int
        Position: list of int
    GeneratorChanged
        GeneratorID: int
        Position: list of int
        IsDisabled: bool
        HoldingPlayerID: string
        TurnsHeld: int
    CrystalChanged
        Position: list of int
        HoldingPlayerID: string
        ControllingPlayerID: string
        TurnsHeld: int
        IsContested: bool
    MysteryTriggered
        TokenID: types.TokenID
        Position: list of int
        Effect: string
    TurnChanged
        TurnNumber: int
        CurrentPlayerID: types.PlayerID
        TurnPhase: string
    RadioChatter
        PlayerID: types.PlayerID
        PlayerName: string
        Text: string
    GameEnded
        WinnerID: types.PlayerID
        WinnerName: string
```

Plus `game/game_events.kuki`:

```kukicha
func EventTypeName on e: GameEvent() string
func EventToDict on e: GameEvent() map of string to any
```

`EventToDict` produces a flat, stable JSON frame:

```json
{"type":"COMBAT_RESOLVED","attacker_id":5,"defender_id":9,"damage":5,"defender_killed":true}
```

### 3.2 New wire message: `EVENT`

Added to `server/ws_endpoint.kuki` alongside `FULL_STATE`:

```json
{"type":"EVENT","game_id":"abc","seq":42,"event":{"type":"COMBAT_RESOLVED","attacker_id":5,"defender_id":9,"damage":5,"defender_killed":true}}
```

`seq` is a monotonically increasing per-session counter. It gives the client:
- ordering guarantees (replacing the ad-hoc `stateUpdateLock` / `stateUpdateQueue` in
  `network_manager.js`),
- gap detection (a missed `seq` ⇒ request a `FULL_STATE` resync),
- replay seeking.

The server still sends a `FULL_STATE` after each action (authoritative), but the `EVENT` frames are
what drive FX, camera and audio. This keeps the protocol robust: if an event is missed, the state
still converges; if an event arrives, the juice fires.

### 3.3 New: `game/visible_state.kuki` — fog of war (unconditional)

**Decision: every network client sees only what its own tokens can see.** This is a core game rule
change, so it lands in Phase 0 (§0.11), not Phase 2.

```kukicha
const VISIBILITY_RADIUS = 3

func VisibleStateDict on gs: reference GameState(viewer: types.PlayerID) StateDict
```

Returns the same shape as `ClientStateDict` but with visibility rules applied:

| Element | Rule |
|---|---|
| Terrain (walls, generator/mystery/crystal **positions**) | Always visible — it is static and acts as a landmark frame. |
| Own tokens | Always visible, full detail. |
| Enemy tokens **within** `VISIBILITY_RADIUS` of any own token | Visible: position, health, owner. |
| Enemy tokens **outside** that radius | Masked: `is_visible: false`, `position: null`, `health: null`, `owner_player_id` retained (you can tell *that* something is out there if it is on a tile you own — optional refinement, see below). |
| Enemy tokens on a cell the viewer owns | Revealed ("you see the enemy standing on your generator") — a common and forgiving rule. |
| Generator `is_disabled` | Always visible — it is a physical fact about the map. |
| Generator `holding_player_id` / `turns_held` | Visible only if the generator is within the viewer's radius, or the holder is the viewer. |
| Crystal position | Always visible (it is the objective). |
| Crystal `holding_player_id` / `controlling_player_id` / `turns_held` | Visible only within the viewer's radius, or when the viewer is the holder. |
| `last_triggered_mystery_event` | Masked if the event position is outside the radius. |
| Board cell `occupants` | Masked consistently with the token rules (an occupant array must not leak a masked token's position). |

**Radius asymmetry:** the viewer's *own* tokens define the radius, so a player who spreads tokens
out sees more. That is the strategic texture fog-of-war should create.

**Where it must be applied — every path that leaves the server:**

| Path | Current | Required |
|---|---|---|
| WS `FULL_STATE` | `ClientStateDict(gamePid)` — already per-player ✅ | `VisibleStateDict(gamePid)` |
| WS `EVENT` frames | n/a (new) | Each event payload must be filtered for the receiving player. An `EVENT` frame describing an enemy move is a leak. |
| HTTP `GET /state` | `ToDict()` (slim, shared) | `VisibleStateDict(playerId)` |
| HTTP `POST /action` → broadcast | `ToDict()` (shared) | per-player `VisibleStateDict` |
| Agent `/observe` | n/a | `VisibleStateDict(agentPlayerId)` |

**Event filtering** is the subtle one. `CombatResolved` names both `attacker_id` and `defender_id`.
If the viewer cannot see the defender, the frame must be rewritten to `{"type":"COMBAT_RESOLVED",
"defender_id":null,"damage":null,"attacker_id":5}` — or dropped entirely if the viewer can see
neither combatant. Design rule: **an event is delivered to a player only if at least one participant
is visible to them**, and any participant they cannot see is nulled out.

**Renderer support.** `renderer.tokens.js#updateTokens` currently draws every token in
`gameState.tokens`. Masked tokens must be skipped, and the renderer must tolerate `position: null`
(do not compute a world position from it). Add a `.is_visible !== false` guard and a null-position
guard. This also lets the renderer draw a "last known position" ghost for a token that was seen and
then lost — a nice touch, but optional.

**Interaction with the crystal effect.** `game/crystal_effects.kuki` has an (unapplied) `FOG_OF_WAR`
crystal effect. With unconditional fog in place, that effect should be redefined as a
**radius modifier** (e.g. halves the viewer's `VISIBILITY_RADIUS` for N turns) rather than an
independent masking mechanism. Do not leave two overlapping fog systems. Implementing the effect is
optional; defining its semantics is not.

### 3.3.1 Boundary: the `learn/` layer stays omniscient

Fog-of-war applies to **network clients only** — the browser, the AI client, and agent seats.

The `learn/` layer (`learn/learn_api.kuki`, `learn/simulation.kuki`, `learn/examples/`) is an
**explicit teaching and inspection tool**: its `Observe()` and `Board()` methods show the full
board, and several tutorials depend on it (`08-reading-the-game`, `10-strategy-ladder` reason about
enemy positions and attack targets). Masking enemies there would make the lessons incoherent —
`api.Actions()` is computed from true state, so the learner would see "attack token 9" with no
token 9 on the board.

**Decision: `learn/` keeps full visibility.** Document this boundary in `learn/learn_api.kuki` and
`docs/LEARN_TO_PROGRAM_WITH_MINECRAFT.md`.

The same boundary applies to the **in-process AI** used by `learn/simulation.kuki` as the opponent:
it plays with perfect information. That is acceptable for lessons. But it must be noted that
`client/ai/http_ai_client.kuki` (the networked AI) **will** be fogged, so the two AI clients play
to different information regimes. When the in-process AI is promoted to a networked seat (Phase 2),
it must go through the same `VisibleStateDict` filter to stay fair.

### 3.4 New: battle log format `.rttc-battle.json`

```json
{
  "format": "rttc-battle",
  "version": 1,
  "game_id": "abc",
  "created_at": "2026-10-21T12:00:00Z",
  "players": [{"id":"player_0","name":"Gemini","color_index":0,"is_agent":true}],
  "final_state": { "...": "compact final snapshot" },
  "snapshots": [
    { "turn": 0, "phase": "PLAYING", "turn_phase": "MOVEMENT",
      "current_turn_player_id": "player_0",
      "tokens": {"0":{"player_id":"player_0","health":10,"max_health":10,"position":[0,0],"is_alive":true,"is_deployed":true}},
      "generators": [{"id":1,"position":[5,5],"is_disabled":false,"holding_player_id":"","turns_held":0}],
      "crystal": {"position":[12,12],"holding_player_id":"","controlling_player_id":"","turns_held":0},
      "players": [{"id":"player_0","name":"Gemini","is_active":true,"token_ids":[0,1,2]}]
    }
  ],
  "events": [
    { "seq": 1, "turn": 0, "kind": "TURN_CHANGED", "data": { "turn_number": 1, "current_player_id": "player_0" } }
  ],
  "radio": [ { "seq": 7, "turn": 2, "player_id": "player_1", "player_name": "Claude", "text": "Holding the east generator." } ]
}
```

Snapshot cadence: **one per turn**, not per action. The board grid (24×24 static terrain) is stored
once in `final_state`/`snapshots[0]` and reused; per-turn snapshots carry only the mutable layer
(tokens, generators, crystal, players, turn metadata). That keeps a 200-turn match in the low
megabytes.

---

## 4. Phase 0 — Baseline repair (**blocking, must land first**)

Estimated: 3–5 days. Nothing in Phases 1–4 is verifiable until this is done.

### 4.0 Status

| Item | State | Notes |
|---|---|---|
| 0.1 Instantiate the input controller | **Done** | Also fixed the mobile Deploy button, which called a façade method that does not exist. |
| 0.2 Reconcile the HUD with the template | **Done** | Rewrote `updateHUD` against the real ids; ported the crystal-effects panel out of the dead file; deleted `game_client.ui.js`; added a crystal-status line and the click-to-copy game ID. |
| 0.3 Fix the crystal-effects module | **Done** | Converted to an ES module importing the constants; deleted the duplicate local `CrystalEffect` map. |
| 0.4 Server-side event stream | *Not started* | The keystone. |
| 0.5 Unify the HTTP and WS state paths | *Not started* | |
| 0.6 Fix the phantom-client bug | *Not started* | |
| 0.7 Deterministic seats and colours | **Done** | Extended beyond `color_index` to seat assignment and player names (§2.14). |
| 0.8 Harden the WebSocket path | *Not started* | |
| 0.9 Turn timeout / auto-pass | *Not started* | Timeout policy decided: **30 s for humans, 120 s for agents**. |
| 0.10 Cleanup | **Partially done** | Deleted the dead UI file; fixed the favicon and the deprecated meta tag. Mercure is still to be made explicitly WS-primary. |
| 0.11 Unconditional fog-of-war | *Not started* | |

**Additional defects found and fixed while validating 0.1–0.3** (these were not in
the original plan; they are recorded in §2.10–§2.15):

- Turn-phase type mismatch between the client and the wire format (§2.10).
- Board decoration was pickable, so clicks resolved to the wrong cell (§2.11).
- The WebSocket action path rejected every numeric field (§2.12).
- `handleStateChanged` recursed infinitely on every non-your-turn update (§2.13).
- Lobby seats, colours and names were unstable (§2.14).
- `make test` ran stale test artifacts (§2.15).

**Verified end-to-end in a real browser** (Chromium via DevTools, against a live
server): connect → create lobby → second player joins → ready → start → select
a token → **move** it → **deploy** a token → **end turn**, with the HUD
updating on every state change and the server accepting every action. Plus
`kukicha fmt --check .`, `kukicha check ./...`, `make build` and `make test` all
green.

### 0.1 Instantiate the input controller

`web_server/static/game_client.js` — construct `InputController` alongside the other managers:

```js
this.inputController = new InputController(this);
```

`InputController` already takes `(gameClient)` and already exposes `setupInputHandlers()`. It
reads `gameClient.networkManager` and `gameClient.stateManager` lazily, so constructing it early is
safe — but `setupInputHandlers()` must still be called after `initGameModules()` (it is, at
`game_client.modules.js:1090`, inside the `requestAnimationFrame` callback).

**Verification:** clicking a token highlights it; `Enter` ends the turn; `Tab` cycles tokens.

### 0.2 Reconcile the HUD with the template

Decision: **the template is the source of truth.** The live HUD ids are
`#turnNumber`, `#gamePhase`, `#turnPhase`, `#currentPlayer`, `#playersList`,
`#crystal-effects-indicator`.

- Rewrite `ui_manager.js#updateHUD` to populate those ids, porting the working implementations out
  of the dead `game_client.ui.js` (the crystal-effects badge rendering with
  `.effect-badge` / `.fog-of-war` / `.phantom-enemies` / `.damage-boost` / `.speed-boost` classes is
  already written and already styled in `index.css` — reuse it verbatim).
- **Delete `web_server/static/game_client.ui.js`** (690 lines of dead code) after porting.
- Add a `#crystal-status` line to the HUD if the crystal's capture progress is not otherwise shown.

**Verification:** the HUD updates on every state change; crystal-effect badges appear when an effect
is active.

### 0.3 Fix the crystal-effects module

Convert `web_server/static/game_client.crystal_effects.js` to an ES module that imports
`game_client.constants.js`, or export the needed constants onto `window` from the constants
module. Prefer the ES-module conversion — it removes the classic-script/global-lexical coupling
entirely.

Also fix the dead `"crystal"` / `"crystal_glow_1..6"` mesh references in `renderer.animations.js`
(the crystal mesh is now `"nlo_hub"`).

### 0.4 Introduce the server-side event stream

This is the biggest single chunk of Phase 0 and the enabler for everything downstream.

**Server (`server/`):**

1. New `server/game_events.kuki` (or reuse `game/game_events.kuki` + a server-side emitter):
   - `GameSession` gains `events: list of GameEvent`, `eventSeq: int`, `snapshots: list of ...`.
   - `executeGameAction` inspects the returned `ActionResultData` and appends the corresponding
     event(s). `ActionResultData` already carries everything needed:
     - `MoveData{token_id, old_position, new_position}` → `TokenMoved`
     - `AttackData{attacker_id, defender_id, damage_dealt, defender_killed}` → `CombatResolved`
     - `DeployData{new_token_id, health_value, position}` → `TokenDeployed`
     - `TurnEndData{turn_number, next_player_id, generators_disabled, crystal_captured}` →
       `TurnChanged` + `GeneratorChanged` / `CrystalChanged`
   - `MysteryTriggered` needs the mystery result — `game/mystery_square.kuki` returns a
     `MysteryEventResult`; thread it into `MoveData.mystery_effect` (already present in the
     variant) and emit from there.
2. `broadcastState` → `broadcastSession` now sends **both**:
   ```kukicha
   {"type":"EVENT","game_id":sid,"seq":sid.eventSeq,"event":eventToDict}
   {"type":"FULL_STATE","game_id":sid,"game_state":perPlayerState}
   ```
3. Add a per-session mutex so concurrent actions serialize (§2.9).

**Client (`web_server/static/`):**

5. `network_manager.js` — add an `event` handler branch; emit `event` with the parsed frame.
6. Replace the ad-hoc `stateUpdateLock`/`stateUpdateQueue` with `seq`-based ordering: drop frames
   with `seq <= lastSeq`, and if a gap is detected (`seq > lastSeq + 1`), request a resync
   (`SSE_FALLBACK_REQUEST` equivalent → a new `RESYNC_STATE` WS message).

**Verification:** the browser console logs every event; the existing-but-dead
`animateCombat` / `animateTokenMove` / `animateGeneratorUpdate` / `animateCrystalUpdate` /
`animateMysteryEvent` handlers now actually fire.

### 0.5 Unify the HTTP and WS state paths

- `HTTPHandler.HandleAction` broadcasts the **per-player full state**, matching WS — not the slim
  `ToDict()`. Add a `broadcastFullState(session)` helper in the server package and call it from
  both paths.
- `HTTPHandler.HandleGetState` returns `ClientStateDict(playerId)` for the requesting player, not
  the shared slim dict.
- Fix the client-side key mismatch (`data.data || data`) by standardizing on a single envelope.

### 0.6 Fix the phantom-client bug (HTTP joiners get no pushes)

`HTTPHandler.HandleJoinGame` must not fabricate a `WSClient` with an empty `conn`. Options:
- **(a)** Give the session a separate list of *polling* subscribers and have `GET /state` serve
  them (they already poll) — i.e. accept that HTTP clients poll, and make sure `GET /state` is
  complete. **Recommended**: simplest, and it is the path the agent seat will use.
- **(b)** Add a real WS upgrade for HTTP-joined clients (they'd need to re-connect with their
  `player_id`). Deferred.

Under (a), remove the misleading `UpdateClientPlayerID` call and document that HTTP-joined players
are poll-only.

### 0.7 Deterministic `color_index`

`game/state_serializer.kuki` — `playerToDict` is called with an incrementing index over a **map
iteration**. Replace with the lobby's `PlayerInfo.colorIndex`, or with a stable sort of
`gs.players` by ID. Since `game/` must not depend on `server/`, use a stable sort:

```kukicha
playerIds := sortedKeys(gs.players)   # stable, deterministic
for idx in playerIds
    result.players[playerIds[idx]] = playerToDict(gs.players[playerIds[idx]], idx)
```

Also make it match the seat order the lobby assigned.

### 0.8 Harden the WebSocket path

- `conn.SetReadLimit(...)` to actually enforce a message cap. Note the existing
  `MAX_MESSAGE_SIZE = 1024` (`server/websocket_handler.kuki:10`) is declared but never used, and
  1 KiB is far too small for a `FULL_STATE` frame — raise it to ~256 KiB and apply it.
- `checkWsOrigin` — restrict to the configured web-server origin instead of `true`.
- Wire `RateLimiter.CheckAction(playerId)` into `handleGameAction` (the HTTP path already has it).
- Add a per-session `sync.Mutex` around `executeGameAction`.

### 0.9 Turn timeout / auto-pass

Implement `TURN_TIMEOUT_SECONDS` (already defined, unused). Required before agent seats exist, or a
stalled LLM hangs the match. Design: the server tracks `turnStartedAt`; a watchdog ends the turn
after the timeout and emits a `TurnChanged` event. Also emit a `TURN_TIMER` event so the browser can
show a countdown.

### 0.10 Cleanup

- Delete `web_server/static/game_client.ui.js`.
- Wire `Renderer3D.updateGeneratorHums(generators)` from the state-update path (hums currently
  never play).
- Replace the `TIMEOUT_CONFIG` global-vs-module mismatch in `mercure_client.js` (it silently uses a
  literal copy).
- **Mercure/SSE: keep the code, but make the client unambiguously WebSocket-primary.** (Decision:
  the full-Phase-0 scope does not delete the Mercure publisher.) The Mercure publisher is
  currently *entirely* dead — `PublishFullState` / `PublishStateUpdate` / `PublishTurnChange` are
  never called, and the topics are per-**game**, not per-player, so per-player fog (§0.11) cannot
  be expressed on them without rework. Therefore:
  - Do **not** enable `MERCURE_ENABLED` / `SSE_PRIMARY_MODE` in any deployment.
  - Make the client's SSE attempt explicitly opt-in (a `?sse=1` query flag or a settings toggle),
    so the default path is unambiguously WS. Today the client silently attempts SSE and can fall
    back mid-game, which is a source of the "state stopped updating" class of bug.
  - Add a short note to `web_server/MERCURE_SETUP.md` stating the current status: *implemented but
    not wired; per-player topics required before it can carry fog-of-war state.*
  - **Revisit in Phase 2**: if the agent seat ends up preferring SSE for its state stream, the
    per-player topic scheme (`{prefix}/{gameId}/{playerId}`) must be implemented first.

### 0.11 Unconditional fog-of-war

Per the decision in §3.3, this becomes a core rule and lands in Phase 0.

- **New `game/visible_state.kuki`** — `VisibleStateDict(gs, viewer)` implementing the §3.3 table.
- **Replace `ClientStateDict` calls** in `server/ws_endpoint.kuki` (`broadcastState`) and
  `server/http_handler.kuki` (`HandleGetState`, `HandleAction`) with `VisibleStateDict`. Keep
  `ClientStateDict` as the unfiltered serializer for internal/server-side use (and for the
  `learn/` layer).
- **Event filtering** — `server/` filters each `GameEvent` per receiving player before broadcasting
  (§3.3 "Event filtering"). This means `broadcastState` becomes per-player twice: once for the
  state snapshot, once for each event frame. Keep the two in one loop so they cannot drift.
- **Renderer support** — `renderer.tokens.js#updateTokens` must skip tokens with
  `is_visible === false` and tolerate a `null` position.
- **Board grid occupants** — `board.grid[].occupants` must be masked consistently, or the fog is
  trivially bypassed. This is the easiest thing to miss; treat it as a required part of the task.
- **Tests** — add `game/visible_state_test.kuki` covering: own tokens always visible, enemy inside
  radius visible, enemy outside masked, enemy on an owned cell revealed, generator/crystal
  ownership masked at distance, and no position leak through `board.grid[].occupants`.

**Risk note:** this is the highest-blast-radius change in Phase 0. It touches the serializer, the
server broadcast path, the event path, and the renderer. Land it *after* 0.4 (the event stream) is
stable, so the event-filtering work has a frame to hang on, and before Phase 1 so that all the
"juice" is built on the final state shape.

### Phase 0 exit gate

```bash
kukicha fmt --check . && kukicha check ./... && kukicha build ./... && go test ./...
```
Plus a manual browser checklist:
- [ ] Click a token → selection glow + valid-move indicators.
- [ ] Move / attack / deploy / end-turn all work over WebSocket.
- [ ] HUD updates every turn.
- [ ] Console shows `EVENT` frames with monotonically increasing `seq`.
- [ ] An attack visibly moves the token and updates health **without** a page reload.
- [ ] With fog on: a second browser in a separate seat cannot see the first player's tokens, and
      neither can see the other's via `board.grid[].occupants`.

---

## 5. Phase 1 — Game feel & juice

Depends on Phase 0.4 (event stream) and 0.11 (fog — all of Phase 1 draws over the final state
shape, and the threat overlays in 1.4 must respect masked tokens).

### 1.1 Screen shake, impact particles, floating combat text

**New file `web_server/static/renderer.fx.js`** (a `Renderer3D.prototype` side-effect module,
imported by `game_client.renderer.js` — matching the existing `renderer.animations.js` pattern).

Components:
- **Trauma-based shake** (Squirrel Eiserloh's model): a scalar `trauma ∈ [0,1]`; per frame
  `shake = trauma²`, offsets applied to `camera.target` (not `camera.position`, so the ArcRotate
  rig stays intact) and to `camera.rotation`; trauma decays exponentially.
  ```js
  Renderer3D.prototype.addTrauma = function(amount) {
      this.trauma = Math.min(1, (this.trauma || 0) + amount);
  };
  Renderer3D.prototype.updateTrauma = function(dt) {
      this.trauma = Math.max(0, (this.trauma || 0) - dt * TRAUMA_DECAY);
      const shake = this.trauma * this.trauma;
      // apply to camera target + rotation, scaled by noise
  };
  ```
  Hook `updateTrauma` into the existing `updateAnimations()` in `renderer.animations.js`, which
  already runs every frame.
- **Impact particles**: reuse the existing `triggerExplosion(position, color)` in
  `renderer.animations.js`; add `triggerTokenBurst(tokenId, color)` and
  `triggerCrystalBurst(position)` using the same `BABYLON.ParticleSystem` + `DynamicTexture`
  pattern the ambient particles already use (`renderer.base.js:219`).
- **Floating combat text**: Babylon `DynamicTexture` on a billboard plane, or (cheaper and
  pixel-consistent with the HUD) DOM elements positioned by projecting the token's world position
  through `BABYLON.Vector3.Project`. **Recommendation: DOM** — it reuses the existing HUD/CSS
  conventions (`#hud`, `.action-error`, z-index scale in `index.css`) and avoids texture churn on
  mobile.

Event → FX mapping:

| Event | FX |
|---|---|
| `CombatResolved` (killed) | trauma 0.6, red burst at defender, floating `-{damage}`, token mesh dissolve |
| `CombatResolved` (survived) | trauma 0.25, white burst, floating `-{damage}` |
| `TokenMoved` | whoosh sound, motion trail |
| `TokenDeployed` | deploy pulse ring, rising chord |
| `GeneratorChanged` (disabled) | trauma 0.8, orange explosion (existing `triggerExplosion`) |
| `CrystalChanged` (captured) | trauma 0.9, cyan/gold burst, victory sting, confetti (`confettiParticles` already exists) |
| `MysteryTriggered` | existing mystery ring animation + `mystery_bing` |

### 1.2 Dynamic camera choreography

Extend `web_server/static/camera_controller.js` with a **focus** system layered on top of the
existing overview/first-person modes:

```js
class CameraController {
    // existing: cameraMode, toggleCameraMode(), update(token), resetView()

    focusOn(worldPos, {radius, duration, easing}) { ... }   // cinematic push-in
    releaseFocus() { ... }                                  // return to the user's framing
    followToken(tokenId) { ... }                            // follow mode
}
```

Three behaviours:
1. **Event push-in** — `GeneratorChanged` (disabled) or `CrystalChanged` (captured) → brief
   `focusOn` on the affected cell at a tighter radius, then release.
2. **Follow mode** — when it is not the local player's turn, optionally follow the active player's
   token. Make this a **user setting**, not a default (it fights with manual camera control).
3. **Combat framing** — on `CombatResolved`, frame both attacker and defender.

Critically: the camera must **not** steal control. Any user input (drag / pinch / wheel) during a
focus cancels it immediately. Track that in `input_handler.js` by emitting a `camera:user_input`
event.

Existing infrastructure to reuse: `_transition` (the smoothstep overview transition),
`_setCameraPose`, `moveCamera*`, `adjustZoom`.

### 1.3 Audio punch, dynamic synthesis, ducking

**Prerequisite: a master bus.** `audio_manager.js` currently connects every gain node straight to
`destination`. Restructure:

```
sources → categoryGain (sfx | music | hum | voice) → masterGain → compressor → destination
```

- `masterGain` — global volume + mute, exposed as a UI slider (there is currently **no volume UI**).
- `compressor` (`DynamicsCompressorNode`) — keeps explosions from clipping.
- `duck(category, amount, duration)` — during a combat event, ramp `musicGain` and `humGain` down
  to ~25% over 120 ms, hold, then restore over 400 ms. Implement with
  `gain.linearRampToValueAtTime` + `setTargetAtTime`.

New synthesized cues (the file already has a full synthesizer path —
`_playSlidingSound`, `_playFlushingSound`, etc.):
- `_playTurnCountdownTick(step)` — rising pitched click.
- `_playBassHit(intensity)` — low sine + fast decay envelope.
- `_playChordRise(duration)` — stacked detuned saws through a lowpass sweep.
- `_playCrystalExtract()` — shimmering arpeggio + sub drop.

Map events → cues via the same table as §1.1.

Also wire `Renderer3D.updateGeneratorHums()` from the state path (§0.10) so the ambient layer is
actually alive.

### 1.4 Tactical telegraphing and threat overlays

Extend `web_server/static/renderer.indicators.js` (already has hover / valid-move / valid-attack
ground quads). Add:

- **Threat tiles on hover** — when hovering a cell, highlight the cells from which an enemy token
  could attack it (8-neighbour check against enemy tokens' attack range). Under fog (§0.11) this
  must only consider **visible** enemy tokens — the overlay is a projection of what the player
  knows, not of the true board.
- **Generator control radius** — a translucent ring/disc around each generator showing the radius
  in which a player controls it.
- **Crystal extraction path** — a polyline from the player's tokens to the crystal showing the
  shortest path, plus a progress arc on the crystal showing capture progress.

These are pure client-side projections over state the client already has — the cheapest and
highest-value slice of Phase 1. Ship them **first**, before 1.1–1.3.

### 1.5 Mobile- and low-end-safe budgets

`DeviceCapabilities.getRenderingConfig()` already reports `particleMaxCount` (500/1000/2000).
Cap shake/particles/FCT accordingly, and disable bloom + volumetric light scattering on the `low`
profile. `renderer.base.js` already gates god rays on `shouldOptimizePerformance()`.

---

## 6. Phase 2 — AI arena, spectator mode, replays

### 2.1 Agent seat

**Server changes (`server/`):**

New file `server/agent_endpoint.kuki`:

| Route | Purpose |
|---|---|
| `POST /api/game/{id}/seat` | Claim an agent seat. Body: `{player_name, model, agent_kind}`. Returns `{player_id, token, game_id, player_name, tool_schemas}`. Reuses `CreatePlayerToken`. |
| `GET  /api/agent/{id}/observe` | Fog-filtered state for the calling agent. Requires `Authorization: Bearer <jwt>`. |
| `GET  /api/agent/{id}/actions` | Typed legal actions for the calling agent (`ActionsWithPhase()` → `ActionsToDicts`). |
| `POST /api/agent/{id}/act` | Submit one action. Body: `{type, data:{…}}` — the *same* envelope the HTTP path already uses, so `HTTPHandler.buildGameAction` is reused verbatim. |
| `POST /api/agent/{id}/say` | Radio chatter: `{text}`. Appended to the event log as `RadioChatter` and broadcast to spectators. |

Mark the seat with `ClientType.HTTP_AI` (already declared in `server/lobby.kuki:19`, never used) and
add `isAgent` / `model` to `PlayerInfo` so the browser can render an agent badge.

**Tool schemas** are already producible: `game/ai_strategy.kuki#ActionResponseToDict` renders each
legal action as a stable snake_case dict, and `ActionDataToDict` renders the result. Generate the
MCP/LLM tool schemas from those two functions — no new schema machinery.

**Fog-of-war** is already in place for all network clients (Phase 0.11), so `/observe` and the
agent's own `/state` are fogged by construction. The agent seat inherits it for free.

**MCP server:** a **separate package** `mcp/` (new `petiole mcp` directory) that speaks MCP over
stdio or HTTP and proxies to the game server's agent REST API. It is stateless, so it can be run
per-agent, scaled, or hosted anywhere. Tool surface:

| Tool | Maps to |
|---|---|
| `get_visible_state` | `GET /api/agent/{id}/observe` |
| `get_legal_actions` | `GET /api/agent/{id}/actions` |
| `move_token(token_id, x, y)` | `POST /api/agent/{id}/act` `{type:"MOVE"}` |
| `attack(attacker_id, defender_id)` | `POST /api/agent/{id}/act` `{type:"ATTACK"}` |
| `deploy_token(health_value, x, y)` | `POST /api/agent/{id}/act` `{type:"DEPLOY"}` |
| `end_turn()` | `POST /api/agent/{id}/act` `{type:"END_TURN"}` |
| `say(text)` | `POST /api/agent/{id}/say` |

Rationale for a separate package rather than inlining MCP into `server/`: the game server stays a
game server; the MCP process is a thin, stateless adapter that can be pointed at any deployment.
It also means the agent API can be exercised with plain `curl` (no MCP client needed) for testing.

**Turn timeout** (§0.9) is what keeps a stalled LLM from deadlocking the session. The agent seat
must also be exempt from the human-facing rate limits (`CheckAction`: 10 burst / 5 s) or be given a
separate, looser bucket — an LLM turn is a burst of tool calls.

### 2.2 Spectator mode

The browser needs a read-only seat:

- `POST /api/game/{id}/spectate` → `{token, game_id}`.
- A spectator WS client receives `FULL_STATE` + `EVENT` frames but **cannot** act. Enforce this in
  `handleGameAction`: reject any action whose client is not a seated player.
- Spectators do not count against `maxPlayers` (currently hard-capped at 4). Keep spectators in a
  separate list on `GameSession`.
- `GET /api/games` should list in-progress games for spectators to find (currently only `WAITING`
  lobbies are listed).
- **Spectators see everything.** A spectator has no player seat, so there is no visibility radius
  to apply — spectators receive the unfiltered `ClientStateDict`. This is a deliberate exception to
  the unconditional fog rule (§0.11): fog exists to create *player* information asymmetry, and a
  spectator is a broadcast viewer, not a competitor. Replays (Phase 2.4) follow the same rule, with
  a per-player "perspective" selector available for study purposes.

### 2.3 Radio chatter + agent HUD

**New file `web_server/static/game_client.comms.js`:**

- Renders a **"Tactical Comms" sidebar** fed by `RadioChatter` events.
- Per-agent avatar badge + a sentiment/tone indicator. Keep sentiment simple: let the agent supply
  a `tone` field (`"confident" | "aggressive" | "cautious" | "neutral"`) rather than running
  sentiment analysis in the browser.
- Collapsible on mobile; the panel shares the existing `<details>` pattern used by `#hud` and
  `#controls`.

Add a `RADIO_CHATTER` DOM section to `web_server/templates/index.html` and styles to
`index.css` following the existing `.effect-badge` / `.player-info` conventions.

### 2.4 Battle record viewer + replay scrubber

**Server:** `GameSession` maintains `battleLog` (per §3.4). New routes:

| Route | Purpose |
|---|---|
| `GET /api/game/{id}/battle` | Download the battle log JSON (`application/json`, `Content-Disposition: attachment` for `.rttc-battle.json`). |
| `POST /api/game/{id}/battle/import` | Load a battle log into the viewer (client-side only — no server mutation). |

**Client — new file `web_server/static/game_client.replay.js`:**

- `ReplayController` owns `snapshots[]`, `events[]`, `radio[]`, `cursor`, `speed` (1× / 2× / 5×),
  `playing`.
- The battle log stores the **unfiltered** snapshots (it is a local file, not a network payload).
  The viewer can optionally apply a perspective filter on playback to study the match from one
  player's seat — that reuses `VisibleStateDict` logic, but on the client.
- The scrubber is a range input bound to `cursor`; dragging it applies `snapshots[cursor]` to the
  renderer via the **existing** `Renderer3D.updateGameState(state)` path — no new rendering code.
- Event markers (attack, kill, generator, crystal) are drawn as ticks under the scrubber.
- Playback re-emits recorded events into the same FX pipeline as live play, so a replay *looks* like
  the live game. This is the payoff of §3.1: **one** event vocabulary, two consumers.
- Export / import buttons → download / `FileReader` the `.rttc-battle.json`.

`state_manager.js` gains a `replayMode` flag: while replaying, incoming live updates are ignored
(or the session is detached entirely — the latter is cleaner).

### Phase 2 exit gate

- [ ] Two LLM agents (e.g. Gemini vs. Claude) play a full match to completion via MCP, headless.
- [ ] A browser spectator sees the match live, with the comms sidebar showing both agents' chatter.
- [ ] The finished match can be scrubbed, replayed at 1×/2×/5×, and exported as
      `.rttc-battle.json`; re-importing it reproduces the match exactly.

---

## 7. Phase 3 — Frictionless & serverless multiplayer

### 7.1 Acoustic modem — re-scoped (highest-risk item)

The roadmap's "18–20 kHz" target has real hardware problems:

- Many laptop microphones have a low-pass around 16–18 kHz, and some laptops have aggressive
  noise suppression that will not pass 18 kHz at all.
- Browser `getUserMedia` requires a user gesture and a secure context; the page must stay open and
  audible.
- `AnalyserNode` FFT resolution at 44.1 kHz is ~10.5 Hz/bin — workable for FSK, but the *modem*
  has to be right before the *link* is right.

**Re-scoped design:**

1. **Calibration handshake first.** Before enabling the modem, play a known preamble and verify the
   receiver sees it. If not, refuse to arm the link and say why.
2. **Two bands.** Primary: 15–17 kHz (near-ultrasonic, inaudible-ish to most adults, better mic
   pass-through). Fallback: 8–12 kHz "party mode" — audible, works on everything including phone
   speakers, still short-range.
3. **FSK framing.** 2 frequencies per bit (e.g. 15.5 / 16.5 kHz), 20–50 ms symbol duration,
   preamble → sync word → length → payload → CRC-16. A 16-byte turn message fits comfortably.
4. **Symmetric roles.** In a two-device game one device is *host* (owns the authoritative state) and
   the other is *guest*; the guest's turn packets are sent acoustically and the host acks. This
   avoids solving full peer-to-peer state sync over a one-way-ish channel.
5. **Turn the modem off by default.** It is an opt-in mode behind a "Local (no server)" entry on
   the connection screen.

**Recommendation:** treat this as a **stretch goal after Phase 4**, and ship the cheaper wins first:
- **Same-device hotseat** — two players, one screen, alternating turns. Near-zero implementation
  cost (a seat switch in the existing lobby model) and covers "two people, one laptop".
- **LAN direct play** — WebRTC `RTCDataChannel` between two browsers on the same LAN, with the host
  browser as the authority. Needs the WASM game-logic worker from §7.2.

### 7.2 Host-authoritative relay with a WASM game-logic worker

The roadmap hand-waves "WASM-compiled Kukicha game logic worker". This is actually tractable here
because **`game/` is pure logic with zero external dependencies** — it has no rendering, no network,
and no stdlib dependencies beyond `shared/`.

Spike (half a day):

```bash
kukicha build ./game/...         # transpile to Go
GOOS=js GOARCH=wasm go build -o game.wasm ./game/
```

If the `game` package compiles to WASM cleanly, the whole "host browser is the authority" design
becomes real:

- The host browser loads `game.wasm` in a Web Worker, holds the authoritative `GameState`, and
  validates every action locally.
- The guest connects over WebRTC `RTCDataChannel` (or a tiny stateless WS relay) and sends action
  requests; the host replies with the resulting state.
- The **stateless relay** is then genuinely trivial: a WebSocket server that forwards each message
  to the other peer in a room and keeps no state. It can be ~100 lines, or a hosted edge function.

This also gives a clean fallback story for Phase 3's "seamless fallback between full authoritative
server mode and lightweight relay mode": the client picks a transport based on what the connection
screen selected.

**Gate:** if the WASM spike fails (e.g. `game/` pulls in an OS-dependent dependency through
`stdlib/random`), fall back to a **host-authoritative relay with a server-side arbiter** — the
relay forwards to the authoritative game server, which is the current model, and the "relay" only
removes lobby/state management from the relay itself. Lower ambition, still useful.

### 7.3 Explicitly out of scope for Phase 3

- **Voice chat over the acoustic modem.** The roadmap conflates "audio-based multiplayer" (data
  over audio) with "voice chat" (Battle Drones' actual audio-multiplayer feature). These are
  different problems. Voice chat needs WebRTC and a signalling path — that belongs with the AI
  arena's "radio chatter" (which is *text*), not the acoustic modem.
- **WebRTC video.** Out of scope.

---

## 8. Phase 4 — Mobile touch UX

Much of the foundation already exists: `game_client.device.js` detects touch/mobile/tablet and
reports a performance profile; `index.css` has five responsive breakpoints (768 / 1024 / 480 /
landscape-short / coarse-pointer) and a `#mobile-action-bar` with five buttons; `input_handler.js`
already has tap detection. **Do not rewrite this. Fill the gaps.**

### 8.1 Touch gesture arbitration

The core missing piece: `input_handler.js` currently handles `touchstart/move/end` for tap
detection *only*, and separately relies on Babylon's built-in `multiTouchPanning` /
`multiTouchPanAndZoom` on the ArcRotate camera. But Babylon's pointer input has its buttons
stripped (`camera_controller.js:90`, `pointers.buttons = []`) and the built-in keyboard input is
removed — so **single-finger orbit is dead**, and touch/gesture ownership between the game and the
camera is undefined.

**New file `web_server/static/game_client.touch.js`** — a single gesture arbiter on the canvas:

| Gesture | Action |
|---|---|
| 1 finger, tap (< 300 ms, < 10 px) | Select / act on the cell (uses the existing `handleTap` path) |
| 1 finger, drag | Orbit the camera (alpha/beta) — *new*; currently impossible on touch |
| 2 fingers, pinch | Zoom (radius) |
| 2 fingers, drag | Pan (target) |
| Long-press (> 500 ms) | Context action on the cell (e.g. "move here") |

Implementation notes:
- Use **Pointer Events** (`pointerdown/move/up` with `pointerId` tracking) rather than the current
  mix of `touch*` and `mouse*` listeners — Pointer Events unify mouse/touch/pen and give
  `pointerType` for free. This also removes the current duplicate-listener situation
  (`input_handler.js` registers both `mousedown` and `touchstart`).
- Convert pinch/drag deltas into `cameraController` calls — the controller already exposes
  `adjustZoom(steps)`, `moveCamera*()`, and pan via `_panTarget`.
- **Touch hitboxes:** `scene.pick` on a 32-unit cell is fine on desktop and marginal on a phone.
  Add a pick-radius fallback: if the tap misses the ground mesh, pick against a 2D screen-space
  grid overlay (project the 24×24 cell centres and find the nearest within a 44 px radius).

### 8.2 Radial action palette

**New file `web_server/static/game_client.radial.js`.**

- On selecting a token, show a radial menu of the currently *legal* actions around the token's
  projected screen position: **Move**, **Attack**, **Extract/Deploy**, **Wait/End Turn**.
- The palette must reflect the turn phase. `InputController.calculateValidTargets(token)` already
  computes the legal set per phase — reuse it rather than re-deriving.
- Render as DOM (not Babylon GUI) so it inherits the existing HUD/CSS conventions and gets
  browser-native accessibility. `babylon.gui.min.js` is already loaded but is currently unused — a
  DOM radial is simpler and consistent with the rest of the UI.
- Touch targets ≥ 44 px (the `@media (hover:none) and (pointer:coarse)` block already sets a
  44 × 44 minimum — extend it to the radial wedges).
- Haptics: `DeviceCapabilities.vibrate()` already exists and `index.page.js` already calls
  `navigator.vibrate(50)`.

### 8.3 Responsive HUD

- **End Turn FAB** — a floating action button, bottom-right, ≥ 56 px, always reachable with a
  thumb. `#mobile-action-bar` already has `#mobile-btn-end-turn` as a `.main-action`; promote it
  to a true FAB (circular, elevated, safe-area aware) rather than adding a second control.
- **Collapsible panels** — `#hud`, `#controls`, `#mobile-controls` are already `<details>`; make
  the comms panel and the replay scrubber the same pattern so one CSS rule covers all four.
- **Portrait/landscape** — the CSS already handles `(max-height:500px) and (orientation:landscape)`.
  Verify the radial palette and FAB do not collide with the action bar in landscape.
- **Viewport units** — the canvas is `height:100vh`; on mobile browsers `100vh` exceeds the visual
  viewport when the URL bar is showing. Switch to `100dvh` with a `100vh` fallback.

### Phase 4 exit gate

- [ ] A complete match is playable on a phone using **only** touch: select, move, attack, deploy,
      end turn — no keyboard, no mouse.
- [ ] Single-finger orbit, pinch-zoom and two-finger pan all work without fighting the tap
      handler.
- [ ] The radial palette shows only legal actions for the current phase.

---

## 9. Sequencing, sizing and dependencies

```
Phase 0 ──────────────────────────────────────────────────────────────┐
  0.1 input │ 0.2 HUD │ 0.3 fx-globals │ 0.5/0.6 state paths           │
  0.7 colors │ 0.8 ws hardening │ 0.9 turn timer │ 0.10 cleanup       │
  0.4 EVENT STREAM ─────────────┐                                    │
  0.11 FOG (unconditional) ◀────┘ (needs events to filter)           │
                              │                                     │
Phase 1 ────────────────────────┼─────────────────────────────────────┤
  1.4 overlays (cheapest)       │                                     │
  1.1 shake/particles/FCT  ◀────┘ (needs events)                     │
  1.2 camera choreography ◀────┘                                     │
  1.3 audio bus + ducking (independent of events)                     │
                              │                                     │
Phase 2 ────────────────────────┼─────────────────────────────────────┤
  2.1 agent seat + MCP │ 2.2 spectator │ 2.3 comms │ 2.4 replay      │
                              │                                     │
Phase 4 ────────────────────────┼─────────────────────────────────────┤
  8.1 touch │ 8.2 radial │ 8.3 responsive  (independent of 1–2)      │
                              │                                     │
Phase 3 ────────────────────────┼─────────────────────────────────────┤
  hotseat (cheap) │ 7.2 WASM spike + relay │ 7.1 acoustic (stretch)   │
```

| Block | Size | Notes |
|---|---|---|
| Phase 0.1–0.3, 0.7, 0.10 | ~1 day | Pure client fixes, low risk, immediately visible. |
| Phase 0.4 (event stream) | ~2–3 days | The keystone. Touches `game/`, `server/`, and the client. |
| Phase 0.11 (unconditional fog) | ~2 days | Highest blast radius: serializer + both broadcast paths + event filtering + renderer. |
| Phase 0.5–0.6, 0.8, 0.9 | ~1.5 days | Server correctness and safety. |
| Phase 1.4 | ~0.5 day | Independent of events. |
| Phase 1.1 | ~2 days | New `renderer.fx.js` + event→FX table. |
| Phase 1.2 | ~1.5 days | Camera focus system + user-input cancellation. |
| Phase 1.3 | ~2 days | Master-bus refactor is the bulk of it. |
| Phase 2.1 | ~2.5 days | Agent endpoints + MCP package. Fog is already done in Phase 0. |
| Phase 2.2 | ~1 day | Spectator seat. |
| Phase 2.3 | ~1 day | Comms panel. |
| Phase 2.4 | ~2 days | Replay controller + scrubber UI. |
| Phase 4.1–4.3 | ~3 days | Touch arbiter + radial + CSS. |
| Phase 3 hotseat | ~0.5 day | Cheap win. |
| Phase 3.2 WASM spike | ~1 day spike, ~3 days to finish if green | |
| Phase 3.1 acoustic | ~5 days, high risk | **Stretch — after Phase 4.** |

**Rough total: ~28–34 engineer-days** for Phases 0–4 excluding the acoustic modem.

---

## 10. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Event stream slips and Phase 1 is rebuilt on state diffing | Medium | High | Phase 0.4 is a hard gate; no Phase 1 work starts until `EVENT` frames are visible in the browser console with monotonic `seq`. |
| **Unconditional fog leaks state through `board.grid[].occupants`** | **Medium** | **High** | A masked token whose id still appears in the cell's occupant array is a total bypass. §3.3 requires occupant masking; `game/visible_state_test.kuki` asserts it; add a second browser seat to the manual exit checklist. |
| Fog breaks the renderer (null positions, missing tokens) | Medium | Medium | `renderer.tokens.js` must guard `is_visible === false` and `position === null`. The fog may be flag-gated *during* development, but the end state is unconditional (**D4**) — the flag is a rollout safety net, not the destination. |
| Fog makes the two AI clients inequitable (in-process AI omniscient) | Certain | Low | Documented boundary in §3.3.1. When the in-process AI is promoted to a networked seat it must observe through `VisibleStateDict`. |
| Audio-bus refactor breaks all existing SFX | Medium | Medium | Land the bus refactor behind a feature flag; keep the existing per-category gains working until the master bus is verified. |
| MCP package becomes a second, divergent client | Medium | Medium | The MCP package must be a **thin proxy** — no game logic, no state caching. The game server stays the only authority. |
| WASM build of `game/` fails | Medium | Low | Time-box the spike to half a day; §7.2 has a documented fallback. |
| Acoustic modem never links on real hardware | **High** | Medium | Ship the calibration gate so failure is *diagnosed*, not mysterious. Scheduled as a stretch goal after Phase 4. |
| Touch arbiter regresses desktop mouse input | Medium | Medium | Pointer Events unify both; keep the mouse path under regression test in a real browser. |
| `game/` growing server/network concerns | Low | High | `game/` must stay pure. The event vocabulary belongs in `game/`; the *session log* belongs in `server/`. |
| Mercure left in a half-enabled state | Medium | Low | §0.10: client SSE becomes opt-in, deployment keeps `MERCURE_ENABLED=false`, and the status is written down in `MERCURE_SETUP.md`. |

---

## 11. Decisions taken and still open

### 11.1 Decided (2026-10-21)

| # | Decision | Consequence for the plan |
|---|---|---|
| D1 | **Full Phase 0 baseline repair.** | §4.0.1–0.11 all in scope. Mercure/SSE is **kept** but the client becomes explicitly WS-primary (§0.10). |
| D2 | **Server-side `EVENT` stream.** | The event vocabulary in `game/game_events.kuki` and seq-numbered `EVENT` frames are the foundation for Phase 1, Phase 2, and the replay scrubber. No client-side diffing. |
| D3 | **Acoustic modem = stretch goal, after Phase 4.** | §7.1 is explicitly the lowest priority; §7's hotseat and LAN relay ship first. |
| D4 | **Fog-of-war for everyone, unconditionally.** | Promoted to a core rule: new `game/visible_state.kuki` in Phase 0 (§0.11), with the `learn/`-layer boundary in §3.3.1 and occupant-masking as a required part of the task. |

### 11.2 Still open

1. **Turn timeout policy.** Auto-pass after 30 s of inactivity is the obvious default, but with LLM
   seats a 30 s budget may be too tight (thinking time). Consider a per-client-type timeout: 30 s
   for humans, 120 s for agents. (`TURN_TIMEOUT_SECONDS = 30` already exists and is unused.)
2. **Spectator mode — in scope or not?** Does the browser need to *spectate* AI-vs-AI matches, or
   only to *play against* an AI? Spectator mode (Phase 2.2) roughly doubles the Phase 2 server work
   but is what makes the "Battle Spectator Mode" idea actually work. The plan assumes yes; say if
   it should be dropped.
3. **Relay hosting.** If Phase 3.2 proceeds, does the stateless relay ship in this repo, or is it a
   separate deployment artifact? A ~100-line relay in `server/` (a second binary) is the simplest
   thing that could work.
4. **Fog radius and tuning.** `VISIBILITY_RADIUS = 3` is a starting point. The 24×24 board with
   tokens that move 1–2 cells per turn means a radius of 3 shows a lot. Worth a playtest sweep at
   2 / 3 / 4 before locking it.
5. **Should a player's *own* previously-seen enemies stay marked on the board** (a "last known
   position" ghost)? This is a UX call with a real information-leak implication if implemented
   server-side vs. client-side. Recommendation: implement it **client-side** (the client remembers
   the last position it saw), so the server stays stateless about it.
6. **Audio modem band.** 15–17 kHz primary vs. 8–12 kHz audible primary? A calibration handshake
   that picks the best band automatically would answer this empirically.

---

## 12. Verification matrix

| Roadmap milestone | Where verified | How |
|---|---|---|
| **M1 Game Juice** | `renderer.fx.js`, `camera_controller.js`, `audio_manager.js` | Trigger a combat event; assert camera trauma > 0, a particle burst spawned, a floating damage label appeared, and the music ducked. |
| **M2 Replay Scrubber** | `game_client.replay.js` | Export a match; scrub to turn *N*; assert the board matches `snapshots[N]`; play at 1×/2×/5×. |
| **M3 AI Arena HUD** | `ui_manager.js`, `game_client.comms.js` | Two agents battle; assert the comms sidebar receives `RadioChatter` frames in real time and the badge renders. |
| **M4 Mobile Controls** | `input_handler.js`, `game_client.touch.js`, `game_client.radial.js` | Play a full match on a touch device with the keyboard disconnected. |
| **M5 Audio Sync** | `audio_manager.js` | Two devices exchange turns over chirps with no server. **Stretch goal.** |

Run the standard gate after every phase:

```bash
kukicha fmt --check .
kukicha check ./...
kukicha build ./...
go test ./...
make lint
```

---

## Appendix A — File-by-file change map

| File | Phase | Change |
|---|---|---|
| `web_server/static/game_client.js` | 0.1 | Instantiate `InputController`. |
| `web_server/static/ui_manager.js` | 0.2, 2.3 | Rewrite `updateHUD` against the real template ids; add the comms panel. |
| `web_server/static/game_client.ui.js` | 0.2 | **Delete** after porting. |
| `web_server/static/game_client.crystal_effects.js` | 0.3 | Convert to an ES module; import constants. |
| `web_server/static/network_manager.js` | 0.4 | Handle `EVENT` frames; seq-based ordering; resync. |
| `web_server/static/renderer.animations.js` | 0.3, 1.1 | Fix dead crystal-mesh pulses; hook trauma update. |
| `web_server/static/renderer.indicators.js` | 1.4 | Threat tiles, generator radius, crystal path. |
| `web_server/static/renderer.fx.js` | 1.1 | **New.** Trauma shake, particle bursts, floating combat text. |
| `web_server/static/game_client.renderer.js` | 1.1 | Import `renderer.fx.js`. |
| `web_server/static/camera_controller.js` | 1.2 | Focus system, follow mode, user-input cancellation. |
| `web_server/static/audio_manager.js` | 1.3 | Master bus, compressor, ducking, new synth cues. |
| `web_server/static/game_client.comms.js` | 2.3 | **New.** Tactical Comms sidebar. |
| `web_server/static/game_client.replay.js` | 2.4 | **New.** Replay controller + scrubber. |
| `web_server/static/game_client.touch.js` | 4.1 | **New.** Pointer-event gesture arbiter. |
| `web_server/static/game_client.radial.js` | 4.2 | **New.** Radial action palette. |
| `web_server/static/input_handler.js` | 4.1 | Delegate to the touch arbiter; keep the mouse path. |
| `web_server/static/index.css` | 1.4, 2.3, 4.3 | Threat overlays, comms panel, radial palette, FAB, `dvh`. |
| `web_server/templates/index.html` | 0.2, 2.3, 2.4, 4.2 | Add comms panel, scrubber, radial container. |
| `game/game_events.kuki` | 0.4 | **New.** Event variant enum + `EventToDict`. |
| `game/visible_state.kuki` | 0.11 | **New.** `VisibleStateDict` (fog of war, unconditional). |
| `game/visible_state_test.kuki` | 0.11 | **New.** Fog correctness tests (incl. occupant-array leak). |
| `game/state_serializer.kuki` | 0.7, 0.11 | Deterministic `color_index`; keep `ClientStateDict` unfiltered for internal use. |
| `game/ai_actions.kuki` | 0.4 | Thread mystery/crystal detail into `ActionResultData` for event emission. |
| `renderer.tokens.js` (`web_server/static/`) | 0.11 | Skip masked tokens; tolerate `position: null`. |
| `server/game_coordinator.kuki` | 0.4, 0.11 | Session event log, snapshots, mutex; per-player event filtering. |
| `server/ws_endpoint.kuki` | 0.4, 0.8, 0.11, 2.2 | Emit `EVENT` frames; read limit; origin check; rate limit; fogged state; spectator handling. |
| `server/http_handler.kuki` | 0.5, 0.6, 0.11 | Per-player fogged full state; drop the phantom client. |
| `server/agent_endpoint.kuki` | 2.1 | **New.** Agent seat REST API. |
| `server/lobby.kuki` | 2.1, 2.2 | Use `ClientType.HTTP_AI`; add `isAgent`/`model`; spectator list. |
| `server/auth.kuki` | 2.1 | Reuse `CreatePlayerToken` for agent seats. |
| `server/mercure_publisher.kuki` | 0.10 | Keep, but document as inactive; per-player topics required before it can carry fogged state. |
| `web_server/static/mercure_client.js` | 0.10 | Make the SSE attempt opt-in (WS-primary by default). |
| `web_server/MERCURE_SETUP.md` | 0.10 | Record the current status and the per-player-topic requirement. |
| `mcp/` | 2.1 | **New package.** MCP proxy to the agent REST API. |
| `shared/constants/constants.kuki` | 0.9 | Wire `TURN_TIMEOUT_SECONDS`; add agent-specific timeout. |
| `learn/learn_api.kuki` | 0.11 | Document the omniscient-visibility boundary (§3.3.1). |
| `docs/LEARN_TO_PROGRAM_WITH_MINECRAFT.md` | 0.11 | Same boundary note. |

## Appendix B — Kukicha notes for implementers

The `.kuki` sources use `#` comments (not `//`), `equals` / `isnt` instead of `==` / `!=`,
`when` / `default` instead of `case` / `default`, `list of T` / `map of K to V`, `reference T` /
`optional reference T`, and `onerr` for error handling. Variant enums with payload fields are the
right shape for the event vocabulary — note that payload fields must be **capitalized** to be
readable across packages (`TokenID: types.TokenID`), and that `switch` on a variant enum is
exhaustiveness-checked.

Run `kukicha fmt -w .` before committing; `make lint` is `kukicha fmt -w --check .`.

### B.1 Traps hit while implementing Phase 0

The first two are compiler bugs, reported upstream to the Kukicha maintainers
on 2026-10-21. They are **not** bugs in this project, but they will bite
anyone writing Kukicha code in the meantime — so the working forms are
recorded here.

**`empty <Alias>` lowers to a nil map — use `make(<Alias>)`.**
`empty map of string to any` is rewritten by the compiler into an *allocated* map. Applying the
same `empty` form to a transparent alias (`type JSONMap = map of string to any`) lowers to
`*new(JSONMap)` — a nil map. Writing to it panics at runtime with
`assignment to entry in nil map`. The codebase already had this right in one place
(`make(JSONMap)` in `ws_endpoint.kuki`); the alias form only bites when it is introduced.

**`dereference` copies — it does not mutate through the reference.**
`p := dereference pRef` copies the struct, so `p.SetName(...)` mutates the copy and the change is
silently lost. To mutate a `reference T`, call the method on the reference directly
(`pRef.SetName(...)`); Kukicha auto-dereferences for field access and method calls.

**`is` narrowing does not apply to concrete map types.**
`if v is map of string to any as m` is rejected ("'is' requires a variant enum or interface-typed
value"). Narrow to a map only via a typed local (`m := state["players"]` where the map's value
type is known), and read scalars with `cast.ToIntOr` / a typed helper rather than an `is` check.

**`for i from 0 to n` is exclusive** (`for i from 0 through n` is inclusive), unlike Go's
`for i := 0; i < n; i++` which is also exclusive. `CreateGame(n)` therefore creates exactly `n`
players.

**JSON numbers are `float64`.** Any validation of a decoded message must accept float64 — this
is the root cause of §2.12 and it will bite the new agent API too.

### B.2 Go-side traps

**Go map iteration order is random.** Any code that iterates a map and assigns an index, a
colour, a seat or an order is non-deterministic. `lobby.players`, `gs.players` and
`gs.tokens` are all maps; sort before assigning anything order-dependent.
