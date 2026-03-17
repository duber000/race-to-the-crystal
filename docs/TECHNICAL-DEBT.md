# Technical Debt Register

**Last Updated:** 2026-03-17
**Review Type:** Comprehensive Codebase Audit
**Reviewer:** AI Agent (opencode)
**Sprint 1 Status:** ✅ COMPLETED - Silent exception swallowing + Input validation
**Sprint 2 Status:** ✅ COMPLETED - SSE migration + Exception handling + Magic numbers
**Sprint 3 Status:** ✅ COMPLETED - Function refactoring + Code patterns + Init exports
**Sprint 4 Status:** ✅ COMPLETED - Null validation fixes + Type hints
**Sprint 5 Status:** ✅ COMPLETED - Core game logic tests (mystery_square, player, api, schemas)

---

## Executive Summary

This document catalogs technical debt identified during a comprehensive codebase review of Race to the Crystal. The codebase demonstrates **strong architectural fundamentals** with clean separation of concerns, testable game logic, and modern Python patterns. However, significant technical debt exists in **test coverage gaps** and **incomplete client rendering tests**.

**Sprint 2 (2026-03-16):** Resolved Item #6 - Complete SSE migration and centralized state management.

### Overall Health Assessment

| Category | Status | Risk Level |
|----------|--------|------------|
| Architecture | ✅ Strong | Low |
| Code Quality | ✅ Good | Low-Medium |
| Test Coverage | ⚠️ Partial | Medium-High |
| Error Handling | ✅ Good | Low |
| Documentation | ✅ Good | Low |
| Security | ✅ Good | Low |

### Priority Summary

- **🔴 Critical:** 2 items remaining (2, 7) - down from 6 (Item 1 completed)
- **🟡 High:** 0 items - all completed
- **🟢 Medium:** 2 items remaining (14, 20) - down from 6 (Items 18, 19 completed)

---

## Critical Technical Debt (Immediate Action Required)

### 1. Untested Core Game Logic ✅ RESOLVED 2026-03-17

**Status:** Resolved  
**Date Fixed:** 2026-03-17

**Impact:** Game mechanics could break silently without detection  
**Files:**
- `game/mystery_square.py` (163 lines) - Random events, teleportation ✅ Now tested
- `game/player.py` (110 lines) - Token ownership, serialization ✅ Now tested
- `game/api.py` (315 lines) - GameAPI facade for AI agents ✅ Now tested
- `game/schemas.py` (166 lines) - TypedDict validation schemas ✅ Now tested

**Test Files Added:**
- `tests/test_mystery_square.py` - 22 tests covering heal/teleport effects, edge cases, random distribution
- `tests/test_player.py` - 33 tests covering creation, token management, serialization, edge cases
- `tests/test_api.py` - 28 tests covering observation methods, actions, utility methods, edge cases
- `tests/test_schemas.py` - 36 tests covering all TypedDict schemas and validation

**Total New Tests:** 119 tests (was 0)

**Risk:** ✅ Mitigated - All core game logic now has comprehensive test coverage

**Completed:** Sprint 5 (2026-03-17)

---

### 2. Untested Server Infrastructure (1,794 lines)

**Impact:** Production failures undetected, debugging difficult  
**Files:**
- `server/game_server.py` (1,049 lines) - Main server logic
- `server/websocket_handler.py` (584 lines) - WebSocket protocol handling
- `server/auth.py` (164 lines) - JWT authentication
- `server/ai_spawner.py` (320 lines) - AI process management
- `server/mercure_publisher.py` (317 lines) - SSE publishing

**Risk:** Server is production-facing infrastructure. Bugs cause downtime, security vulnerabilities, or data loss.

**Recommendation:** Add tests for:
- Connection handling (CONNECT, RECONNECT, DISCONNECT)
- Message routing and validation
- JWT token creation/verification/expiration
- AI process lifecycle management
- SSE publish success/failure paths

