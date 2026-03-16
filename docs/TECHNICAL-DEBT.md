# Technical Debt Register

**Last Updated:** 2026-03-16
**Review Type:** Comprehensive Codebase Audit
**Reviewer:** AI Agent (opencode)
**Sprint 1 Status:** ✅ COMPLETED - Silent exception swallowing + Input validation

---

## Executive Summary

This document catalogs technical debt identified during a comprehensive codebase review of Race to the Crystal. The codebase demonstrates **strong architectural fundamentals** with clean separation of concerns, testable game logic, and modern Python patterns. However, significant technical debt exists in **test coverage gaps** and **incomplete architectural migration** (SSE-primary mode).

**Sprint 1 (2026-03-16):** Resolved 2 critical items - silent exception swallowing and unvalidated user input.

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

- **🔴 Critical:** 3 items remaining (immediate action required) - down from 5
- **🟡 High:** 5 items (address within 2 sprints)
- **🟢 Medium:** 6 items (address within 4 sprints)

---

## Critical Technical Debt (Immediate Action Required)

### 1. Untested Core Game Logic (754 lines)

**Impact:** Game mechanics could break silently without detection  
**Files:**
- `game/mystery_square.py` (163 lines) - Random events, teleportation
- `game/player.py` (110 lines) - Token ownership, serialization
- `game/api.py` (315 lines) - GameAPI facade for AI agents
- `game/schemas.py` (166 lines) - TypedDict validation schemas

**Risk:** These modules contain core game mechanics with zero unit test coverage. Changes could introduce game-breaking bugs undetected.

**Recommendation:** Add comprehensive unit tests covering:
- Mystery square random events (heal vs teleport probabilities)
- Mystery square edge cases (teleport to occupied cells)
- Player token ownership and serialization
- GameAPI facade methods (move, attack, deploy, end_turn, observe)
- Schema validation edge cases

**Estimated Effort:** 2-3 sprints

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

### 5. Overly Broad Exception Handling

**Impact:** Error diagnosis impossible, wrong errors handled  
**Count:** 40+ `except Exception` blocks across codebase

| File | Count | Risk |
|------|-------|------|
| `client/audio_manager.py` | 15 | Audio operations should catch specific media errors |
| `server/ai_spawner.py` | 8 | Process management needs specific handling |
| `server/websocket_handler.py` | 6 | Protocol errors should be specific |
| `network/connection.py` | 6 | Network I/O should catch specific errors |
| `server/game_server.py` | 4 | Server logic needs specific error handling |

**Risk:** Broad exceptions catch unexpected errors, masking real bugs and making debugging difficult.

**Recommendation:** Replace with specific exception types:
```python
# Instead of:
except Exception as e:
    logger.error(f"Error: {e}")

# Use:
except asyncio.TimeoutError as e:
    logger.warning(f"Connection timeout: {e}")
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
```

**Estimated Effort:** 1-2 sprints

---

### 6. Incomplete SSE Migration (Feature Flag Debt)

**Impact:** Architectural complexity, dual-path maintenance burden  
**Files:** `docs/SSE_ROADMAP.md`, `docs/PHASE4_5_SSE_TODO.md`, `server/game_server.py`

**Details:**
- Feature flag `sse_primary_mode` creates conditional complexity
- Dual-channel (WebSocket + SSE) vs SSE-primary mode paths
- Incomplete migration documented since 2026-01-11
- Phase 3-5 testing and deployment pending

**Code Example:**
```python
# game_server.py:775-777
if self.sse_primary_mode and client_type in SSE_CAPABLE_CLIENTS:
    logger.debug(f"Skipping FULL_STATE for {player_id} ({client_type.value}) - using SSE")
    continue  # Skip WebSocket send
```

**Risk:** Feature flags accumulate technical debt. Dual-path code diverges, testing becomes harder, eventual migration more difficult.

**Recommendation:** Complete SSE migration testing per `docs/PHASE4_5_SSE_TODO.md` or remove feature flag and revert to single architecture.

**Estimated Effort:** 2-3 sprints (complete migration) or 1 sprint (remove flag)

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

### 8. Large Monolithic Functions

**Impact:** Maintenance difficulty, bug risk, testing complexity  
**Functions:**

