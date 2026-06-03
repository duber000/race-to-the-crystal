# Race to the Crystal: Python → Kukicha Conversion Plan

## Overview

Convert the Python codebase (~35,630 LOC across 115 files) to [Kukicha](https://kukicha.dev), a near-superset of Go. The JS web client (Babylon.js) stays as-is.

## Current Status (2026-06-01)

| Phase | Description | Status | LOC |
|-------|-------------|--------|-----|
| Phase 0 | Project setup (go.mod, Makefile, kukicha init) | **COMPLETE** | — |
| Phase 1 | `shared/` (types, enums, constants, errors) | **COMPLETE** | 166 LOC |
| Phase 2 | `game/` (game logic, 16 files) | **COMPLETE** | 2,756 LOC |
| Phase 3 | `server/` (10 files) | **COMPLETE** | 1,919 LOC |
| Phase 4 | `client/ai_client` (poll + SSE) | **COMPLETE** | ~500 LOC |
| Phase 5 | `client/desktop` (ebitengine) | **COMPLETE** | ~500 LOC |
| Phase 6 | `web_server/` | **NOT STARTED** | — |
| Phase 7 | Tests (`*_test.kuki`) | **NOT STARTED** | — |

**What works:** All 9 packages pass `kukicha check ./...`. `client/desktop/` builds to an ELF binary via `make desktop`. Server and AI client continue to work as before. Kukicha v0.48.1.

**Phase 5 completed (2026-06-02):** Desktop 2D client using ebitengine directly (not `github.com/kukichalang/game`, which is WASM-only with `//go:build js`). 

**Key architectural decisions during Phase 5:**
1. **Direct ebitengine, not `github.com/kukichalang/game`** — The game package has `//go:build js` constraint making it WASM-only. Desktop build uses ebitengine directly via Go interop (adapter.go + desktop_main.go).
2. **Go interop for ebitengine.Game interface** — Kukicha cannot implement the `ebiten.Game` interface (its method definition syntax `func Update on a: reference Foo() error` fails to parse empty `()` parameter lists — a Kukicha parser bug in v0.48.1). A Go adapter file (`adapter.go`) implements `Update()`, `Draw()`, `Layout()` and delegates to Kukicha functions `updateFrame()`, `drawFrame()`, `layoutScreen()`.
3. **CGO build requirements** — ebitengine needs X11 development headers. On systems using Homebrew, set `CGO_CFLAGS` and `CGO_LDFLAGS` via `pkg-config`. The `make desktop` target handles this automatically.

**Kukicha compiler bug found during Phase 5:**
1. **Empty `()` on `on`-style method definitions fails to parse** — `func Update on a: reference Adapter() error` produces `expected '(' after 'func'`. The parser expects an explicit parameter between the receiver and the return type. All existing project methods with `on` syntax have at least one parameter. Workaround: use regular Kukicha functions called from a Go adapter.
1. **`reference of s.game_state.EndTurn()` workaround** at `server/game_coordinator.kuki:66` was invalid Go (calling `new()` on a void function result). Removed the workaround — pointer-receiver method calls on value-typed fields work correctly in Go.
2. **Stale `current_turn_player_id`** in `get_state_dict()` was caused by `NewGameSession` returning a `GameSession` **by value**. The api_map was populated with pointers to the local `session` inside `NewGameSession`, but the returned value was a **copy** — so mutations via `api.game_state.EndTurn()` modified the original (abandoned) struct, while reads from `session.game_state` saw a different copy. Fixed by changing `NewGameSession` to return `reference GameSession`.

**Kukicha stdlib issues found during Phase 4 (besides the bugs above):**
- `stdlib/cast` needed for parsing JSON-decoded values (Go's `encoding/json` produces `[]interface{}`, not `[][]int`, and `interface{}` for nullable types — `.(int)`, `.(string)`, `.(bool)` panic on type mismatch).
- `stdlib/cast.SmartInt` / `SmartString` are needed at every JSON boundary.
- `if state == empty` on a `map[string]any` is always false (returns empty map, not nil). Use `len(state) == 0` or `KUKICHA_LINT_TYPED_NIL_EMPTY=0`.
- `onerr` cannot be used in `and`/`or` boolean expressions. Must assign first, then check.
- **v0.48.0 enum change**: enum values without explicit integer/string backing are now generated as **variant enums** (interface + empty struct cases) instead of integer constants. To use the original integer-backed style, add `= 0`, `= 1`, etc. to each case, then use `EnumName.VALUE` for qualified access.
- **v0.48.0 stdlib imports**: must use bare `stdlib/<pkg>` form (not `github.com/kukichalang/kukicha/stdlib/<pkg>`) — the old GitHub form no longer resolves via the stdlib registry.

**Kukicha compiler bugs — all fixed:**
1. ~~#241 `dereference x.field` transpiles to `*x.field`~~ — **Fixed in v0.25.3.**
2. ~~#250 `delete dereference m.field[key]`~~ — **Fixed in v0.26.0.**
3. ~~#251 `nullable reference func(...)` generates uncallable `*func(...)` in Go~~ — **Fixed in v0.26.2.**
4. ~~#252 Value-returning constructor with `reference of s.field` inside creates dangling pointer when caller stores the value~~ — **Worked around in code** (changed `NewGameSession` to return `reference GameSession`).

**Kukicha stdlib issues found during Phase 3:**
- `signal.OnInterrupt()` spawns a goroutine and returns immediately — doesn't block main goroutine. Fixed in server by using a channel-based blocking pattern.

**What's next:** Phase 4 (AI client). Unit tests can be written in parallel (Phase 7).

### Key Architectural Decisions

1. **Drop TCP entirely** — All clients communicate via HTTP/WebSocket only. The `network/` protocol layer and TCP server are **removed**, not converted.
2. **Desktop 2D via ebitengine directly** — `github.com/kukichalang/game` is WASM-only (`//go:build js`). Use ebitengine via Go interop. Drop all 3D Python code. Rebuild `renderer_2d.kuki` + menus + input handling.
3. **File GitHub issues** for any Kukicha/stdlib bugs found during conversion — with minimal reproducers.

### What Gets Dropped (not converted)

| File | LOC | Reason |
|------|-----|--------|
| `client/board_3d.py` | 780 | 3D OpenGL, replaced by ebitengine 2D |
| `client/token_3d.py` | 206 | 3D model |
| `client/phantom_token_3d.py` | 197 | 3D model |
| `client/camera_3d.py` | 312 | 3D camera |
| `client/camera_controller.py` | 486 | 3D controls |
| `client/renderer_3d.py` | 429 | 3D renderer |
| `client/crystal_effect_animator.py` | 320 | Arcade-specific animations |
| `client/game_window.py` | 695 | Arcade window |
| `client/game_action_handler.py` | 346 | Arcade-specific dispatch |
| `client/client_main.py` | 123 | Arcade entry point |
| `client/menu_main.py` | 456 | Arcade menus |
| `client/input_handler.py` | 767 | Arcade input |
| `client/audio_manager.py` | 555 | Arcade audio |
| `client/music_generator.py` | 588 | Procedural music |
| `client/sound_effects.py` | 291 | Arcade sound |
| `client/crystal_effect_animator.py` | 320 | Arcade animations |
| `client/deployment_menu_controller.py` | 381 | Arcade UI |
| `client/network_client.py` | 548 | TCP client — removed |
| `client/ui/` (9 files) | ~3,600 | Arcade UI — rebuilt for ebitengine |
| `client/sprites/` (3 files) | ~737 | Arcade sprites — rebuilt for ebitengine |
| `client/shaders/` (2 GLSL) | N/A | OpenGL shaders |
| `network/connection.py` | 332 | TCP removed |
| `network/protocol.py` | 445 | TCP removed |
| `network/messages.py` | 125 | TCP removed |
| `server/game_server.py` | 1,113 | TCP listener — replace with stdlib/http |
| `server/message_router.py` | 52 | replaced by http route handlers |
| `server/http_handler.py` | 534 | aiohttp — replace with stdlib/http |
| `server/websocket_handler.py` | 564 | rewrite using gorilla/websocket |
| `server/mercure_publisher.py` | 327 | httpx — replace with stdlib/fetch |
| `server/rate_limiter.py` | 280 | convert |
| `server/action_validation.py` | 79 | convert |
| `web_server/main.py` | 351 | replace with Kukicha stdlib/http |
| `web_server/mercure_publisher.py` | 171 | replace with Kukicha stdlib |
| `tests/test_*` (30 files) | 9,343 | all rewritten as `*_test.kuki` |

### What Gets Preserved (unchanged)

| Path | LOC | Reason |
|------|-----|--------|
| `web_server/static/` (29 JS files) | ~10,457 | Babylon.js frontend — works with Kukicha HTTP backend |

---

## New File Structure

```
race-to-the-crystal/
├── shared/
│   ├── types/
│   │   └── types.kuki
│   ├── enums/
│   │   └── enums.kuki
│   ├── constants/
│   │   └── constants.kuki
│   └── errs/
│       └── errors.kuki
├── game/
│   ├── token.kuki
│   ├── player.kuki
│   ├── board.kuki
│   ├── movement.kuki
│   ├── combat.kuki
│   ├── generator.kuki
│   ├── crystal.kuki
│   ├── crystal_effects.kuki
│   ├── mystery_square.kuki
│   ├── capture_utils.kuki
│   ├── game_state.kuki
│   ├── schemas.kuki
│   ├── ai_actions.kuki
│   ├── ai_observation.kuki
│   ├── ai_strategy.kuki
│   └── api.kuki
├── server/
│   ├── auth.kuki
│   ├── lobby.kuki
│   ├── game_coordinator.kuki
│   ├── http_handler.kuki
│   ├── websocket_handler.kuki
│   ├── mercure_publisher.kuki
│   ├── action_validation.kuki
│   ├── rate_limiter.kuki
│   ├── ai_spawner.kuki
│   └── server_main.kuki
├── client/
│   ├── ai_client.kuki           # HTTP+SSE using stdlib/fetch
│   ├── http_ai_client.kuki      # HTTP+SSE (simplified)
│   └── desktop/
│       ├── main.kuki
│       ├── renderer_2d.kuki
│       ├── input_handler.kuki
│       └── ui/
│           ├── main_menu.kuki
│           ├── lobby_view.kuki
│           ├── game_view.kuki
│           └── victory_view.kuki
├── web_server/
│   ├── main.kuki
│   └── static/                  # unchanged Babylon.js files
├── tests/
│   ├── test_shared.kuki
│   ├── test_token.kuki
│   ├── test_player.kuki
│   ├── test_board.kuki
│   ├── test_movement.kuki
│   ├── test_combat.kuki
│   ├── test_generator.kuki
│   ├── test_crystal.kuki
│   ├── test_crystal_effects.kuki
│   ├── test_mystery_square.kuki
│   ├── test_game_state.kuki
│   ├── test_schemas.kuki
│   ├── test_ai_actions.kuki
│   ├── test_ai_observation.kuki
│   ├── test_ai_strategy.kuki
│   ├── test_api.kuki
│   ├── test_lobby.kuki
│   ├── test_http_api.kuki
│   ├── test_sse.kuki
│   ├── test_auth.kuki
│   ├── test_rate_limiter.kuki
│   └── test_security.kuki
├── .kukicha/stdlib/             # compiler stdlib (bundled)
├── go.mod
└── Makefile
```

### Petiole (Package) Layout

| Petiole | Files | Imports from |
|---------|-------|-------------|
| `types` | `shared/types/types.kuki` | nothing |
| `enums` | `shared/enums/enums.kuki` | nothing |
| `constants` | `shared/constants/constants.kuki` | nothing |
| `errs` | `shared/errs/errors.kuki` | nothing |
| `game` | `token.kuki`–`api.kuki` (17 files) | `shared/*` |
| `server` | `auth.kuki`–`server_main.kuki` (~10 files) | `shared`, `game`, `stdlib/*` |
| `client` | `ai_client.kuki`, `http_ai_client.kuki` (standalone) | `shared`, `game`, `stdlib/fetch` |
| `client/desktop` | `main.kuki`–`ui/victory_view.kuki` (~7 files) | `shared`, `game`, `github.com/kukichalang/game` |
| `web_server` | `main.kuki` | `stdlib/http`, `stdlib/fetch` |
| `*_test` | `test_*.kuki` (mirrors above) | `stdlib/test`, its petiole |

---

## Phases

### Phase 0: Project Setup (1 day)

**Goal:** Working Kukicha project with Makefile, go.mod, and the build pipeline compiling.

**Tasks:**
1. Initialize a new `kukicha init` in a separate Go module path. The repo root already has `go.mod` for the current stdlib. We need to decide whether to reuse or re-init.
2. Create `Makefile` with targets:
   - `check` → `kukicha check ./...`
   - `build` → `kukicha build ./...`
   - `test` → `kukicha build ./... && go test ./...`
   - `format` → `kukicha fmt -w *.kuki **/*.kuki`
3. Set up Kukicha petiole structure for `shared`, `game`, `server`, `client`, `web_server`
4. `go install github.com/kukichalang/game` (or `go get`) and verify it compiles
5. Set up `_test.kuki` convention in Makefile

**Stdlib usage:** `stdlib/cli` for Makefile commands (optional), `stdlib/files`, `stdlib/shell`

**Risk:** `kukicha init` module path choice. The repo root already has `go.mod` (`module race-to-the-crystal`). We should `kukicha init` using `github.com/tluker/race-to-the-crystal` or keep the current module path. **Decision:** reuse `race-to-the-crystal` module path.

---

### Phase 1: `shared/` (1 day)

**Goal:** Pure data definitions — types, enums, constants, errors.

**Tasks:**
1. `types.kuki` — `type TokenID int`, `type PlayerID string`, `type Position [2]int`
2. `enums.kuki` — Kukicha `enum` for all Python `Enum`:
   - `CellType` (NORMAL, GENERATOR, CRYSTAL, MYSTERY, START)
   - `GamePhase` (SETUP, PLAYING, ENDED)
   - `TurnPhase` (MOVEMENT, ACTION, END_TURN)
   - `PlayerColor` (CYAN=0, MAGENTA=1, YELLOW=2, GREEN=3)
   - `MysteryEffect` (HEAL, TELEPORT)
   - `CombatResult` (HIT, KILLED, INVALID)
   - `CrystalEffect` (FOG_OF_WAR, PHANTOM_ENEMIES, DAMAGE_BOOST, SPEED_BOOST)
3. `constants.kuki` — All `const` values from `shared/constants.py`:
   - `BOARD_WIDTH = 24`, `BOARD_HEIGHT = 24`
   - `TOKEN_HEALTH_VALUES = list of int{10, 8, 6, 4}`
   - `TOKENS_PER_HEALTH_VALUE = 5`, `TOKENS_PER_PLAYER = 20`
   - `TOKEN_MOVEMENT_RANGE = 2`
   - `COMBAT_DAMAGE_MULTIPLIER = 0.5`
   - `GENERATOR_CAPTURE_TOKENS_REQUIRED = 2`, `GENERATOR_CAPTURE_TURNS_REQUIRED = 2`, `GENERATOR_TOKEN_REDUCTION = 2`
   - `CRYSTAL_BASE_TOKENS_REQUIRED = 12`, `CRYSTAL_CAPTURE_TURNS_REQUIRED = 3`
   - `CRYSTAL_EFFECT_INITIAL_DURATION = 4`, `CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR = 1`
   - `PHANTOM_ENEMIES_COUNT = 3`, `CRYSTAL_RANDOM_EFFECT_ROUND_INTERVAL = 5`
   - `CRYSTAL_DAMAGE_BOOST_MULTIPLIER = 1.5`, `CRYSTAL_SPEED_BOOST_AMOUNT = 1`
   - `MYSTERY_SQUARES_PER_QUADRANT = 2`
   - `MIN_PLAYERS = 2`, `MAX_PLAYERS = 4`
   - `TURN_TIMEOUT_SECONDS = 30`
   - `MYSTERY_PLACEMENT_MAX_ATTEMPTS = 100`
   - `MYSTERY_PLACEMENT_EDGE_MARGIN = 2`
   - Visual/grid/audio/3D config constants — **only those used by game logic**, drop rendering-only constants
4. `errors.kuki` — Kukicha structs for the four error types:
   - `GameError{action string, reason string, context map of string to any}`
   - `ValidationError{field string, reason string, context map of string to any}`
   - `ActionError{action string, reason string, context map of string to any}`
   - `ServerError{code string, message string, details map of string to any}`
   - `ErrorCode` enum (or const block) with all string codes from `ErrorCode` class:
     - TOKEN_NOT_FOUND, TOKEN_NOT_DEPLOYED, TOKEN_NOT_OWNED, etc.
   - `String()` method on each error producing the `CANNOT {action}: {reason} | {context}` format
   - `to_dict()` for JSON serialization

**Test plan:** Convert `tests/test_schemas.py` first to validate JSON serialization.

**GitHub issue risk:** Low — this is straightforward Kukicha structs, enums, and consts.

---

### Phase 2: `game/` (5 days)

**Goal:** Pure game logic ported method-by-method, preserving all 5,185 LOC of rules.

#### Day 1: Token + Player + Capture Utils

1. `token.kuki`:
   - `type Token struct {id TokenID; player_id PlayerID; health int; max_health int; position Position; is_alive bool; is_deployed bool}`
   - `__post_init__` validations → constructor function `NewToken`
   - `movement_range` — property: `if health <= 6 then 2 else 1`
   - `attack_power` — property: `health // 2`
   - `take_damage(damage int) bool` — 50+ LOC logic: subtract damage, round down to nearest valid health (10,8,6,4), mark dead if <=0
   - `heal_to_full()`, `heal(amount int)`, `move_to(position Position)`
   - `distance_to`, `is_adjacent_to` — pure math
   - `to_dict`, `from_dict` serialization

2. `player.kuki`:
   - `type Player struct {id PlayerID; name string; color PlayerColor; token_ids list of TokenID; is_ready bool; is_active bool; team nullable int}`
   - Methods: `add_token`, `remove_token`, `has_token`, `set_ready`, `eliminate`, `to_dict`, `from_dict`

3. `capture_utils.kuki`:
   - `count_tokens_by_player(tokens list of (TokenID, PlayerID)) map of PlayerID to list of TokenID`
   - `find_dominant_player(counts map of PlayerID to list of TokenID) (nullable PlayerID, int)` — find who has most, return None if tied

**Stdlib usage:** `stdlib/slice` for list operations, `stdlib/maps` for map handling.

#### Day 2: Board + Movement

4. `board.kuki`:
   - `type Cell struct {position Position; cell_type CellType; occupants list of TokenID}` with `is_occupied`, `is_passable`, `has_enemy_tokens`
   - `type Board struct {width int; height int; grid [][]Cell; _generator_positions []Position; _mystery_positions []Position}`
   - `_initialize_grid` → `place_crystal` (center), `place_generators` (4 quadrants), `place_mystery_squares` (random, 2 per quadrant)
   - `get_cell(x, y)`, `is_valid_position`, `add/remove/clear_occupant`
   - `get_starting_position(player_index)`, `get_deployable_positions` (3x3 corner zones via `stdlib/corner_layout`)
   - `to_dict`, `from_dict` (with position cache rebuild)

5. `movement.kuki`:
   - `type MovementSystem struct {}` — all static methods
   - `get_valid_moves` — 8-directional BFS with range limit, occupancy checks, friendly stacking only on GEN/CRYSTAL
   - `is_valid_move`, `find_path` (BFS), `get_distance` (Manhattan), `get_euclidean_distance`, `is_adjacent` (8-dir), `get_adjacent_positions`

**Stdlib usage:** `stdlib/random` for mystery square placement.

#### Day 3: Combat + Generator + Crystal

6. `combat.kuki`:
   - `enum CombatResult {HIT; KILLED; INVALID}`
   - `type CombatOutcome struct {result CombatResult; damage_dealt int; attacker_id TokenID; defender_id TokenID; defender_killed bool}`
   - `type CombatSystem struct {}` — all static methods
   - `can_attack(attacker, defender)`, `resolve_combat(attacker, defender) CombatOutcome`
   - Rules: damage = `attacker.health // 2` (or `CRYSTAL_DAMAGE_BOOST_MULTIPLIER` if crystal effect active)
   - `get_attackable_targets`, `calculate_damage_preview`, `would_kill`

7. `generator.kuki`:
   - `type Generator struct {id int; position Position; capturing_player_id nullable PlayerID; capture_token_ids list of TokenID; turns_held int; is_disabled bool}`
   - `required_tokens`, `required_turns`, `token_reduction_value` properties
   - `update_capture_status(tokens_at_position list of (TokenID, PlayerID)) bool` — check dominant player, increment turns, disable generator if held long enough
   - `type GeneratorManager struct` — `create_generators`, `update_all_generators`, `count_disabled_generators`, `get_generator_at_position`

8. `crystal.kuki`:
   - `type Crystal struct {position Position; holding_player_id nullable PlayerID; holding_token_ids list of TokenID; turns_held int; base_tokens_required int}`
   - `get_tokens_required(disabled_generators int) int` — `max(1, base - disabled * 2)`
   - `update_capture_status(tokens list of (TokenID, PlayerID), disabled_generators int) nullable PlayerID`
   - `type CrystalManager struct` — `create_crystal`, `check_win_condition`, `get_capture_status_message`

**Stdlib usage:** `stdlib/math` for Clamp/Round, `stdlib/sort` for By/ByKey.

#### Day 4: Crystal Effects + Mystery Squares + Game State

9. `crystal_effects.kuki`:
   - `type ActiveEffect struct {effect_type CrystalEffect; turns_remaining int; applied_turn int}` with `reduce_duration`, `is_active`
   - `type PhantomToken struct {phantom_id int; apparent_player_id PlayerID; position Position; apparent_health int}`
   - `type PlayerEffects struct {player_id PlayerID; active_effects list of ActiveEffect; phantom_tokens list of PhantomToken}`
   - `type CrystalEffectsManager struct {player_effects map of PlayerID to reference PlayerEffects; _next_phantom_id int}`
   - Methods: `apply_effect`, `get_effect`, `has_effect`, `reduce_all_durations`, `tick_all_effects`, `generate_phantom_tokens`, `generate_random_effect`

10. `mystery_square.kuki`:
    - `type MysteryEventResult struct {effect MysteryEffect; token_id TokenID; old_position Position; new_position Position; old_health int; new_health int}`
    - `type MysterySquareSystem struct` — `trigger_mystery_event`: 50% heal to full, 50% teleport to deployment area

11. **`game_state.kuki`** (biggest file, ~821 LOC → ~600 LOC):
    - `type GameState struct {board Board; players map of PlayerID to Player; tokens map of TokenID to Token; generators list of Generator; crystal nullable reference Crystal; crystal_effects CrystalEffectsManager; current_turn_player_id nullable PlayerID; turn_number int; phase GamePhase; turn_phase TurnPhase; winner_id nullable PlayerID; _next_token_id int; last_triggered_crystal_effect nullable (PlayerID, CrystalEffect); last_triggered_mystery_event nullable (TokenID, Position, string)}`
    - Player management: `add_player`, `remove_player`, `create_tokens_for_player`, `get_player`
    - Token management: `get_token`, `get_reserve_tokens`, `get_reserve_token_counts`, `deploy_token`, `get_tokens_at_position`, `get_player_tokens`, `move_token`, `remove_token`, `attack_token`
    - Turn management: `start_game`, `end_turn`, `_clear_turn_state`, `_advance_to_next_player`, `_get_active_players`, `_calculate_next_player_index`, `_increment_turn_number`
    - Objective updates: `update_generators_and_crystal`, `end_turn_with_objective_update`, `check_win_condition`, `set_winner`
    - Crystal effects: `apply_crystal_effect`, `generate_phantom_tokens_for_player`, `get_visible_tokens_for_player`, `trigger_random_crystal_effect`
    - Serialization: `to_dict`, `to_json`, `from_dict`, `from_json`, `get_delta`, `_calculate_dict_delta`
    - factory: `create_game(num_players)`
    - Movement range with boosts: `get_token_movement_range`

**Stdlib usage:** `stdlib/json` for to/from JSON, `stdlib/slice` extensively.

#### Day 5: AI Actions + AI Observation + API

12. `ai_actions.kuki`:
    - Variant enum for action types:
      ```
      enum AIAction
          Move
              token_id TokenID
              destination Position
          Attack
              attacker_id TokenID
              defender_id TokenID
          Deploy
              health_value int
              position Position
          EndTurn
      ```
    - `type ValidationResult struct {is_valid bool; message string}`
    - `type ActionResult struct {success bool; message string; data nullable map of string to any}`
    - `type AIActionExecutor struct {}` with:
      - `validate_action`, `execute_action` — switch on AIAction variant
      - `_validate_move`, `_execute_move` — BFS range check, trigger mystery squares
      - `_validate_attack`, `_execute_attack` — adjacency check, delegate to game_state.attack_token
      - `_validate_deploy`, `_execute_deploy` — health value check, reserve check, position in zone
      - `_validate_end_turn`, `_execute_end_turn` — valid in MOVEMENT or ACTION, triggers generator/crystal updates

13. `ai_observation.kuki`:
    - `type AIObserver struct {}` — all static methods returning strings
    - `describe_game_state`, `get_board_map` (ASCII 24x24 grid)
    - `list_available_actions`, `explain_victory_conditions`
    - Template-based text generation (no f-strings needed; Kukicha has `"{expr}"` interpolation)

14. `ai_strategy.kuki`:
    - `enum AIStrategy {Random; Aggressive; Defensive}`
    - `type AIStrategyRunner struct {api GameAPI; player_id PlayerID; strategy AIStrategy}`
    - `get_next_action() nullable AIAction` — strategy-specific action selection

15. `api.kuki`:
    - `type GameAPI struct {game_state reference GameState; player_id PlayerID; executor AIActionExecutor}`
    - Methods: `observe`, `actions`, `actions_with_phase`, `board_map`, `describe`, `victory_conditions`, `move`, `attack`, `deploy`, `end_turn`, `is_my_turn`, `get_phase`, `get_my_tokens`, `get_deployed_tokens`, `get_reserve_counts`

**GitHub issue risk:** Medium.
- **Variant enum exhaustiveness checking** on `AIAction` switch arms — needs to work reliably.
- `ActionResult.data` as `nullable map of string to any` — need nullable reference of map to work.

---

### Phase 3: `server/` (4 days)

**Goal:** HTTP+WebSocket game server using `stdlib/http`.

**Changes from Python architecture:**
- No more TCP server. Drop `game_server.py` entirely.
- Everything is HTTP + WebSocket.
- `stdlib/http` for REST API + static file serving.
- External `gorilla/websocket` for WebSocket support (stdlib has no WS).

#### Day 1: Auth + Rate Limiter + Action Validation

1. `auth.kuki`:
   - `generate_secret_key()` — `stdlib/crypto.RandomToken`
   - `create_player_token(player_id, game_id, secret_key)` — JWT encoding
   - `verify_player_token(token, secret_key)` — JWT decoding
   - `extract_token_from_header`, `validate_token_for_game`
   - **Need:** stdlib/crypto has `SHA256`, `HMAC`, `RandomToken` but JWT encode/decode requires `stdlib/json` for payload + base64url encoding via `stdlib/encoding`. JWT signing is HMAC-SHA256, which stdlib/crypto supports.

2. `rate_limiter.kuki`:
   - Token bucket algorithm
   - `type TokenBucket struct {tokens int; max_tokens int; refill_rate float64; last_refill datetime; capacity int}`
   - `try_consume(count int) bool`
   - Kukicha `stdlib/datetime` for time tracking

3. `action_validation.kuki`:
   - `validate_action_fields(data map of string to any, required list of string) []ValidationError`
   - Type checks for token_id (int), position ([]int with len 2), health_value (4,6,8,10)

#### Day 2: Lobby + Game Coordinator

4. `lobby.kuki`:
   - `type GameLobby struct {id string; name string; max_players int; host_id PlayerID; players map of PlayerID to LobbyPlayer; status GameStatus; created_at datetime}`
   - `type LobbyManager struct {games map of string to reference GameLobby; _next_id int}`
   - Methods: `create_game`, `join_game`, `leave_game`, `set_ready`, `list_games`, `start_game`
   - `validate_player_name` — length/character validation

5. `game_coordinator.kuki`:
   - `type GameSession struct {id string; state reference GameState; players list of SessionPlayer; created_at datetime; ai_players list of AIInfo}`
   - `type GameCoordinator struct {sessions map of string to reference GameSession}`
   - Methods: `create_session`, `get_session`, `remove_session`, `handle_action`, `broadcast_state`, `end_session`

#### Day 3: WebSocket + Mercure Publisher

6. `websocket_handler.kuki`:
   - Wraps `gorilla/websocket` via Go interop (or check if stdlib has been updated to support WS)
   - `type WebSocketClient struct {conn reference WSConn; player_id PlayerID; game_id string}`
   - `type WebSocketManager struct {clients map of PlayerID to reference WebSocketClient}`
   - `handle_upgrade(w http.ResponseWriter, r reference Request)`
   - `handle_message(client, msg)`, `broadcast_to_game(game_id, msg)`

7. `mercure_publisher.kuki`:
   - `type MercureConfig struct {hub_url string; publisher_jwt string; topic_prefix string}` with `from_env`
   - `type MercurePublisher struct {config MercureConfig; enabled bool}`
   - `publish_full_state(game_id, state_dict)`, `publish_state_update(game_id, delta)`
   - `publish_turn_change`, `publish_token_moved`, `publish_combat_result`
   - Uses `stdlib/fetch` for HTTP POST to Mercure hub
   - `_generate_publisher_jwt()` — craft JWT with `mercure.publish: ["*"]` claim

#### Day 4: HTTP Handler + Server Main + AI Spawner

8. `http_handler.kuki`:
   - Routes using `stdlib/http`:
     - `GET /` → serve index.html
     - `GET /api/config` → Mercure config JSON
     - `POST /api/game` → create game
     - `POST /api/game/{id}/join` → join with JWT response
     - `POST /api/game/{id}/action` → execute action (requires JWT)
     - `GET /api/game/{id}/state` → full state dump
     - `GET /api/games` → list games
     - `GET /ws` → WebSocket upgrade
     - `GET /static/*` → serve from web_server/static/
   - `httphelper.SafeHTML` for HTML responses
   - `httphelper.TrustedHosts` middleware for production
   - `httphelper.JSON` for API responses

9. `ai_spawner.kuki`:
   - `type AISpawner struct {...}` — manages goroutines for AI players
   - `spawn_ai(game_session, player_id, strategy)`, `stop_all()`
   - Each AI runs in a goroutine, calls `GameAPI` methods on a timer (with `stdlib/datetime.SleepMilliseconds`)

10. `server_main.kuki`:
    - CLI entry point using `stdlib/cli`:
      ```
      server [--port 8080] [--dev] [--mercure-url "..."]
      ```
    - Sets up logger (`stdlib/log`)
    - Creates HTTP server, registers routes, starts listening

**GitHub issue risk:** High.
- **WebSocket support** — stdlib has no WS. Need `gorilla/websocket` via Go interop.
- **Raw HTTP handler for POST body parsing** — need `httphelper.ReadJSON` which requires `stdlib/json`.
- **`stdlib/http` route path parameters** (`/api/game/{id}/join`) — need to verify stdlib supports path params. If not, use Go's `http.ServeMux` directly.
- **JWT library** — stdlib/crypto may not cover all JWT needs; may need `golang-jwt/jwt` directly.

---

### Phase 4: `client/ai_client` (1 day)

**Goal:** AI players using HTTP+SSE, converting `ai_client.py` and `http_ai_client.py`.

**Status:** COMPLETE. End-to-end verified: two AI bots playing a full game (deploy → end-turn cycles, with state mutations persisting correctly across the shared `GameSession`).

**Bugs fixed during Phase 4 (were not Kukicha compiler bugs but design/usage issues):**
1. **`server/game_coordinator.kuki:66`**: `reference of s.game_state.EndTurn()` was invalid syntax — `reference of` on a void function call produces `new(<void>)` which is a Go compile error. Removed; the call is now `s.game_state.EndTurn()` directly. Pointer-receiver method calls on value-typed fields work correctly in Go (auto-addresses the field, mutations persist).
2. **`server/game_coordinator.kuki:21`**: `NewGameSession(...) GameSession` (value return) was the actual cause of the "stale state" symptom. `initialize_players` called inside `NewGameSession` captured `&session.game_state` for each `GameAPI`, but `return session` returned a copy, so the api_map held pointers to a struct that was about to be discarded. The stored `GameSession` in `gc.active_games` was a different struct, so `session.game_state.EndTurn()` (via api) and `session.game_state.ToDict()` (via the stored session) read/wrote different objects. Fixed by changing the return type to `reference GameSession`. **This was a Kukicha semantic trap**, not a Go trap — the same Go code would have the same bug.

**Files written:**
1. `client/ai_client.kuki` — CLI with `poll` and `sse` subcommands. Auto-ready after create/join. Auto-starts as host when both players are ready. Polls `/state` (or subscribes to SSE), detects turn via `perspective_player_id` vs `current_turn_player_id`, picks action via `gamepkg.ChooseAction(strategy)`, sends via `POST /action`.
2. `client/http_ai_client.kuki` — `Session` type with `NewSession`, `CreateGame`, `JoinGame`, `FillFromResponse`, `FetchState`, `FetchActions`, `SendAction`, `SetReady`, `StartGame`, `ListLobbies`, `GetLobby`, `TryAutoStart`, `IsMyTurn`, `IsGameOver`, `IsGameActive`, `PickAction`, `ConnectSSE`, `ExtractStateFromSSE`.

**Server additions:**
- `HandleGetState` enriches the state dict with `perspective_player_id` and `your_player_id` for the requesting player, so the AI client can match its network id to the game's player id.
- `HandleGetActions` returns the available actions for the current player via `api.ActionsWithPhase()`.

**Stdlib usage:** `stdlib/fetch` for HTTP, `stdlib/cli` for CLI flags, `stdlib/cast` for type-safe JSON parsing, `stdlib/datetime` for polling timing, `stdlib/signal` for graceful shutdown, `stdlib/log` for output.

**GitHub issue risk:** Resolved. `fetch.GetJSON of T from url` works. JSON unmarshaling quirks required `cast.SmartInt`/`SmartString` instead of direct `.()` assertions.

---

### Phase 5: `client/desktop` (5 days)

**Goal:** 2D ebitengine desktop client using `github.com/kukichalang/game`.

**Dependency:** Need to evaluate `github.com/kukichalang/game` API first. It wraps ebitengine for WASM 2D games.

**Tasks:**
1. `go get github.com/kukichalang/game` and explore its API surface:
   - Does it provide window creation, event loop?
   - 2D drawing primitives (lines, rects, circles, text)?
   - Input handling (keyboard, mouse)?
   - Audio?
2. If API is incomplete, supplement with direct ebitengine calls via Go interop.
3. `main.kuki` — entry point, initializes window at 1280×720, creates game loop
4. `renderer_2d.kuki`:
   - Black background (vector arcade aesthetic)
   - Grid lines (gray on black, 32px cell size)
   - Token rendering (colored hexagons or circles with HP labels)
   - Crystal (white/magenta glow), Generators (orange indicators), Mystery (purple/cyan)
   - Text rendering via `stdlib/string` formatting
5. `input_handler.kuki`:
   - Keyboard: arrow keys pan, Q/E rotate, Enter deploy, Esc to menu
   - Mouse: click to select/move/attack
   - Gamepad: optional
6. `ui/main_menu.kuki` — menu with "Local Game", "Network Game", "Settings", "Quit"
7. `ui/lobby_view.kuki` — player list, ready button, game start
8. `ui/game_view.kuki` — main game view with HUD (player info, phase, turn)
9. `ui/victory_view.kuki` — winner display with "Play Again" / "Main Menu"

**Dropped features (from Python client, not rebuilt):**
- 3D mode entirely
- Procedural music generation
- OpenGL shader effects
- Crystal visual effect animations (fog spread, lightning, whirlwind — Python has these but they're cosmetic)
- Sound effects (can add later with ebitengine audio)

**GitHub issue risk:** Very high. This depends entirely on `github.com/kukichalang/game` having a usable 2D drawing API. If the package is minimal or WASM-only, we may need to write the desktop directly against ebitengine.

---

### Phase 6: `web_server/` (1 day)

**Goal:** Kukicha HTTP server serving the Babylon.js static frontend + proxying to game server.

1. `main.kuki`:
   - Serve static files from `web_server/static/`
   - Serve `templates/index.html` at `/`
   - Mercure config endpoint at `/api/config`
   - Pass-through for game actions to the game server (or run embedded)
   - Uses `stdlib/http` for `Serve`, `httphelper.SafeHTML`, `httphelper.JSON`

**Important:** The web_server Python was a separate process from the game server. In the Kukicha version, they can be a single process — embed the static serving and game server in one binary, or keep them separate.

**Preserved (unchanged):**
- All 29 JavaScript files (`10,457 LOC`) in `web_server/static/`
- The Babylon.js 3D game client, which communicates via Mercure SSE + WebSocket

**GitHub issue risk:** Medium. Static file serving in `stdlib/http` needs `Serve` + file handler.

---

### Phase 7: Tests (3 days, parallel)

**Goal:** All 30 pytest files (~9,343 LOC) converted to `*_test.kuki` using `stdlib/test`.

**Pattern for each file:**
```
petiole game_test

import "testing"
import "stdlib/test"
import "../game/game_state" as gs

type TestCase
    name string
    ...

func TestFeature(t: reference testing.T)
    cases := list of TestCase{
        ...
    }
    for tc in cases
        t.Run(tc.name, (t: reference testing.T) =>
            result := doThing()
            test.AssertEqual(t, result, tc.expected)
        )
```

**Key test files to prioritize:**
1. `test_game_state.kuki` — 438 LOC, most critical
2. `test_ai_actions.kuki` — 603 LOC
3. `test_combat.kuki` — 399 LOC
4. `test_board.kuki` — 314 LOC
5. `test_crystal.kuki` — 333 LOC
6. `test_generator.kuki` — 301 LOC
7. `test_movement.kuki` — 285 LOC
8. `test_crystal_effects.kuki` — 995 LOC (biggest test file)
9. `test_api.kuki` — 399 LOC

**Tests to drop (Python-specific):**
- `test_complete_3d_controls.py` (235 LOC) — 3D removed
- `test_game_window_initialization.py` (109 LOC) — Arcade-specific
- `test_sound_effects.py` (147 LOC) — dropped for now
- `test_network_protocol.py` (262 LOC) — TCP removed
- `test_network_multiplayer_integration.py` (318 LOC) — TCP removed

**Tests to add for new patterns:**
- `test_websocket_handler.kuki` — WebSocket upgrade and messaging
- `test_http_handler.kuki` — HTTP REST API
- `test_mercure_publisher.kuki` — SSE publishing

**Stdlib usage:** `stdlib/test` for
`AssertEqual`/`AssertNotEqual`/`AssertTrue`/`AssertFalse`/`AssertNoError`/`AssertError`/`AssertNotEmpty`/`AssertNil`/`AssertNotNil`.

**GitHub issue risk:** Medium. `stdlib/test` must handle all our assertion patterns. Table-driven subtests with `t.Run` need to work.

---

## Risk Register

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|-----------|------------|
| 1 | `stdlib/http` lacks path params or WebSocket | Server can't be built on stdlib alone | Medium | Use Go `http.ServeMux` + `gorilla/websocket` directly, file stdlib issue |
| 2 | `github.com/kukichalang/game` has broken/minimal API | Desktop 2D blocked | High | Evaluate immediately in Phase 0; fall back to raw ebitengine + Go interop |
| 3 | Variant enum exhaustiveness breaks | `AIAction` switch won't compile | Low | File issue; add `default` arm as escape hatch |
| 4 | `GameState` 821 LOC struct hits Go complexity limits | Large file hard to port | Low | Split into multiple files in same petiole |
| 5 | JWT library coverage in stdlib | Auth can't be implemented cleanly | Medium | Use Go's `golang-jwt/jwt` directly, file issue for stdlib |
| 6 | `stdlib/json` typed decode doesn't handle game state map types | Serialization hacky | Medium | Use generic `jsonpkg.Marshal`/`Unmarshal` of T for well-typed things, `map of string to any` for dynamic state |
| 7 | Random placement differs between Python `random.randint` and Kukicha `stdlib/random` | Board generation deterministic differences | Low | Accept difference; game rules same |
| 8 | BFS with deque in Kukicha | Movement system performance | Low | Kukicha has `stdlib/slice` + goroutines; deque from linked list if needed |
| 9 | BFS adjacency uses `collections.deque` in Python | Need to implement queue | Low | Use `stdlib/slice` as stack/queue (`append`, `PopFirst` with `slice[1:]`) |
| 10 | `dereference x.field` transpiles to `*x.field` instead of `(*x).field` | Go build fails on valid Kukicha code | **Fixed** (v0.25.3, #241) | N/A — inline `dereference x.field` now works |
| 11 | `delete dereference m.field[key]` not supported by transpiler | Can't delete map entries via dereferenced struct | **Fixed** (#250, v0.26.0) | N/A |
| 12 | `nullable reference func(...)` generates uncallable `*func(...)` in Go | Callback fields can't be invoked | **Fixed** (#251, v0.26.2) | N/A |

---

## GitHub Issue Filing Guidelines

When filing issues for Kukicha/stdlib bugs:

1. **Minimal reproducer** — a single `.kuki` file (or Go equivalent) that demonstrates the bug in the smallest possible way.
2. **`kukicha explain <code>`** first — if the issue is a diagnostic error, run `kukicha explain <code>` and include the output.
3. **Versions** — include both `kukicha version` and Go version in bug reports.
4. **What was expected vs what happened** — describe the intended Kukicha behavior.
5. **Label appropriately** — use labels: `bug`, `stdlib/<pkg>`, `enhancement` for missing features.

---

## Commands Reference

```bash
# Development
kukicha check ./...              # syntax + semantic validation
kukicha build ./...              # transpile + go build
kukicha run ./server             # transpile + go build + run
kukicha fmt -w .                 # format all

# Testing
kukicha build ./...              # transpile (produces *_test.go too)
go test ./...                    # run all tests
go test ./game/...               # run game tests only

# Git workflow
kukicha check ./...              # pre-commit check
kukicha fmt -w .                 # pre-commit format
git add -p                       # review hunks (never brew .go)
```
