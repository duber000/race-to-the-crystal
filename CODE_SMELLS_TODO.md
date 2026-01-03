# Code Smells TODO

This document tracks identified code smells and refactoring opportunities in the Race to the Crystal codebase.

## Status Legend
- 🔴 **High Priority** - Should be addressed soon
- 🟡 **Medium Priority** - Should be addressed when time permits
- 🟢 **Low Priority** - Nice to have improvements
- ✅ **Completed** - Issue has been resolved

---

## Critical Issues

### 🔴 1. God Object - GameView Class
**Status:** ✅ **IN PROGRESS** (Phases 1-4 of 8 complete)
**Location:** `client/game_window.py` (1816 lines → 1084 lines after Phases 1-4)
**Issue:** The `GameView` class handles too many responsibilities:
- ~~Rendering (2D and 3D)~~ ✅ **2D EXTRACTED**
- Input handling (mouse, keyboard)
- ~~Camera management (2D and 3D cameras)~~ ✅ **EXTRACTED**
- UI management
- ~~Music/audio management~~ ✅ **EXTRACTED**
- Game state updates
- Network communication
- ~~Deployment menu logic~~ ✅ **EXTRACTED**
- Token selection logic

**Progress:**
- ✅ **Phase 1 Complete:** Extracted `AudioManager` (151 lines removed)
  - Background music loading and playback
  - Generator hum track management (4 separate audio streams)
  - Music toggle functionality
  - Generator hum updates based on game state
  - File: `client/audio_manager.py` (248 lines)

- ✅ **Phase 2 Complete:** Extracted `DeploymentMenuController` (285 lines removed)
  - Corner indicator rendering (R hexagon)
  - Deployment menu rendering and interaction
  - Menu state management
  - Deployment position validation
  - Fixed duplicate corner positioning logic using shared corner_layout config
  - File: `client/deployment_menu_controller.py` (399 lines)

- ✅ **Phase 3 Complete:** Extracted `CameraController` (187 lines removed)
  - 2D camera system (orthographic top-down view)
  - 3D camera system (first-person perspective)
  - Camera mode switching between 2D and 3D
  - Panning and zooming in 2D mode
  - Token following in 3D mode
  - Mouse-look rotation (right-click drag)
  - Q/E key camera rotation around token
  - Screen-to-world coordinate conversion (2D and 3D ray casting)
  - Window resize handling
  - File: `client/camera_controller.py` (397 lines)

- ✅ **Phase 4 Complete:** Extracted `Renderer2D` (109 lines removed)
  - Board shapes rendering (grid, generators, crystal, mystery squares)
  - Token sprite management and rendering
  - Selection visual feedback (highlights and valid move indicators)
  - 2D rendering update loop
  - Sprite animation updates
  - File: `client/renderer_2d.py` (249 lines)

**Remaining Phases:**
- Phase 5: Extract `Renderer3D` (3D rendering)
- Phase 6: Extract `GameActionHandler` (game actions)
- Phase 7: Extract `InputHandler` (input coordination)
- Phase 8: Final cleanup and testing

**Total Reduction:** 732 lines removed (1816 → 1084 lines, 40% reduction)

**Commits:**
- 984b254: Refactor: Extract AudioManager from GameView (Phase 1/8)
- 517f13b: Refactor: Extract DeploymentMenuController from GameView (Phase 2/8)
- 997f10a: Refactor: Extract CameraController from GameView (Phase 3/8)
- (Phase 4 commit pending)

---

### 🔴 2. Long Methods
**Status:** Open
**Locations:**
- `client/game_window.py:_draw_corner_menu_ui()` (lines 631-699+)
- `game/ai_observation.py:describe_game_state()` (lines 88-237)
- `game/ai_observation.py:list_available_actions()` (lines 343-453)
- `client/game_window.py:on_mouse_press()` (likely 100+ lines)

**Recommendation:**
- Break down methods into smaller, single-responsibility functions
- Extract complex conditional logic into separate helper methods
- Use early returns to reduce nesting

---

### 🔴 3. Duplicate Code - Player Index Corner Handling
**Status:** ✅ **IN PROGRESS**
**Location:** `client/game_window.py` (lines 550-699), `board.py` (lines 301-323)

**Issue:** Corner position calculation and deployment logic is repeated for each of 4 players with slight variations.

**Current Pattern:**
```python
if player_index == 0:  # Top-left
    # Logic for player 0
elif player_index == 1:  # Top-right
    # Similar logic for player 1
# ... etc
```

