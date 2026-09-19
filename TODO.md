# Modernization TODO — Race to the Crystal (Kukicha v0.85.1)

Scan date: 2026-09-19  
Compiler version: v0.85.2  
Pin status: `kukicha.org/kukicha/stdlib v0.85.2` (`go.mod` current)  
Status: `[ ]` pending · `[~]` in progress · `[x]` done · `[/]` blocked

> **Completed 2026-09-19:** Phases 1–6 verified with `kukicha fmt --check .`, `kukicha check ./...` (0 errors, 0 warnings), `kukicha build ./...`, `go test ./...`, binary builds, and clean git state.
> Phase 3.2 note: `p.String()` on enum values from other packages is not resolved by the semantic pass — use `"{p}"` interpolation at call sites.

This plan outlines modernization steps to update `race-to-the-crystal` to modern Kukicha idioms and conventions.

---

## Phase 1 — Zero-Risk Mechanical Syntax Modernization

Mechanical replacements that eliminate legacy Go-isms, improve code readability, and satisfy Kukicha conventions.

### 1.1 Emptiness Checks (`len(...)` -> `is empty` / `isnt empty`)

Replace `len(collection) equals 0` / `len(collection) == 0` with `collection is empty`, and `len(collection) > 0` with `collection isnt empty`. In Kukicha, `is empty` and `isnt empty` work directly on strings, lists, maps, and channels.

- [x] `game/board.kuki:18`**:
  ```kukicha
  // Before
  return len(c.occupants) > 0
  // After
  return c.occupants isnt empty
  ```
- [x] `game/crystal.kuki:78`**:
  ```kukicha
  // Before
  return c.holding_player_id equals "" and len(c.holding_token_ids) > 0
  // After
  return c.holding_player_id is empty and c.holding_token_ids isnt empty
  ```
- [x] `game/ai_observation.kuki`**:
  - Line 77: `if len(lines) equals 0` -> `if lines is empty`
  - Line 126: `if len(gs.generators) > 0` -> `if gs.generators isnt empty`
  - Line 155: `if len(deployed) > 0` -> `if deployed isnt empty`
  - Line 225: `if len(holders) > 0` -> `if holders isnt empty`
  - Line 383: `if len(valid_moves) > 0` -> `if valid_moves isnt empty`
  - Line 407: `if len(available) > 0` -> `if available isnt empty`
  - Line 487: `if len(holders) > 0` -> `if holders isnt empty`
  - Line 538: `if len(actions_data.Actions) > 0` -> `if actions_data.Actions isnt empty`
- [x] `game/ai_strategy.kuki`**:
  - Line 68: `if len(actions) equals 0` -> `if actions is empty`
  - Lines 87, 91, 95, 102, 106, 110: `len(attacks) > 0` / `len(moves) > 0` / `len(deploys) > 0` -> `... isnt empty`
  - Line 194: `if len(chosen.Positions) equals 0` -> `if chosen.Positions is empty`
- [x] `game/game_state.kuki`**:
  - Line 288: `if len(active) equals 0` -> `if active is empty`
  - Line 315: `if len(gs.players) equals 0` -> `if gs.players is empty`
- [x] `game/movement.kuki`**:
  - Lines 44 & 100: `for len(queue) > 0` -> `for queue isnt empty`
- [x] `server/` packages**:
  - `server/ai_spawner.kuki:27`: `if len(strategies) equals 0` -> `if strategies is empty`
  - `server/http_handler.kuki:449`: `if len(parts) > 0` -> `if parts isnt empty`
  - `server/lobby.kuki:121`: `len(l.players) > 0` -> `l.players isnt empty`
  - `server/lobby.kuki:227`: `len(dereference lobby.players) equals 0` -> `lobby.players is empty`