| Function | File | Lines | Issue |
|----------|------|-------|-------|
| `_handle_new_connection()` | `server/game_server.py` | 234 | Connection handling should be split into smaller methods |
| `end_turn()` | `game/game_state.py` | 133 | Violates single responsibility - does too much |
| `on_update()` | `client/game_window.py` | 124 | Game loop logic should be delegated |
| `__init__()` | `client/game_window.py` | 96 | Initialization should use helper methods |
| `on_draw()` | `client/game_window.py` | 84 | Rendering should be delegated to controllers |
| `_handle_start_game()` | `server/game_server.py` | 101 | Game start logic should be extracted |
| `get_reserve_token_counts()` | `game/game_state.py` | 91 | Complex counting logic should be simplified |

**Recommendation:** Refactor using:
- Extract method pattern
- Single responsibility principle
- Delegation to helper methods
- Early returns to reduce nesting

**Estimated Effort:** 1-2 sprints

---

### 9. Duplicate Code Patterns

**Impact:** DRY violations, maintenance burden, inconsistency risk  
**Instances:**

| Pattern | Location | Count |
|---------|----------|-------|
| Validation pattern: `if not (var := ...): return ValidationResult(False, ...)` | `game/ai_actions.py` | 14 similar patterns |
| `to_dict()` method | `game/ai_actions.py` action classes | 4 duplicates |
| Glow rendering pattern | `client/renderer_2d.py` | 2 similar blocks |
| `for j in range(len(points) - 1):` | `client/renderer_2d.py` | 4 duplicates |
| `for token_3d in self.tokens_3d:` | `client/renderer_3d.py` | 6 duplicates |
| `except Exception as e:` with identical logging | `client/renderer_3d.py` | 6 duplicates |
| `lines.append("=" * 60)` | `game/ai_observation.py` | 3 duplicates |

**Recommendation:** Extract common patterns into helper methods:
```python
# ai_actions.py - create validation helper
def _validate_field(self, value: Any | None, field_name: str) -> ValidationResult:
    if not value:
        return ValidationResult(False, f"{field_name} is required")
    return ValidationResult(True, "Valid")
```

**Estimated Effort:** 1 sprint

---

### 10. Magic Numbers in Rendering Code

**Impact:** Configuration drift, inconsistency, maintenance difficulty  
**Locations:** `client/board_3d.py`, `client/game_window.py`, `client/renderer_2d.py`

**Examples:**
```python
# board_3d.py:92
color = np.array([0.78, 0.78, 0.78, 1.0])  # Magic color value

# board_3d.py:211
segments = 20  # Magic number for circle segments

# board_3d.py:329
cube_height = 40.0  # Magic generator height

# game_window.py:101-111
(255, 255, 255), (200, 200, 200), (150, 150, 150)  # Magic RGB colors

# renderer_2d.py:296, 315
(255, 255, 0, alpha), (0, 255, 0, alpha)  # Magic glow colors
```

**Recommendation:** Move to `shared/constants.py`:
```python
# shared/constants.py
BOARD_GRID_COLOR = (0.78, 0.78, 0.78, 1.0)
CIRCLE_SEGMENTS = 20
GENERATOR_HEIGHT = 40.0
CRYSTAL_HEIGHT = 50.0
COLOR_WHITE = (255, 255, 255)
COLOR_LIGHT_GRAY = (200, 200, 200)
COLOR_GRAY = (150, 150, 150)
GLOW_YELLOW = (255, 255, 0)
GLOW_GREEN = (0, 255, 0)
```

**Estimated Effort:** 1-2 days

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

### 13. 20 `# type: ignore` Comments

**Impact:** Type system compromised, potential runtime errors  
**Location:** `client/game_window.py` (20 instances)

**Lines:** 252, 260, 307, 308, 310, 333, 348, 350, 359, 371, 380, 382, 391, 397, 400, 410, 411, 417, 534, 535

**Risk:** Type ignore comments indicate type system issues. Runtime type errors possible.

**Recommendation:** Audit each `# type: ignore` and:
- Fix underlying type issue
- Add proper type annotations
- Remove ignore comment

**Estimated Effort:** 1-2 days

---

### 14. Inconsistent Error Message Formats

**Impact:** Debugging difficulty, inconsistent API, poor DX  
**Pattern:** Multiple error formats across codebase