**Recommendation:**
- Create a `CornerLayout` data class with configurations for each corner
- Use a dictionary/lookup table instead of if-elif chains
- Extract common logic into reusable functions

---

### 🟡 4. Inconsistent Logging
**Status:** ✅ **COMPLETED**
**Location:** Throughout codebase

**Issue:** Mix of `print()` statements and proper logging:
- `client/game_window.py` uses `print()` extensively
- `server/`, `network/`, and `client/ai_client.py` use proper `logging`

**Resolution:**
- ✅ Created `shared/logging_config.py` module
- ✅ Converted all 84 print() statements in `game_window.py` to appropriate logger calls
- ✅ Used proper log levels: DEBUG (detailed state), INFO (normal flow), WARNING (potential issues), ERROR (actual errors)
- ✅ Consistent logging format across the codebase

**Files Modified:**
- `shared/logging_config.py` (new)
- `client/game_window.py` (84 print statements → logger calls)

---

### 🟡 5. Magic Numbers
**Status:** ✅ **COMPLETED**
**Location:** Multiple files

**Issue:** Hardcoded numeric values throughout the codebase without named constants.

**Resolution:**
- ✅ Added 20+ new constants to `shared/constants.py`:
  - **UI Configuration**: HUD_HEIGHT, CORNER_INDICATOR_SIZE, CORNER_INDICATOR_MARGIN, DEPLOYMENT_MENU_SPACING, MENU_OPTION_CLICK_RADIUS, HEXAGON_SIDES, CIRCLE_SEGMENTS
  - **Chat Widget**: CHAT_WIDGET_WIDTH, CHAT_WIDGET_HEIGHT, CHAT_WIDGET_X, CHAT_WIDGET_Y
  - **Camera Controls**: CAMERA_PAN_SPEED, CAMERA_INITIAL_ZOOM, CAMERA_ROTATION_INCREMENT, MOUSE_LOOK_SENSITIVITY
  - **Audio**: BACKGROUND_MUSIC_VOLUME, GENERATOR_HUM_VOLUME
  - **Animation**: MYSTERY_ANIMATION_DURATION
  - **Board Generation**: MYSTERY_PLACEMENT_MAX_ATTEMPTS, MYSTERY_PLACEMENT_EDGE_MARGIN
- ✅ Replaced all magic numbers in `client/game_window.py` with named constants
- ✅ Replaced magic numbers in `game/board.py` for mystery square placement
- ✅ All constants properly documented with comments

**Files Modified:**
- `shared/constants.py` (+20 new constants)
- `client/game_window.py` (replaced ~15 magic numbers)
- `game/board.py` (replaced 3 magic numbers)

---

### 🟡 6. Feature Envy - AIObserver
**Status:** Open
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

---

### 🟡 7. Data Clumps - Position Tuples
**Status:** ✅ **COMPLETED**
**Location:** Throughout codebase

**Issue:** Position tuples `(x, y)` passed around repeatedly with same operations.

**Resolution:**
- ✅ Created `shared/position.py` with immutable Position dataclass
- ✅ Includes helper methods: `is_valid()`, `distance_to()`, `manhattan_distance_to()`, `is_adjacent_to()`, `get_neighbors()`, `offset()`
- ✅ Supports tuple conversion for backwards compatibility
- ✅ Supports unpacking: `x, y = position`
- ✅ Operator overloading for vector math (+ and -)

**Files Modified:**
- `shared/position.py` (new)

**Note:** Legacy code still uses tuples. Gradual migration recommended for new code.

---

### 🟡 8. Primitive Obsession - Token ID and Player ID
**Status:** Open
**Location:** Throughout codebase

**Issue:** Using `int` for token_id and `str` for player_id without type safety.

**Recommendation:**
- Consider using NewType or custom ID classes:
```python
from typing import NewType

TokenID = NewType('TokenID', int)
PlayerID = NewType('PlayerID', str)
```

---

### 🟡 9. Temporary Fields / State Flags
**Status:** Open
**Location:** `client/game_window.py`

**Issue:** Multiple boolean flags that are only meaningful in certain states:
- `corner_menu_open` (line 93)
- `corner_menu_just_opened` (line 94) - **Particularly problematic**
- `selected_deploy_health` (line 95-97)
- `mouse_look_active` (line 104)