- [x] `client/` packages**:
  - `client/desktop/renderer_2d.kuki:172, 179`: `len(app.message) > 0` -> `app.message isnt empty`; `len(gs.winner) > 0` -> `gs.winner isnt empty`
  - `client/desktop/main.kuki:224, 280`: `len(winner_id) > 0` -> `winner_id isnt empty`; `len(actions) equals 0` -> `actions is empty`
  - `client/ai/http_ai_client.kuki:401`: `if len(actions_typed) equals 0` -> `if actions_typed is empty`
  - `client/ai/ai_client.kuki:63, 98, 112, 116, 165, 198, 210, 214`: Update `len(...)` checks on `state`, `payload`, `actions`, `result`
- [x] `shared/errs/errors.kuki`**:
  - Lines 96, 108, 120, 132: `if len(e.context) > 0` / `len(e.details) > 0` -> `... isnt empty`
- [x] `learn/` packages**:
  - `learn/examples/05-decisions/main.kuki:20`: `if len(mine) equals 0` -> `if mine is empty`
  - `learn/examples/09-strategist/main.kuki:52`: `if len(api.MyTokens()) equals 0` -> `if api.MyTokens() is empty`
  - `learn/simulation.kuki:113`: `if len(actions) equals 0` -> `if actions is empty`

### 1.2 Nil/Empty Equality (`equals empty` -> `is empty`)

Replace `if x equals empty` with `if x is empty`. In Kukicha, `is empty` is the idiomatic syntax for checking optional/reference emptiness.

- [x] `game/api.kuki`**:
  - Lines 14, 19, 25, 30, 35, 40, 45, 52, 58, 65, 71, 76, 81, 89: `if api.game_state equals empty` -> `if api.game_state is empty`
- [x] `game/game_state.kuki`**:
  - Lines 89, 107, 121: `if p_ref equals empty` -> `if p_ref is empty`
  - Lines 146, 171, 183: `if t_ref equals empty` -> `if t_ref is empty`
  - Lines 195, 198: `if a_ref equals empty` / `if d_ref equals empty` -> `... is empty`
- [x] `server/ws_endpoint.kuki`**:
  - Lines 95, 124, 170, 210, 231, 255, 282, 317, 337: `if client equals empty` -> `if client is empty`
  - Lines 152, 185, 262: `if lobby equals empty` -> `if lobby is empty`
  - Lines 269: `if start_result equals empty` -> `if start_result is empty`
  - Lines 289, 322: `if session equals empty` -> `if session is empty`
- [x] `server/auth.kuki:89`**:
  - `if payload equals empty` -> `if payload is empty`
- [x] `server/game_coordinator.kuki:128`**:
  - `if session equals empty` -> `if session is empty`
- [x] `server/http_handler.kuki`**:
  - Lines 75, 323, 402: `if lobby equals empty` -> `if lobby is empty`
  - Lines 86, 420: `if join_result equals empty` / `if start_result equals empty` -> `... is empty`
  - Lines 117, 220, 245, 349, 363, 396: `if payload equals empty` -> `if payload is empty`
  - Lines 180, 224, 249: `if session equals empty` -> `if session is empty`
- [x] `server/lobby.kuki`**:
  - Lines 213, 224, 233, 239, 248, 255: `if lobby equals empty` -> `if lobby is empty`
- [x] `client/` & `learn/`**:
  - `client/desktop/main.kuki:198, 256, 283, 305`: `if gs equals empty` / `if chosen_ref equals empty` -> `... is empty`
  - `client/desktop/input_handler.kuki:45, 95, 108, 121, 131, 146`: `if gs equals empty` / `if app.real_api equals empty` -> `... is empty`
  - `client/ai/http_ai_client.kuki:222, 367, 378, 389, 404`: `... equals empty` -> `... is empty`
  - `learn/simulation.kuki:99, 117` & `learn/learn_api.kuki:98`: `... equals empty` -> `... is empty`

### 1.3 Superfluous `dereference` Cleanup

