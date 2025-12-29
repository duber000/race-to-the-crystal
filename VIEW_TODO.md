# GameWindow Refactoring TODO

## Current Issue

The current `GameWindow` class inherits from `arcade.Window`, which causes problems when trying to transition from the menu window to the game window. This results in crashes when clicking "Local Hot-Seat Game" in the menu.

## Current Architecture Problems

1. **Window Transition Issues**: When closing the menu window and opening the game window, the Arcade event loop gets confused about which window is active.

2. **Inconsistent Architecture**: Network games use `NetworkGameView` (which inherits from `arcade.View`) and show it within the existing window, while local games create a new `GameWindow` (which inherits from `arcade.Window`).

3. **Complex Window Management**: The current workaround uses `arcade.schedule_once()` to defer window transitions, which is fragile and not the intended way to handle this in Arcade.

## Proposed Solution

Refactor `GameWindow` to inherit from `arcade.View` instead of `arcade.Window`. This would make it consistent with how network games work.

## Benefits of View-Based Architecture

1. **Smooth Transitions**: No need to close and reopen windows - just show/hide views within the same window.

2. **Consistency**: Both local and network games would use the same architectural pattern.

3. **Better User Experience**: No flickering or delays when transitioning between menu and game.

4. **Simpler Code**: Eliminates the need for complex window transition logic.

5. **Better Error Handling**: Views can be shown and hidden without affecting the event loop.

## Implementation Plan

### Phase 1: Research and Preparation
- Study how `NetworkGameView` is implemented
- Understand the differences between `arcade.Window` and `arcade.View`
- Identify all the methods and properties that would need to change

### Phase 2: Create View-Based GameWindow
- Create a new class `GameView` that inherits from `arcade.View`
- Move all game logic from `GameWindow` to `GameView`
- Adapt event handlers to work with the View architecture

### Phase 3: Update Menu System
- Modify `_start_local_game` to show the `GameView` instead of creating a new window
- Update the menu callbacks to work with the new architecture
- Ensure proper view transitions and cleanup

### Phase 4: Update 3D Rendering
- Adapt 3D rendering code to work within a View context
- Ensure camera and rendering systems work correctly
- Test both 2D and 3D modes

### Phase 5: Testing and Bug Fixing
- Test all game functionality in the new View-based architecture
- Fix any issues with input handling, rendering, or game logic
- Ensure performance is not degraded

### Phase 6: Cleanup and Documentation
- Remove old `GameWindow` class (or keep as fallback)
- Update documentation and comments
- Add examples of how to use the new View-based system

## Migration Strategy

To minimize disruption, we could:

1. **Keep both implementations temporarily**: Allow both window-based and view-based game modes during transition
2. **Feature flag**: Add a feature flag to enable the new view-based architecture
3. **Gradual migration**: Migrate one component at a time (e.g., start with 2D mode, then add 3D)
4. **Backward compatibility**: Ensure existing code still works during the transition

## Estimated Effort

This is a medium-to-large refactoring project that would likely take several days to implement and test thoroughly. The complexity comes from:

- The size of the `GameWindow` class (1500+ lines)
- The complexity of 3D rendering integration
- The need to maintain all existing functionality
- Testing across different platforms and configurations

## Priority

While this refactoring would improve code quality and consistency, it's not urgent since the current workaround (using `arcade.schedule_once()`) addresses the immediate crash issue. This should be considered a medium-priority technical debt item to be addressed when time permits.

## Related Files

- `client/game_window.py` - Main file to refactor
- `client/menu_main.py` - Menu system that needs updating
- `client/ui/network_game_view.py` - Reference implementation for View-based games
- `client/board_3d.py` - 3D rendering that may need adaptation
- `client/token_3d.py` - 3D token rendering
- `client/camera_3d.py` - 3D camera system

## Success Criteria

The refactoring will be considered successful when:

1. Local games can be started from the menu without crashes
2. All game functionality works identically to the current implementation
3. Performance is equal to or better than the current implementation
4. The code is cleaner and more maintainable
5. Both 2D and 3D modes work correctly
6. Network and local games use consistent architectural patterns