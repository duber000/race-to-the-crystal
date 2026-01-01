"""
Test chat widget integration in the game view.
"""

import pytest
import inspect


def test_chat_widget_import():
    """Test that the chat widget can be imported."""
    try:
        from client.ui.chat_widget import ChatWidget
        assert True
    except ImportError as e:
        pytest.fail(f"ChatWidget import failed: {e}")


def test_game_window_import():
    """Test that the game window can be imported with chat widget."""
    try:
        from client.game_window import GameView
        assert True
    except ImportError as e:
        pytest.fail(f"GameView import failed: {e}")


def test_chat_widget_in_game_view():
    """Test that GameView has chat_widget attribute."""
    from client.game_window import GameView
    
    # Check if chat_widget is in the __init__ method
    init_source = inspect.getsource(GameView.__init__)
    assert 'chat_widget' in init_source, "GameView should contain chat_widget initialization"


def test_chat_widget_draw_method():
    """Test that GameView calls chat_widget.draw()."""
    from client.game_window import GameView
    
    # Check if chat_widget.draw() is called in on_draw
    draw_source = inspect.getsource(GameView.on_draw)
    assert 'chat_widget.draw()' in draw_source, "GameView should call chat_widget.draw() in on_draw"


def test_chat_widget_input_handling():
    """Test that GameView handles chat widget input."""
    from client.game_window import GameView
    
    # Check if chat_widget input is handled in on_key_press
    key_press_source = inspect.getsource(GameView.on_key_press)
    assert 'chat_widget' in key_press_source, "GameView should handle chat_widget input in on_key_press"
    assert 'on_key_press' in key_press_source, "GameView should call chat_widget.on_key_press()"


def test_chat_widget_update_method():
    """Test that GameView updates chat widget."""
    from client.game_window import GameView
    
    # Check if chat_widget is updated in on_update
    update_source = inspect.getsource(GameView.on_update)
    assert 'chat_widget.update' in update_source, "GameView should update chat_widget in on_update"


def test_chat_widget_on_text_method():
    """Test that GameView has on_text method for chat input."""
    from client.game_window import GameView
    
    # Check if on_text method exists and handles chat widget
    assert hasattr(GameView, 'on_text'), "GameView should have on_text method"
    text_source = inspect.getsource(GameView.on_text)
    assert 'chat_widget' in text_source, "GameView.on_text should handle chat_widget input"