Kukicha automatically dereferences reference types (`reference T`) for field access and method calls. `dereference` is only needed when copying value semantics or obtaining a non-pointer value.

- [x] Method calls on references**:
  - `game/mystery_square.kuki:39`: `if not dereference cell.is_occupied()` -> `if not cell.is_occupied()`
  - `game/ai_observation.kuki:405`: `if not dereference cell.is_occupied()` -> `if not cell.is_occupied()`
  - `server/lobby.kuki:241`: `if not dereference lobby.can_start()` -> `if not lobby.can_start()`
  - `server/websocket_handler.kuki:99, 111`: `dereference client.conn.WriteMessage(...)` -> `client.conn.WriteMessage(...)`
  - `game/ai_strategy.kuki:244`: `if dereference tok.movement_range() >= 2` -> `if tok.movement_range() >= 2`
  - `learn/simulation.kuki:101`: `return dereference p_ref.Name()` -> `return p_ref.Name()`
- [x] Field access on references**:
  - `server/lobby.kuki:215`: `if dereference lobby.status isnt GameStatus.WAITING` -> `if lobby.status isnt GameStatus.WAITING`
  - `game/api.kuki:78`: `return dereference api.game_state.current_turn_player_id equals api.player_id` -> `return api.game_state.current_turn_player_id equals api.player_id`
  - `game/board.kuki:23`: `dereference tok.player_id` -> `tok.player_id`
- [x] Assertions in tests**:
  - `game/board_test.kuki:57`: `test.AssertEqual(t, dereference cell.position, types.Pos(5, 7))` -> `test.AssertEqual(t, cell.position, types.Pos(5, 7))`
  - `game/game_state_test.kuki:63-64`: `test.AssertTrue(t, dereference tok.is_deployed)` -> `test.AssertTrue(t, tok.is_deployed)`

### 1.4 Code Formatting

- [x] Run `kukicha fmt -w server/ws_endpoint.kuki` (or `make format`) to fix formatting drift flagged by `kukicha fmt --check .`.

---

## Phase 2 — Map Access & Nullability Modernization

### 2.1 Direct Map Lookups for Reference Types

In Kukicha, indexing a map whose value is a reference type (`map of K to reference T`) evaluates to `empty` (Go `nil`) when the key is absent. The 5-line comma-ok pattern is unnecessary boilerplate.

- [x] `game/game_state.kuki:72-76` (`GetPlayer`)**:
  ```kukicha
  // Before
  func GetPlayer on gs: reference GameState(player_id: types.PlayerID) optional reference Player
      p, ok := gs.players[player_id]
      if ok
          return p
      return empty

  // After
  func GetPlayer on gs: reference GameState(player_id: types.PlayerID) optional reference Player
      return gs.players[player_id]
  ```
- [x] `game/game_state.kuki:81-85` (`GetToken`)**:
  ```kukicha
  // Before
  func GetToken on gs: reference GameState(token_id: types.TokenID) optional reference Token
      t, ok := gs.tokens[token_id]
      if ok
          return t
      return empty

  // After
  func GetToken on gs: reference GameState(token_id: types.TokenID) optional reference Token
      return gs.tokens[token_id]
  ```
- [x] `server/game_coordinator.kuki:114-118` (`get_session`)**:
  ```kukicha
  // Before
  func get_session on gc: reference GameCoordinator(game_id: string) optional reference GameSession
      session, ok := gc.active_games[game_id]
      if ok
          return session
      return empty

  // After
  func get_session on gc: reference GameCoordinator(game_id: string) optional reference GameSession
      return gc.active_games[game_id]
  ```
- [x] `server/lobby.kuki:205-209` (`get_lobby`)**:
  ```kukicha
  // Before
  func get_lobby on lm: reference LobbyManager(game_id: string) optional reference GameLobby
      lobby, ok := lm.lobbies[game_id]
      if ok
          return lobby
      return empty

  // After
  func get_lobby on lm: reference LobbyManager(game_id: string) optional reference GameLobby
      return lm.lobbies[game_id]
  ```