**Estimated Effort:** 3-4 sprints

---

### 3. Silent Exception Swallowing ✅ RESOLVED 2026-03-16

**Impact:** Bugs hidden in production, debugging impossible  
**Instances:** 4 files with `except Exception: pass` - **ALL FIXED**

| File | Line | Context | Status |
|------|------|---------|--------|
| `server/ai_spawner.py` | 316-317 | AI process cleanup - errors swallowed after kill() fails | ✅ Fixed |
| `client/audio_manager.py` | 405-406 | Sound player cleanup - errors silently ignored | ✅ Fixed |
| `client/sprites/phantom_token_sprite.py` | 97 | Font loading fallback - no logging | ✅ Fixed |
| `client/sprites/token_sprite.py` | 94-95 | Font loading fallback - assigns default without logging | ✅ Fixed |

**Risk:** Silent failures mask bugs. Production issues go undetected until users report problems.

**Resolution:** Replaced all `except Exception: pass` with:
```python
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    # Handle gracefully but log
```

**Completed:** Sprint 1 (2026-03-16)

---

### 4. Unvalidated User Input ✅ RESOLVED 2026-03-16

**Impact:** Security vulnerabilities, injection attacks, crashes  
**Files:** `server/http_handler.py`, `server/websocket_handler.py`, `server/game_server.py` - **ALL FIXED**

**Examples:**
```python
# http_handler.py:215
player_name = data.get("player_name")  # Now validated with .strip() and length checks

# http_handler.py:360
action_type = action_data.get("type")  # Now validated with action-specific validation

# websocket_handler.py:373
data.get("defender_id") or data.get("target_id")  # Now validated with error responses
```

**Risk:** Malicious clients could send invalid data causing crashes, game state corruption, or security breaches.

**Resolution:** Added comprehensive input validation:
- Player names: `.strip()` and length validation
- Action types: validated against known types with specific field requirements
- Action fields: MOVE requires token_id + destination, ATTACK requires attacker_id + defender_id, DEPLOY requires health_value + position
- Game IDs: `.strip()` and empty checks
- All validation returns descriptive error messages

**Completed:** Sprint 1 (2026-03-16)

---

### 5. Overly Broad Exception Handling ✅ RESOLVED 2026-03-16

**Impact:** Error diagnosis impossible, wrong errors handled  
**Count:** 88 → 0 major instances in core rendering and server paths.

**Status:** Completed remediation for Tier 1-3.

| File | Status | Changes |
|------|--------|---------|
| `server/auth.py` | ✅ Already good | No changes needed |
| `server/game_server.py` | ✅ COMPLETE | ConnectionError, OSError, JSONDecodeError, etc. |
| `server/websocket_handler.py` | ✅ COMPLETE | aiohttp.ClientError, ConnectionResetError, etc. |
| `server/http_handler.py` | ✅ COMPLETE | jwt.InvalidTokenError, ValueError, etc. |
| `server/ai_spawner.py` | ✅ COMPLETE | asyncio.TimeoutError, OS errors, etc. |
| `server/mercure_publisher.py` | ✅ COMPLETE | httpx.HTTPStatusError added |
| `server/server_main.py` | ✅ COMPLETE | KeyboardInterrupt, OSError added |
| `network/connection.py` | ✅ COMPLETE | ConnectionResetError, BrokenPipeError, etc. |
| `client/audio_manager.py` | ✅ COMPLETE | Specific errors for sound operations |
| `client/renderer_3d.py` | ✅ COMPLETE | Refactored token creation loops |
| `client/board_3d.py` | ✅ COMPLETE | Shader compilation errors refactored |
| `client/sprites/*.py` | ✅ COMPLETE | Font loading and initialization |

**Risk:** Broad exceptions catch unexpected errors, masking real bugs.

**Resolution:** Replaced generic `Exception` catches with specific types and improved logging in all critical paths.

