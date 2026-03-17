"""
Unit tests for GameAPI facade.
"""

import pytest
from unittest.mock import MagicMock, patch

from game.api import GameAPI
from game.game_state import GameState
from shared.enums import GamePhase, TurnPhase, PlayerColor


class TestGameAPICreation:
    """Test cases for GameAPI initialization."""

    def test_api_creation(self):
        """Test creating GameAPI instance."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)

        api = GameAPI(game_state, "p1")

        assert api.game_state == game_state
        assert api.player_id == "p1"
        assert api.executor is not None

    def test_api_creation_with_nonexistent_player(self):
        """Test creating API for player not in game."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)

        # Should still create, but operations will fail
        api = GameAPI(game_state, "nonexistent")
        assert api.player_id == "nonexistent"


class TestGameAPIObservation:
    """Test cases for observation methods."""

    def test_observe_returns_string(self):
        """Test that observe() returns a string."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        report = api.observe()

        assert isinstance(report, str)
        assert len(report) > 0

    def test_observe_contains_game_info(self):
        """Test that observe contains game information."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        report = api.observe()

        # Should contain turn info
        assert "Turn" in report or "turn" in report

    def test_actions_returns_list(self):
        """Test that actions() returns a list."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        actions = api.actions()

        assert isinstance(actions, list)

    def test_actions_with_phase_returns_dict(self):
        """Test that actions_with_phase() returns a dict."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        result = api.actions_with_phase()

        assert isinstance(result, dict)
        assert "phase" in result
        assert "actions" in result

    def test_board_map_returns_string(self):
        """Test that board_map() returns ASCII string."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        board = api.board_map()

        assert isinstance(board, str)
        assert len(board) > 0

    def test_describe_returns_string(self):
        """Test that describe() returns a string."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        description = api.describe()

        assert isinstance(description, str)
        assert len(description) > 0

    def test_victory_conditions_returns_string(self):
        """Test that victory_conditions() returns a string."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        conditions = api.victory_conditions()

        assert isinstance(conditions, str)
        assert len(conditions) > 0


class TestGameAPIActions:
    """Test cases for action methods."""

    def test_move_valid_token(self):
        """Test moving a valid token."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")

        # Get a deployed token
        player = game_state.get_player("p1")
        token_id = player.token_ids[0]
        token = game_state.get_token(token_id)
        old_pos = token.position

        # Try to move to adjacent cell
        new_x, new_y = old_pos[0] + 1, old_pos[1]
        result = api.move(token_id, new_x, new_y)

        assert result.success is True
        assert token.position == (new_x, new_y)

    def test_move_invalid_token(self):
        """Test moving a non-existent token."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        result = api.move(9999, 10, 10)

        assert result.success is False

    def test_attack_adjacent_token(self):
        """Test attacking an adjacent enemy token."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.add_player("p2", "Player 2", PlayerColor.MAGENTA)
        game_state.start_game()

        api = GameAPI(game_state, "p1")

        # Get tokens
        p1_token = game_state.get_token(game_state.get_player("p1").token_ids[0])
        p2_token = game_state.get_token(game_state.get_player("p2").token_ids[0])

        # Position tokens adjacent to each other
        p2_token.move_to((p1_token.position[0] + 1, p1_token.position[1]))

        # Try to attack - should fail in MOVEMENT phase
        result = api.attack(p1_token.id, p2_token.id)

        # Verify it fails with wrong_phase error
        assert result.success is False
        assert "wrong_phase" in result.message

    def test_attack_non_adjacent_token_fails(self):
        """Test attacking a non-adjacent token fails."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.add_player("p2", "Player 2", PlayerColor.MAGENTA)
        game_state.start_game()

        api = GameAPI(game_state, "p1")

        p1_token = game_state.get_token(game_state.get_player("p1").token_ids[0])
        p2_token = game_state.get_token(game_state.get_player("p2").token_ids[0])

        # Tokens are far apart
        result = api.attack(p1_token.id, p2_token.id)

        assert result.success is False

    def test_deploy_token(self):
        """Test deploying a token from reserve."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")

        # Deploy to a valid position in deployment area
        result = api.deploy(8, 2, 2)

        assert result.success is True
        assert "new_token_id" in result.data

    def test_deploy_invalid_position(self):
        """Test deploying to invalid position fails."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")

        # Try to deploy outside deployment area
        result = api.deploy(8, 20, 20)

        assert result.success is False

    def test_end_turn(self):
        """Test ending turn."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        current_turn = game_state.current_turn_player_id
        api = GameAPI(game_state, current_turn)

        result = api.end_turn()

        assert result.success is True
        assert "turn_number" in result.data