### 2.2 Adopt `stdlib/maps` for JSON Payloads & Dictionaries

- [x] **`server/http_handler.kuki:49-65`**:
  Replace 17 lines of comma-ok and type assertion with `maps.StringOr`:
  ```kukicha
  // Before
  player_name_val, has_pn := body["player_name"]
  if not has_pn
      return APIResponse{success: false, message: "missing player_name", data: empty map of string to any}
  player_name := ""
  if player_name_val is string as pn
      player_name = pn
  if player_name equals ""
      return APIResponse{success: false, message: "invalid player_name", data: empty map of string to any}

  // After
  player_name := maps.StringOr(body, "player_name", "")
  if player_name is empty
      return APIResponse{success: false, message: "missing or invalid player_name", data: empty map of string to any}
  ```
- [x] **`server/http_handler.kuki:136-151`**:
  Replace 16 lines of action type extraction with `maps.StringOr`:
  ```kukicha
  // Before
  action_type_val, has_at := body["type"]
  if not has_at ...
  type_str := ""
  if action_type_val is string as ts ...
  if type_str equals "" ...

  // After
  type_str := maps.StringOr(body, "type", "")
  if type_str is empty
      return APIResponse{success: false, message: "missing or invalid action type", data: empty map of string to any}
  ```
- [x] **`server/game_coordinator.kuki:106-111`**:
  ```kukicha
  // Before
  pid_val, has_id := info["player_id"]
  if has_id
      if pid_val is string as pid_str
          if pid_str isnt ""
              gc.player_to_game[pid_str] = game_id

  // After
  pid_str := maps.StringOr(info, "player_id", "")
  if pid_str isnt empty
      gc.player_to_game[pid_str] = game_id
  ```

### 2.3 Map Membership (`in` / `not in`)

- [x] `game/crystal_effects.kuki:99-100`**:
  ```kukicha
  // Before
  _, occ := occupied[pos]
  if not occ

  // After
  if pos not in occupied
  ```
- [x] `server/rate_limiter.kuki:95-118`**:
  Simplify `get_ip_counter`, `get_action_bucket`, and `get_game_creation_counter`:
  ```kukicha
  // Before
  counter, ok := rl.ip_connections[ip]
  if ok
      return counter
  new_counter := NewSlidingWindowCounter(MAX_CONNECTIONS_PER_IP, CONNECTION_WINDOW_SECONDS)
  rl.ip_connections[ip] = reference of new_counter
  return rl.ip_connections[ip]

  // After
  counter := rl.ip_connections[ip]
  if counter isnt empty
      return counter
  new_counter := reference of NewSlidingWindowCounter(MAX_CONNECTIONS_PER_IP, CONNECTION_WINDOW_SECONDS)
  rl.ip_connections[ip] = new_counter
  return new_counter
  ```

---

## Phase 3 — Enum Modernization

### 3.1 Drop Redundant `*Name()` String Helpers

In `shared/enums/enums.kuki`, the compiler automatically generates a `.String() string` method on enums. The hand-rolled `GamePhaseName`, `TurnPhaseName`, and `MysteryEffectName` switch functions duplicate compiler-generated behavior.

- [x] `shared/enums/enums.kuki`**:
  - Remove `GamePhaseName(p: GamePhase) string` (lines 15-24)
  - Remove `TurnPhaseName(p: TurnPhase) string` (lines 31-40)
  - Remove `MysteryEffectName(e: MysteryEffect) string` (lines 65-72)
- [x] Update Callers**:
  Replace `enums.GamePhaseName(p)` with `p.String()` or `{p}`, and `enums.TurnPhaseName(p)` with `p.String()` or `{p}`:
  - `game/ai_actions.kuki:287, 414`
  - `game/ai_observation.kuki:352`
  - `game/api.kuki:85, 86`
  - `game/game_state.kuki:412, 417`
  - `game/state_serializer.kuki:141, 142`
  - `client/desktop/main.kuki:210, 211`