| Pattern | Example Location | Format |
|---------|-----------------|--------|
| Simple string | `server/http_handler.py:288` | `{"error": str(e)}` |
| Generic message | `server/http_handler.py:292` | `{"error": "Internal server error"}` |
| Prefixed error | `server/websocket_handler.py:174` | `"Invalid JSON format"` |
| Server error prefix | `server/websocket_handler.py:176` | `"Server error: {e}"` |
| Tuple return | `server/game_coordinator.py:128` | `(False, "Player not in game", None)` |
| Game logic format | `game/ai_actions.py` | `CANNOT {action}: {reason} \| {context}` |

**Recommendation:** Standardize on game logic format across all modules:
```python
# Standard format: CANNOT {action}: {reason} | {context}
return ValidationResult(
    False,
    "CANNOT MOVE: token_not_found | token_id=99 | valid_tokens=[1,2,3,4,5]"
)
```

**Estimated Effort:** 1 sprint

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

### 17. Empty `__init__.py` Files

**Impact:** Import verbosity, missed opportunity for clean API  
**Count:** 12 empty `__init__.py` files (0 bytes)

**Files:** `game/__init__.py`, `client/__init__.py`, `server/__init__.py`, `shared/__init__.py`, etc.

**Recommendation:** Add re-exports for cleaner imports:
```python
# game/__init__.py
from game.api import GameAPI
from game.game_state import GameState
from game.ai_actions import AIActionExecutor, MoveAction, AttackAction, DeployAction, EndTurnAction
from game.ai_observation import AIObserver

__all__ = [
    "GameAPI",
    "GameState",
    "AIActionExecutor",
    "MoveAction",
    "AttackAction",
    "DeployAction",
    "EndTurnAction",
    "AIObserver",
]
```

**Benefit:** Users can import from top level: `from game import GameAPI, GameState`

**Estimated Effort:** 1-2 days

---

### 18. Uncalidated None Returns

**Impact:** AttributeError crashes, silent failures  
**Files:** `server/game_coordinator.py`, `server/lobby.py`, `server/mercure_publisher.py`, `client/network_client.py`

**Pattern:** Functions return `None` or `False` but callers don't validate:
```python
# game_coordinator.py:128
return (False, "Player not in game", None)

# Caller may not check:
result = executor.execute_action(action, game_state, player_id)
# result.success not checked
```

**Recommendation:** Add validation at call sites:
```python
result = executor.execute_action(action, game_state, player_id)
if not result.success:
    logger.error(f"Action failed: {result.message}")
    return
```

**Estimated Effort:** 1 sprint

---

### 19. Missing Null Checks

**Impact:** AttributeError crashes on edge cases  
**Count:** 18 null checks present (good), but gaps exist

**Gaps:**
- `server/websocket_handler.py:373` - `data.get("defender_id") or data.get("target_id")` could still be None
- `server/game_coordinator.py:126-128` - Checks `game_player_id` but action executor may return None
- `client/input_handler.py` - Multiple `is None` checks but not all code paths covered

**Recommendation:** Add null checks before using data from `.get()` without defaults:
```python
defender_id = data.get("defender_id") or data.get("target_id")
if defender_id is None:
    return error_response("Missing defender_id")
```

**Estimated Effort:** 1-2 days

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

### Sprint 2 (Critical - Remaining)
- [ ] Add tests for `mystery_square.py`
- [ ] Add tests for `player.py`
- [ ] Add tests for `auth.py`

### Sprint 3-4 (High)
- [ ] Refactor large functions (>100 lines)
- [ ] Extract duplicate code patterns
- [ ] Move magic numbers to constants
- [ ] Standardize error message format
- [ ] Complete SSE migration testing or remove flag

### Sprint 5-6 (Medium)
- [ ] Add type hints to all public methods
- [ ] Refactor deep nesting
- [ ] Audit `# type: ignore` comments
- [ ] Add re-exports to `__init__.py` files
- [ ] Add network layer tests
- [ ] Add shared utility tests

### Sprint 7-8 (Coverage)
- [ ] Add client rendering tests (screenshot-based)
- [ ] Add integration tests for full gameplay loop
- [ ] Add AI client integration tests
- [ ] Achieve >80% test coverage on game logic
- [ ] Achieve >70% test coverage on server
- [ ] Achieve >50% test coverage on client

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
