"""
Tests for GameWindow initialization to prevent AttributeError issues.
"""
import pytest
from unittest.mock import Mock
from game.game_state import GameState
from client.game_window import GameWindow


class TestGameWindowInitialization:
    """Test GameWindow initialization and attribute safety."""

    def test_game_window_initialization(self):
        """Test that GameWindow can be initialized without errors."""
        # Create a properly initialized game state
        game_state = GameState.create_game(2)
        game_state.start_game()  # Start the game to initialize all components
        
        # Create GameWindow (this should not raise AttributeError)
        try:
            window = GameWindow(game_state, width=800, height=600)
            
            # Verify that critical attributes are set
            assert hasattr(window, 'ui_manager')
            assert hasattr(window, 'camera_mode')
            assert hasattr(window, 'mouse_look_active')
            assert hasattr(window, 'board_3d')
            assert hasattr(window, 'shader_3d')
            
            # Verify attribute values
            assert window.camera_mode == "2D"
            assert window.ui_manager is not None
            
        except AttributeError as e:
            pytest.fail(f"GameWindow initialization failed with AttributeError: {e}")

    def test_event_handlers_safe_before_initialization(self):
        """Test that event handlers can handle calls before full initialization."""
        # Create a properly initialized game state
        game_state = GameState.create_game(2)
        game_state.start_game()  # Start the game to initialize all components
        
        # Create GameWindow
        window = GameWindow(game_state, width=800, height=600)
        
        # Test that event handlers don't crash when called with missing attributes
        # We'll temporarily remove the attributes to simulate the initialization race condition
        original_ui_manager = window.ui_manager
        original_camera_mode = window.camera_mode
        original_mouse_look_active = window.mouse_look_active
        
        try:
            # Simulate the race condition where attributes are not yet set
            delattr(window, 'ui_manager')
            delattr(window, 'camera_mode')
            delattr(window, 'mouse_look_active')
            
            # These should not raise AttributeError even if called during initialization
            window.on_resize(800, 600)  # Should handle missing ui_manager gracefully
            window.on_mouse_motion(100, 100, 10, 10)  # Should handle missing camera_mode gracefully
            window.on_mouse_press(100, 100, 1, 0)  # Should handle missing camera_mode gracefully
            window.on_mouse_release(100, 100, 1, 0)  # Should handle missing camera_mode gracefully
            window.on_key_press(ord('v'), 0)  # Should handle missing camera_mode gracefully
            
        except AttributeError as e:
            pytest.fail(f"Event handler failed with AttributeError: {e}")
        finally:
            # Restore the attributes
            window.ui_manager = original_ui_manager
            window.camera_mode = original_camera_mode
            window.mouse_look_active = original_mouse_look_active


if __name__ == "__main__":
    pytest.main([__file__, "-v"])