### 3.2 Enum Case Names & Dot Syntax

- [x] Dot syntax in tests and code**:
  In `game/board_test.kuki:11`, `game/game_state_test.kuki:14, 16, 69`, the tests reference Go constant names `enums.CellTypeNORMAL`, `enums.GamePhaseSETUP`, `enums.GamePhasePLAYING`.
  Update to Kukicha enum variant syntax: `enums.CellType.NORMAL`, `enums.GamePhase.SETUP`, `enums.GamePhase.PLAYING`.
- [/] **Consider PascalCase for enum variants** (deferred — would change the compiler-generated `.String()` output and serialized wire values; coordinate with the web frontend first):
  Modern Kukicha style uses PascalCase for enum cases (e.g. `GamePhase.Setup`, `GamePhase.Playing`, `GamePhase.Ended`). If updating case names, coordinate across `shared/enums/enums.kuki` and callers.

---

## Phase 4 — Address Compiler Warnings

Running `kukicha check ./...` reports 4 warnings:
```
── WARNING ───── game/board.kuki:117:24 ──
[semantic/potential-panic] random.Int may panic: "when max - min overflows int"
117 │             x := random.Int(q.x_min, q.x_max + 1)

── WARNING ───── game/board.kuki:118:24 ──
[semantic/potential-panic] random.Int may panic: "when max - min overflows int"
118 │             y := random.Int(q.y_min, q.y_max + 1)

── WARNING ───── game/crystal_effects.kuki:95:24 ──
[semantic/potential-panic] random.Int may panic: "when max - min overflows int"
95 │             x := random.Int(0, bw)

── WARNING ───── game/crystal_effects.kuki:96:24 ──
[semantic/potential-panic] random.Int may panic: "when max - min overflows int"
96 │             y := random.Int(0, bh)
```

- [x] **`game/board.kuki:117-118`**:
  `q.x_max + 1` and `q.y_max + 1` are dynamically computed. Validate `q.x_max >= q.x_min` before calling or extract a small local helper:
  ```kukicha
  func safeRandomRange(min_val: int, max_val: int) int
      if min_val >= max_val
          return min_val
      return random.Int(min_val, max_val)
  ```
- [x] `game/crystal_effects.kuki:95-96`**:
  Ensure `bw > 0` and `bh > 0` before the loop, or use the checked random helper.

---

## Phase 5 — Identifier Casing & Idiomatic Polish (Incremental)

`race-to-the-crystal` uses Python-style `snake_case` heavily for function names, struct fields, and methods:
- Functions: `add_player`, `remove_player`, `create_generators`, `get_cell`, `is_valid_position`
- Fields: `player_id`, `turn_phase`, `current_turn_player_id`, `_next_token_id`

Modern Kukicha follows Go conventions: camelCase for unexported identifiers, PascalCase for exported identifiers.

- [x] Package-internal unexported methods in `game/`**:
  Gradually migrate unexported methods to camelCase (e.g. `addPlayer`, `removePlayer`, `createGenerators`, `isValidPosition`).
- [x] Exported APIs**:
  Maintain consistency with existing exported public APIs (`GetPlayer`, `GetToken`, `NewBoard`) while updating any internal callers.

---

## Phase 6 — Verification Gates

After completing each phase, run the verification commands to ensure zero regressions:

```bash
# 1. Format check
kukicha fmt --check .

# 2. Type-check all packages
kukicha check ./...

# 3. Transpile and build all packages
kukicha build ./...

# 4. Run test suite
go test ./...

# 5. Build client and server binaries
make desktop
make web-server
make ai-client

# 6. Verify clean git state (no stray .go artifacts or uncommitted build binaries)
make clean
git status
```