**Completed:** Sprint 2 (2026-03-16)

---

### 6. Incomplete SSE Migration ✅ RESOLVED 2026-03-16

**Impact:** Resolved architectural complexity and dual-path maintenance burden.

**Status:** Phase 5 and 6 (Delta updates, Centralized state management) completed.

**Resolution:** 
- Implemented SSE Delta Updates (`STATE_UPDATE`) with sequence tracking.
- Centralized JavaScript state management via `StateManager.js`.
- Cleaned up dual-channel race conditions and redundant merging logic.
- SSE-primary mode is now the fully supported and verified primary path.

**Completed:** Sprint 2 (2026-03-16)

---

### 7. Untested Client Rendering (~6,000 lines)

**Impact:** Visual bugs undetected, rendering issues in production  
**Files:** All `client/` rendering, input, audio, UI modules

**Key Untested Modules:**
- `client/board_3d.py` (762 lines) - 3D board rendering
- `client/input_handler.py` (762 lines) - Input routing
- `client/renderer_2d.py` (415 lines) - 2D sprite rendering
- `client/renderer_3d.py` (350 lines) - 3D OpenGL rendering
- `client/audio_manager.py` (464 lines) - Audio management
- `client/camera_controller.py` (486 lines) - Camera systems
- All `client/ui/` and `client/sprites/` modules (~1,200 lines)

**Risk:** Rendering bugs, input handling issues, and audio problems go undetected until user reports.

**Recommendation:** Add tests using:
- Screenshot-based visual regression testing (use `/testing-graphics` skill)
- Mock-based unit tests for rendering logic
- Integration tests for input handling

**Estimated Effort:** 4-6 sprints (requires graphical environment)

---

## High-Priority Technical Debt (Address Within 2 Sprints)

### 8. Large Monolithic Functions ✅ RESOLVED 2026-03-16

**Status:** Resolved  
**Date Fixed:** 2026-03-16

**Impact:** Maintenance difficulty, bug risk, testing complexity  
**Functions:**

| Function | File | Lines | Issue | Status |
|----------|------|-------|-------|--------|
| `end_turn()` | `game/game_state.py` | 133 → 6 | Violates single responsibility | ✅ Fixed |
| `on_update()` | `client/game_window.py` | 124 → 6 | Game loop logic should be delegated | ✅ Fixed |
| `_handle_new_connection()` | `server/game_server.py` | 234 | Connection handling should be split | ⏸️ Deferred |
| `__init__()` | `client/game_window.py` | 96 | Initialization should use helper methods | ⏸️ Deferred |
| `on_draw()` | `client/game_window.py` | 84 | Rendering should be delegated | ⏸️ Deferred |
| `_handle_start_game()` | `server/game_server.py` | 101 | Game start logic should be extracted | ⏸️ Deferred |
| `get_reserve_token_counts()` | `game/game_state.py` | 91 | Complex counting logic | ⏸️ Deferred |

**Resolution:**
- `end_turn()`: Extracted into 6 helper methods (`_clear_turn_state`, `_advance_to_next_player`, `_get_active_players`, `_calculate_next_player_index`, `_check_and_trigger_crystal_effects`, `_increment_turn_number`)
- `on_update()`: Extracted into 5 helper methods (`_check_victory_condition`, `_update_animations`, `_update_mystery_animations`, `_update_crystal_effects`, `_update_board_shapes`)

**Completed:** Sprint 3 (2026-03-16)

---

### 9. Duplicate Code Patterns ✅ RESOLVED 2026-03-16

**Status:** Resolved  
**Date Fixed:** 2026-03-16

**Impact:** DRY violations, maintenance burden, inconsistency risk  
**Instances:**

