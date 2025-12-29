"""
Unit tests for GameState.create_game() method.
"""
import pytest
from game.game_state import GameState
from shared.enums import PlayerColor


class TestGameCreation:
    """Test cases for GameState.create_game() method."""

    def test_create_game_2_players(self):
        """Test creating a game with 2 players."""
        game_state = GameState.create_game(2)

        assert len(game_state.players) == 2
        assert "player_0" in game_state.players
        assert "player_1" in game_state.players
        
        # Check player properties
        player_0 = game_state.players["player_0"]
        player_1 = game_state.players["player_1"]
        
        assert player_0.name == "Player 1"
        assert player_0.color == PlayerColor.CYAN
        assert player_1.name == "Player 2"
        assert player_1.color == PlayerColor.MAGENTA

    def test_create_game_4_players(self):
        """Test creating a game with 4 players."""
        game_state = GameState.create_game(4)

        assert len(game_state.players) == 4
        assert "player_0" in game_state.players
        assert "player_1" in game_state.players
        assert "player_2" in game_state.players
        assert "player_3" in game_state.players
        
        # Check player colors
        assert game_state.players["player_0"].color == PlayerColor.CYAN
        assert game_state.players["player_1"].color == PlayerColor.MAGENTA
        assert game_state.players["player_2"].color == PlayerColor.YELLOW
        assert game_state.players["player_3"].color == PlayerColor.GREEN

    def test_create_game_invalid_player_count(self):
        """Test that invalid player counts raise ValueError."""
        with pytest.raises(ValueError, match="Number of players must be between 2 and 4"):
            GameState.create_game(1)
        
        with pytest.raises(ValueError, match="Number of players must be between 2 and 4"):
            GameState.create_game(5)

    def test_create_game_initial_state(self):
        """Test that created game has correct initial state."""
        game_state = GameState.create_game(2)

        assert game_state.phase.name == "SETUP"
        assert game_state.turn_number == 0
        assert game_state.current_turn_player_id is None
        assert game_state.winner_id is None
        assert len(game_state.tokens) == 0

    def test_create_game_returns_game_state_instance(self):
        """Test that create_game returns a GameState instance."""
        game_state = GameState.create_game(2)
        assert isinstance(game_state, GameState)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
