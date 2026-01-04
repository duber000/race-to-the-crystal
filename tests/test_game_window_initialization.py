"""
Tests for GameView initialization to prevent AttributeError issues.

Note: These tests require an active display/window and are skipped in headless environments.
"""
import pytest
import arcade
from unittest.mock import Mock, MagicMock
from game.game_state import GameState
from client.game_window import GameView


# Skip these tests if no display is available (headless environment)
def _can_create_window():
    """Check if we can create an arcade window."""
    try:
        # Try to create a minimal window
        window = arcade.Window(100, 100, "test", visible=False)
        window.close()
        return True
    except Exception:
        return False


requires_display = pytest.mark.skipif(
    not _can_create_window(),
    reason="Requires display/window (skipped in headless environment)"
)


@pytest.fixture
def arcade_window():
    """Create an arcade window for testing GameView."""
    window = arcade.Window(800, 600, "Test Window", visible=False)
    yield window
    window.close()


class TestGameViewInitialization:
    """Test GameView initialization and attribute safety."""

    @requires_display
    def test_game_view_initialization(self, arcade_window):
        """Test that GameView can be initialized without errors."""
        # Create a properly initialized game state
        game_state = GameState.create_game(2)
        game_state.start_game()  # Start the game to initialize all components

        # Create GameView (this should not raise AttributeError)
        try:
            game_view = GameView(game_state, start_in_3d=False)

            # Show the view to trigger on_show_view() which initializes controllers
            arcade_window.show_view(game_view)

            # Verify that critical attributes are set after on_show_view()
            assert hasattr(game_view, 'camera_controller')
            assert game_view.camera_controller is not None
            assert hasattr(game_view.camera_controller, 'camera_mode')
            assert hasattr(game_view.camera_controller, 'mouse_look_active')
            assert hasattr(game_view, 'renderer_3d')
            assert hasattr(game_view, 'ui_manager')

            # Verify attribute values
            assert game_view.camera_controller.camera_mode == "2D"

        except AttributeError as e:
            pytest.fail(f"GameView initialization failed with AttributeError: {e}")

    @requires_display
    def test_event_handlers_safe_before_initialization(self, arcade_window):
        """Test that event handlers can handle calls before on_show_view is called."""
        # Create a properly initialized game state
        game_state = GameState.create_game(2)
        game_state.start_game()  # Start the game to initialize all components

        # Create GameView but DON'T call show_view yet
        # This simulates the state before on_show_view() is called
        game_view = GameView(game_state, start_in_3d=False)

        try:
            # These should not raise AttributeError even when called before on_show_view()
            # The event handlers check for input_handler existence before accessing it
            game_view.on_resize(800, 600)  # Should handle missing ui_manager gracefully
            game_view.on_mouse_motion(100, 100, 10, 10)  # Should handle missing input_handler gracefully
            game_view.on_mouse_press(100, 100, 1, 0)  # Should handle missing input_handler gracefully
            game_view.on_mouse_release(100, 100, 1, 0)  # Should handle missing input_handler gracefully
            game_view.on_mouse_scroll(100, 100, 0, 1.0)  # Should handle missing input_handler gracefully
            game_view.on_key_press(ord('v'), 0)  # Should handle missing input_handler gracefully
            game_view.on_text("a")  # Should handle missing input_handler gracefully

        except AttributeError as e:
            pytest.fail(f"Event handler failed with AttributeError before on_show_view: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