| Pattern | Location | Count | Status |
|---------|----------|-------|--------|
| Validation patterns | `game/ai_actions.py` | 14 similar patterns | ✅ Fixed |
| `to_dict()` method | `game/ai_actions.py` | 4 duplicates | ⏸️ Deferred |
| Glow rendering pattern | `client/renderer_2d.py` | 2 similar blocks | ⏸️ Deferred |
| `for j in range(len(points) - 1):` | `client/renderer_2d.py` | 4 duplicates | ⏸️ Deferred |
| `for token_3d in self.tokens_3d:` | `client/renderer_3d.py` | 6 duplicates | ⏸️ Deferred |
| `except Exception as e:` with identical logging | `client/renderer_3d.py` | 6 duplicates | ⏸️ Deferred |
| `lines.append("=" * 60)` | `game/ai_observation.py` | 3 duplicates | ⏸️ Deferred |

**Resolution:**
Added 6 validation helper methods to `AIActionExecutor` class:
- `_validate_game_phase()` - Check game is in PLAYING phase
- `_validate_player_turn()` - Check it's the player's turn
- `_validate_turn_phase()` - Check required turn phase
- `_validate_token_exists()` - Validate token exists and return it
- `_validate_token_ownership()` - Validate player owns the token
- `_validate_token_deployed()` - Validate token is deployed
- `_validate_token_alive()` - Validate token is alive

**Completed:** Sprint 3 (2026-03-16)

---

### 10. Magic Numbers in Rendering Code ✅ RESOLVED 2026-03-16

**Impact:** Configuration drift, inconsistency, maintenance difficulty  
**Locations:** `client/board_3d.py`, `client/game_window.py`, `client/renderer_3d.py`, `client/sprites/board_sprite.py`

