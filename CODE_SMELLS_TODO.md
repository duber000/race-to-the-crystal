# Code Smells TODO

This document tracks identified code smells and refactoring opportunities in the Race to the Crystal codebase.

## Status Legend
- 🔴 **High Priority** - Should be addressed soon
- 🟡 **Medium Priority** - Should be addressed when time permits
- 🟢 **Low Priority** - Nice to have improvements
- ✅ **Completed** - Issue has been resolved

---

### 🟡 1. Feature Envy - AIObserver
**Status:** ⏸️ **ON HOLD** (Skipped for now)
**Location:** `game/ai_observation.py`

**Issue:** The `AIObserver` class extensively accesses internal data of `GameState`, `Generator`, `Crystal`, and other objects.

**Example:**
```python
# ai_observation.py:202
status = AIObserver._get_generator_status(gen, game_state)
# Accesses: generator.is_disabled, generator.capturing_player_id,
# generator.capture_token_ids, game_state.get_player(), player.color, etc.
```

**Recommendation:**
- Consider moving some observation methods as instance methods on the respective classes
- Add `to_observation_dict()` methods on domain objects
- Use the Tell-Don't-Ask principle where possible

**Note:** This refactoring is being deferred as the current implementation is functional and changes could affect AI gameplay behavior.

---

### 🟡 2. Circular Dependencies Risk
**Status:** Open
**Location:** Import statements

**Issue:** Late imports used to avoid circular dependencies (lines 294, 428, 435 in `game_state.py`).

**Examples:**
- `game/ai_actions.py:427` imports from `game/ai_observation`
- `game/game_state.py` imports from `game/combat`, `game/generator`, `game/crystal`

**Recommendation:**
- Restructure module dependencies to be more hierarchical
- Consider dependency injection
- Move shared types to a common module

---

### 🟡 3. Mixed Concerns in Board Class
**Status:** Open
**Location:** `game/board.py`

**Issue:** The `Board` class mixes:
- Grid data structure management
- Cell type placement logic (`_place_crystal`, `_place_generators`, `_place_mystery_squares`)
- Position validation
- Special position queries (`get_starting_position`, `get_deployable_positions`)

**Recommendation:**
- Extract board initialization to a `BoardFactory` or `BoardGenerator`
- Separate position calculation logic into a `BoardGeometry` utility
- Keep `Board` focused on grid data structure operations

---

### 🟢 4. Hardcoded List Sizes
**Status:** Open
**Location:** `client/game_window.py:131-136`

**Issue:** Hardcoded health text objects for specific values `[2, 4, 6, 8, 10, 12]`.

**Recommendation:**
- Should be derived from `TOKEN_HEALTH_VALUES` constant

### 🟢 5. Global State
**Status:** Open
**Location:** `client/ui/async_arcade.py:105`

**Issue:** `get_async_scheduler()` uses module-level global.

**Recommendation:**
- Consider using dependency injection or context managers

