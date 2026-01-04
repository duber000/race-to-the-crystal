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

### ✅ 2. Circular Dependencies Risk
**Status:** ✅ **RESOLVED**
**Location:** Import statements

**Issue:** Late imports used to avoid circular dependencies.

**Resolution:**
- The circular dependency issues have been addressed
- Late imports are now properly managed
- Dependency structure is more hierarchical
- No actual circular imports exist in the current codebase

---

### ✅ 3. Mixed Concerns in Board Class
**Status:** ✅ **RESOLVED**
**Location:** `game/board.py`

**Issue:** The `Board` class mixed various concerns.

**Resolution:**
- Board initialization and special cell placement logic has been moved elsewhere
- The class is now more focused on grid data structure operations
- Position calculation methods like `get_starting_position` remain but are appropriate for the Board class

---

### ✅ 4. Hardcoded List Sizes
**Status:** ✅ **RESOLVED**
**Location:** `client/deployment_menu_controller.py:76`

**Issue:** Hardcoded health text objects for specific values `[2, 4, 6, 8, 10, 12]`.

**Resolution:**
- Added `UI_HEALTH_VALUES` constant in `shared/constants.py`
- Updated `DeploymentMenuController` to use `UI_HEALTH_VALUES` instead of hardcoded list
- This provides a single source of truth for UI health display values
- Separates UI display concerns from game logic (TOKEN_HEALTH_VALUES)

### 🟢 5. Global State
**Status:** Open
**Location:** `client/ui/async_arcade.py:105`

**Issue:** `get_async_scheduler()` uses module-level global.

**Recommendation:**
- Consider using dependency injection or context managers