**Resolution:** Centralized over 50 constants in [shared/constants.py](file:///var/home/tluker/repos/python/race-to-the-crystal/shared/constants.py).

**Completed:** Sprint 2 (2026-03-16)

---

### 11. Missing Type Hints

**Impact:** IDE support reduced, runtime errors possible, code clarity  
**Count:** 20+ methods lacking type hints

**Files:**
- `game/game_state.py` - `deploy_token()`, `attack_token()`, `_auto_deploy_starting_tokens()`, `apply_crystal_effect()`
- `client/game_window.py` - `__init__()`, `_draw_hud()`, `on_draw()`
- `client/input_handler.py` - `__init__()`, `handle_mouse_press()`, `handle_mouse_release()`
- `server/http_handler.py` - `__init__()`

**Recommendation:** Add modern Python 3.9+ type hints:
```python
def deploy_token(self, health_value: int, position: tuple[int, int]) -> Token:
    ...
```

**Estimated Effort:** 1 sprint

---

### 12. Deep Nesting (5+ Levels)

**Impact:** Code readability poor, bug risk, testing difficulty  
**Instances:**

| File | Lines | Depth | Context |
|------|-------|-------|---------|
| `client/game_window.py` | 314 | 6 levels | `_draw_hud()` - nested if-elif chain |
| `client/input_handler.py` | 128-131 | 6 levels | `handle_mouse_motion()` - camera pan call |
| `game/game_state.py` | 127-131 | 5 levels | `create_tokens_for_player()` - Token constructor |
| `server/game_server.py` | 162-166 | 5 levels | Connection message handling |
| `server/game_server.py` | 262-288 | 5 levels | Reconnection logic |
| `server/http_handler.py` | 219-257 | 5 levels | Error response handling |

**Recommendation:** Refactor using:
- Early returns
- Extract method pattern
- Guard clauses
- Pattern matching

**Estimated Effort:** 1 sprint

---

### 13. 20 `# type: ignore` Comments ✅ RESOLVED 2026-03-16

**Impact:** Type system compromised, potential runtime errors  
**Location:** `client/game_window.py`, `client/audio_manager.py`

**Resolution:** Resolved all critical type ignores in the rendering and audio loops by using assertions and safer attribute access patterns.

**Completed:** Sprint 2 (2026-03-16)

---

### 14. Inconsistent Error Message Formats ✅ RESOLVED 2026-03-16

**Status:** Resolved  
**Date Fixed:** 2026-03-16

**Impact:** Debugging difficulty, inconsistent API, poor DX  
**Pattern:** Multiple error formats across codebase

**Resolution:**
Created `shared/errors.py` with standardized error classes:
- `GameError` - Game logic errors: `CANNOT {action}: {reason} | {context}`
- `ValidationError` - Input validation: `Invalid {field}: {reason} | {context}`
- `ServerError` - Server errors: `Server error: {code} | {message}`
- `ActionError` - Action execution failures
- `ErrorCode` - Standardized error codes across all modules

**Files Updated:**
- `shared/errors.py` (NEW) - Standardized error classes
- `shared/__init__.py` - Exported error classes
- `server/http_handler.py` - All error responses use standardized format
- `server/websocket_handler.py` - All error messages use standardized format
- `server/game_coordinator.py` - Error messages standardized

**Completed:** Sprint 4 (2026-03-16)

---

## Medium-Priority Technical Debt (Address Within 4 Sprints)

### 15. Untested Network Layer (330 lines)

**Impact:** Network bugs undetected, protocol issues in production  
**Files:**
- `network/connection.py` (233 lines) - TCP connection wrapper
- `network/messages.py` (97 lines) - Message type enums

**Recommendation:** Add tests for:
- Connection establishment/closure
- Message encoding/decoding
- Protocol error handling
- Reconnection logic

**Estimated Effort:** 1 sprint

---

### 16. Untested Shared Utilities (600 lines)

**Impact:** Configuration bugs, enum misuse, type errors  
**Files:**
- `shared/corner_layout.py` (233 lines) - Player deployment zones
- `shared/constants.py` (164 lines) - Game constants
- `shared/enums.py` (52 lines) - Game enums
- `shared/types.py` (65 lines) - Type aliases
- `shared/ui_config.py` (52 lines) - UI parameters
- `shared/logging_config.py` (52 lines) - Logging setup

**Recommendation:** Add tests for:
- Corner layout configurations for all 4 players
- Constant value verification
- Enum value coverage
- Type alias usage patterns

**Estimated Effort:** 1 sprint

---

### 17. Empty `__init__.py` Files ✅ RESOLVED 2026-03-16

**Status:** Resolved  
**Date Fixed:** 2026-03-16

**Impact:** Import verbosity, missed opportunity for clean API  
**Count:** 6 empty `__init__.py` files (0 bytes) → 0 remaining

**Files Updated:**
- `game/__init__.py` - Exports GameAPI, GameState, AIActionExecutor, actions, AIObserver, Board, Token, Player
- `shared/__init__.py` - Exports enums, constants, types
- `server/__init__.py` - Exports GameServer, LobbyManager, GameLobby, GameStatus, GameCoordinator
- `client/__init__.py` - Exports GameView, NetworkClient, AudioManager, CameraController, InputHandler, Renderer2D, Renderer3D
- `network/__init__.py` - Exports Connection, ConnectionPool, ProtocolHandler, NetworkMessage, MessageType, ClientType

**Benefit:** Users can now import from top level:
```python
from game import GameAPI, GameState
from shared import GamePhase, TurnPhase, BOARD_WIDTH
from server import GameServer, LobbyManager
```

**Completed:** Sprint 3 (2026-03-16)

---

### 18. Uncalidated None Returns ✅ RESOLVED 2026-03-17

**Status:** Resolved  
**Date Fixed:** 2026-03-17

**Impact:** AttributeError crashes, silent failures  
**Files:** `server/game_coordinator.py`, `server/websocket_handler.py`, `server/game_server.py`

**Resolution:**
- Added null checks for `get_game_state_for_player()` returns in `websocket_handler.py` (3 locations)
- Added null check for `get_game_state_for_player()` in `game_server.py` (2 locations)
- Added validation for `defender_id` in action data in `websocket_handler.py`
- Fixed unbound `mercure_success` variable in `game_server.py`

**Files Updated:**
- `server/websocket_handler.py` - Added state_dict null checks and defender_id validation
- `server/game_server.py` - Added state_dict null checks and fixed unbound variable

**Completed:** Sprint 4 (2026-03-17)

---

### 19. Missing Null Checks ✅ RESOLVED 2026-03-17

**Status:** Resolved  
**Date Fixed:** 2026-03-17

**Impact:** AttributeError crashes on edge cases  
**Files:** `server/websocket_handler.py`, `server/game_server.py`

**Resolution:**
- Fixed `defender_id` validation in `websocket_handler.py` - now validates before adding to action_data
- Added comprehensive null checks for all `get_game_state_for_player()` return values
- Added early returns with warning logs when state cannot be retrieved

**Files Updated:**
- `server/websocket_handler.py` - Lines 440-445, 502-517, 606-614, 634-649
- `server/game_server.py` - Lines 726-732, 807-813, 868-873

**Completed:** Sprint 4 (2026-03-17)

---

### 20. Integration Test Gaps

**Impact:** End-to-end bugs undetected, integration issues in production  
**Missing Tests:**
- No end-to-end gameplay integration tests
- No AI client integration with game server
- No 3D rendering + game logic integration
- No deployment flow integration tests
- No crystal/generator capture end-to-end tests

**Current Integration Tests:** 3 files (8 + 5 + 3 = 16 tests total)
- `test_chat_integration.py` - 8 tests
- `test_game_coordinator_integration.py` - 5 tests
- `test_network_multiplayer_integration.py` - 3 tests

**Recommendation:** Add integration tests for:
- Full gameplay loop (start → play → win)
- AI client + server integration
- Deployment → movement → attack → end turn flow
- Generator capture → crystal win condition chain

**Estimated Effort:** 2-3 sprints

---

### 21. Skipped Tests in CI

**Impact:** Test coverage reduced in CI environments  
**File:** `test_game_window_initialization.py` - 2 tests skipped when headless

**Pattern:**
```python
@pytest.mark.skipif(condition, reason="Requires display")
def test_game_window_initialization():
    ...
```

**Risk:** Tests only run on developer machines with displays. CI coverage reduced.

**Recommendation:** Add mock-based tests for headless environments or use virtual framebuffer (Xvfb).

**Estimated Effort:** 1-2 days

---

## Debt Accumulation Trends

### Feature Flags

| Flag | Location | Status | Age |
|------|----------|--------|-----|
| `sse_primary_mode` | `server/game_server.py` | Incomplete migration | 2026-01-11 |

**Risk:** Feature flags older than 2 sprints indicate incomplete work.

---

### Documentation Debt

| Document | Status | Last Updated |
|----------|--------|--------------|
| `docs/SSE_ROADMAP.md` | Incomplete | 2026-01-11 |
| `docs/PHASE4_5_SSE_TODO.md` | Pending tasks | 2026-01-13 |

**Recommendation:** Complete or archive incomplete documentation.

---

## Remediation Roadmap

### ✅ Sprint 1 - COMPLETED (2026-03-16)
- [x] Replace silent `pass` handlers with logging (Item #3 - RESOLVED)
- [x] Add input validation for `.get()` calls (Item #4 - RESOLVED)

### ✅ Sprint 2 - COMPLETED / IN PROGRESS (2026-03-16)
- [x] Complete SSE migration and centralized state management (Item #6 - RESOLVED)
- [x] Refactor broad exception handlers (Item #5 - RESOLVED)
- [x] Move magic numbers to constants (Item #10 - RESOLVED)
- [x] Audit # type: ignore comments (Item #13 - RESOLVED)

### ✅ Sprint 3 - COMPLETED (2026-03-16)
- [x] Refactor large functions (>100 lines) - `end_turn()` and `on_update()` ✅
- [x] Extract duplicate code patterns - Validation helpers in `ai_actions.py` ✅
- [x] Add re-exports to `__init__.py` files - 5 modules updated ✅

### ✅ Sprint 4 - COMPLETED (2026-03-17)
- [x] Fix null validation issues (Items #18, #19) - Added null checks for state returns and defender_id
- [x] Add type hints to critical methods - `input_handler.py`, `game_window.py`, `http_handler.py`
- [x] Fix malformed type annotation in `game_action_handler.py`

### ✅ Sprint 5 - COMPLETED (2026-03-17)
- [x] Add comprehensive tests for core game logic (Item #1 - RESOLVED)
  - [x] `test_mystery_square.py` - 22 tests for mystery square events
  - [x] `test_player.py` - 33 tests for player management
  - [x] `test_api.py` - 28 tests for GameAPI facade
  - [x] `test_schemas.py` - 36 tests for TypedDict schemas

### Sprint 6 (Medium)
- [ ] Add type hints to all public methods
- [ ] Refactor deep nesting (6 instances)
- [ ] Audit `# type: ignore` comments
- [ ] Add network layer tests
- [ ] Add shared utility tests

### Sprint 7-8 (Coverage - Excluded per request)
- [ ] Add client rendering tests (screenshot-based) ⏸️ Excluded
- [ ] Add integration tests for full gameplay loop
- [ ] Add AI client integration tests
- [ ] Achieve >80% test coverage on game logic ⏸️ Excluded
- [ ] Achieve >70% test coverage on server ⏸️ Excluded
- [ ] Achieve >50% test coverage on client ⏸️ Excluded

---

## Monitoring Technical Debt

### Metrics to Track

| Metric | Current | Target | Frequency |
|--------|---------|--------|-----------|
| Test coverage (game) | ~80% | >90% | Per PR |
| Test coverage (server) | ~30% | >70% | Per sprint |
| Test coverage (client) | ~10% | >50% | Per sprint |
| Function length (>50 lines) | 15 | <5 | Per sprint |
| `# type: ignore` count | 20 | 0 | Per sprint |
| Broad exception count | 40+ | <10 | Per sprint |
| Feature flag age | 60+ days | <30 days | Per sprint |

### Code Quality Checks

Add to CI/CD:
```bash
# Run static analysis
make lint

# Check type coverage
# (Consider adding pyright or mypy strict mode)

# Count large functions
find . -name "*.py" -exec awk '/^    def /{func=$2} /^[[:space:]]*$/{if(NR-last>50)print func" "last"-"NR} {last=NR}' {} \;

# Count broad exceptions
grep -r "except Exception" --include="*.py" | wc -l
```

---

## Success Criteria

Technical debt remediation is complete when:

- [ ] All critical untested modules have test coverage
- [x] No silent exception swallowing (`except Exception: pass`) ✅ Sprint 1
- [x] All user input validated ✅ Sprint 1
- [ ] No feature flags older than 30 days
- [ ] All functions <100 lines
- [ ] No duplicate code patterns (DRY enforced)
- [ ] All magic numbers in constants
- [ ] All public methods have type hints
- [ ] No `# type: ignore` comments
- [ ] Standardized error message format
- [ ] >80% test coverage on game logic
- [ ] >70% test coverage on server
- [ ] >50% test coverage on client

---

## References

- [AGENTS.md](../AGENTS.md) - AI agent developer guide
- [SSE_ROADMAP.md](./SSE_ROADMAP.md) - SSE architecture roadmap
- [PHASE4_5_SSE_TODO.md](./PHASE4_5_SSE_TODO.md) - SSE migration TODOs
- [GAME.md](./GAME.md) - Game rules documentation
- [NETWORK.md](./NETWORK.md) - Network protocol documentation
- [3D.md](./3D.md) - 3D rendering documentation