class TestGameAPIUtility:
    """Test cases for utility methods."""

    def test_is_my_turn_true(self):
        """Test is_my_turn when it is player's turn."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")

        # p1 should be first player
        assert api.is_my_turn() is True

    def test_is_my_turn_false(self):
        """Test is_my_turn when it's not player's turn."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.add_player("p2", "Player 2", PlayerColor.MAGENTA)
        game_state.start_game()

        # p1 is current player
        api = GameAPI(game_state, "p2")

        assert api.is_my_turn() is False

    def test_get_phase_movement(self):
        """Test get_phase returns MOVEMENT."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        phase = api.get_phase()

        assert phase == "MOVEMENT"

    def test_get_phase_not_playing(self):
        """Test get_phase when game not started."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        # Don't start game

        api = GameAPI(game_state, "p1")
        phase = api.get_phase()

        assert phase == "SETUP"

    def test_get_my_tokens(self):
        """Test getting player's tokens."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        tokens = api.get_my_tokens()

        assert isinstance(tokens, list)
        assert len(tokens) == 20  # All tokens

    def test_get_my_tokens_nonexistent_player(self):
        """Test get_my_tokens for non-existent player."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "nonexistent")
        tokens = api.get_my_tokens()

        assert tokens == []

    def test_get_deployed_tokens(self):
        """Test getting only deployed tokens."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        tokens = api.get_deployed_tokens()

        assert isinstance(tokens, list)
        # Should have 3 deployed tokens (auto-deployed at start)
        assert len(tokens) == 3

    def test_get_reserve_counts(self):
        """Test getting reserve token counts."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")
        counts = api.get_reserve_counts()

        assert isinstance(counts, dict)
        # Should have counts for each health value
        assert all(health in counts for health in [10, 8, 6, 4])


class TestGameAPIEdgeCases:
    """Test edge cases and error conditions."""

    def test_move_when_not_my_turn(self):
        """Test moving when it's not player's turn."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.add_player("p2", "Player 2", PlayerColor.MAGENTA)
        game_state.start_game()

        # p1's turn, but we use p2's API
        api = GameAPI(game_state, "p2")

        p2_token = game_state.get_token(game_state.get_player("p2").token_ids[0])
        result = api.move(p2_token.id, 10, 10)

        assert result.success is False

    def test_attack_own_token_fails(self):
        """Test attacking own token fails."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")

        # Get two of player's tokens
        player = game_state.get_player("p1")
        token1 = game_state.get_token(player.token_ids[0])
        token2 = game_state.get_token(player.token_ids[1])

        # Position them adjacent
        token2.move_to((token1.position[0] + 1, token1.position[1]))

        result = api.attack(token1.id, token2.id)

        # Should fail - can't attack own tokens
        assert result.success is False

    def test_deploy_invalid_health_value(self):
        """Test deploying with invalid health value fails."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        game_state.start_game()

        api = GameAPI(game_state, "p1")

        # Invalid health value
        result = api.deploy(5, 2, 2)

        assert result.success is False

    def test_actions_when_game_not_started(self):
        """Test getting actions when game hasn't started."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        # Don't start game

        api = GameAPI(game_state, "p1")
        actions = api.actions()

        # Should return empty list or NOT_PLAYING phase
        assert isinstance(actions, list)