**Recommendation:**
- Use a state machine pattern for UI states
- Group related flags into state enums:
```python
class UIState(Enum):
    NORMAL = "normal"
    CORNER_MENU_OPENING = "menu_opening"
    CORNER_MENU_OPEN = "menu_open"
    DEPLOYMENT_MODE = "deployment"
    TOKEN_SELECTED = "token_selected"
```

---

### 🟡 10. Long Parameter Lists
**Status:** Open
**Location:** Multiple method signatures

**Issue:** Methods passing many parameters or complex combinations repeatedly.

**Recommendation:**
- Use parameter objects for related parameters
- Consider builder pattern for complex object construction
- Group related parameters into context objects

---

### 🟡 11. Comments Explaining Complex Code
**Status:** Open
**Location:** Throughout codebase

**Issue:** Many comments explain **what** the code does rather than **why**.

**Examples:**
```python
# game_window.py:94
self.corner_menu_just_opened = False  # Flag to prevent immediate click-through

# board.py:298
# Determine direction into the board from each corner
```

**Recommendation:**
- Refactor complex code to be self-documenting
- Use better variable/method names
- Only comment **why** decisions were made, not what the code does

---

### 🟡 12. Inconsistent Return Types
**Status:** Open
**Location:** `game/ai_actions.py`

**Issue:** The `execute_action()` method returns `Tuple[bool, str, Optional[Dict]]`, which is complex and error-prone.

**Recommendation:**
- Use a result object:
```python
@dataclass
class ActionResult:
    success: bool
    message: str
    data: Optional[Dict] = None
```

---

### 🟡 13. Circular Dependencies Risk
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

### 🟡 14. Mixed Concerns in Board Class
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

### 🟢 15. String-based Type Names in Serialization
**Status:** Open
**Location:** Throughout dataclasses

**Issue:** Using `enum.name` for serialization is fragile to renaming.

**Recommendation:**
- Use enum values instead of names, or
- Add explicit serialization version field
- Consider using a proper serialization library (e.g., pydantic)

---

## Minor Issues

### 🟢 16. Hardcoded List Sizes
**Status:** Open
**Location:** `client/game_window.py:131-136`

**Issue:** Hardcoded health text objects for specific values `[2, 4, 6, 8, 10, 12]`.

**Recommendation:**
- Should be derived from `TOKEN_HEALTH_VALUES` constant

---

### 🟢 17. Dead Code / Unused Methods
**Status:** ✅ **COMPLETED**
**Location:** `client/game_window.py:420`

**Issue:** `_create_corner_indicator()` method body is empty with just `pass`.

**Resolution:**
- ✅ Removed empty `_create_corner_indicator()` method
- ✅ Updated outdated comments in `game_state.py`
- ✅ Clarified TODO comments for future implementation

**Files Modified:**
- `client/game_window.py` (removed method)
- `game/game_state.py` (updated comments)

---

### 🟢 18. Global State
**Status:** Open
**Location:** `client/ui/async_arcade.py:105`

**Issue:** `get_async_scheduler()` uses module-level global.

**Recommendation:**
- Consider using dependency injection or context managers

---

## Positive Observations

The codebase has many **good practices**:

✅ Clear separation between game logic (`game/`) and rendering (`client/`)
✅ Comprehensive test coverage (199 tests)
✅ Good use of dataclasses and type hints
✅ Constants centralized in `shared/constants.py`
✅ Clear enum usage for game states
✅ Good documentation in module docstrings
✅ Consistent code formatting

---

## Priority Recommendations

### High Priority (Address Soon)
1. ✅ **COMPLETED** - Extract corner layout logic to eliminate duplication
2. ✅ **COMPLETED** - Clean up dead code and empty methods
3. ✅ **COMPLETED** - Add proper logging throughout codebase
4. ✅ **COMPLETED** - Create Position value object
5. Refactor `GameView` class - split into smaller components (1835 lines)

### Medium Priority (When Time Permits)
5. ✅ **COMPLETED** - Move magic numbers to constants
6. Create state machine for UI states
7. Refactor long methods (>50 lines)
8. Add `ActionResult` class for better error handling

### Low Priority (Nice to Have)
10. Consider creating ID wrapper types
11. Improve serialization with proper library
12. Reduce circular dependency risks
13. Extract board initialization logic

---

## Notes

- This document should be updated as issues are addressed
- Mark items as completed (✅) when resolved
- Add new code smells as they are discovered
- Link to specific commits that resolve issues
