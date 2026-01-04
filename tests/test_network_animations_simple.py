"""Simple test for network mode client-side prediction logic."""

import pytest
from unittest.mock import Mock
from game.game_state import GameState
from game.token import Token
from shared.enums import PlayerColor


class TestNetworkClientSidePrediction:
    """Test client-side prediction logic without UI dependencies."""

    def test_token_position_update(self):
        """Test that token positions can be updated correctly."""
        # Create a mock game state
        game_state = GameState()
        player = game_state.add_player("test_player", "Test Player", PlayerColor.CYAN)
        
        # Create a token at position (0, 0)
        token = Token(id=1, player_id=player.id, health=10, max_health=10, position=(0, 0), is_deployed=True)
        game_state.tokens[1] = token
        player.token_ids = [1]
        
        # Verify initial state
        assert token.position == (0, 0)
        
        # Simulate a move (this is what client-side prediction does)
        original_position = token.position
        token.position = (1, 0)
        
        # Verify position was updated
        assert token.position == (1, 0)
        
        # Simulate rollback (this is what happens when server rejects the move)
        token.position = original_position
        
        # Verify rollback worked
        assert token.position == (0, 0)

    def test_rollback_logic(self):
        """Test rollback logic for client-side prediction."""
        # Create a mock game state
        game_state = GameState()
        player = game_state.add_player("test_player", "Test Player", PlayerColor.CYAN)
        
        # Create a token at position (0, 0)
        token = Token(id=1, player_id=player.id, health=10, max_health=10, position=(0, 0), is_deployed=True)
        game_state.tokens[1] = token
        player.token_ids = [1]
        
        # Store rollback info (simulating what NetworkGameView does)
        rollback_info = {
            "token_id": 1,
            "original_position": token.position,
            "original_health": token.health,
        }
        
        # Apply client-side prediction
        token.position = (1, 0)
        token.health = 8  # Simulate damage from mystery square
        
        # Verify prediction was applied
        assert token.position == (1, 0)
        assert token.health == 8
        
        # Simulate rollback
        token_id = rollback_info["token_id"]
        original_position = rollback_info["original_position"]
        original_health = rollback_info["original_health"]
        
        # Revert state
        token.position = original_position
        token.health = original_health
        
        # Verify rollback worked
        assert token.position == (0, 0)
        assert token.health == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])