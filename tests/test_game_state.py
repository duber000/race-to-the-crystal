"""
Unit tests for GameState class.
"""
import pytest
import json
from game.game_state import GameState
from shared.enums import GamePhase, PlayerColor


class TestGameState:
    """Test cases for GameState class."""

    def test_game_state_creation(self):
        """Test creating a game state."""
        state = GameState()

        assert state.board is not None
        assert len(state.players) == 0
        assert len(state.tokens) == 0
        assert state.current_turn_player_id is None
        assert state.turn_number == 0
        assert state.phase == GamePhase.SETUP
        assert state.winner_id is None

    def test_add_player(self):
        """Test adding a player to the game."""
        state = GameState()

        player = state.add_player("p1", "Alice", PlayerColor.CYAN)

        assert player.id == "p1"
        assert player.name == "Alice"
        assert player.color == PlayerColor.CYAN
        assert "p1" in state.players
        assert state.players["p1"] == player

    def test_add_multiple_players(self):
        """Test adding multiple players."""
        state = GameState()

        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.add_player("p2", "Bob", PlayerColor.MAGENTA)
        state.add_player("p3", "Charlie", PlayerColor.YELLOW)
        state.add_player("p4", "Diana", PlayerColor.GREEN)

        assert len(state.players) == 4

    def test_remove_player(self):
        """Test removing a player."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)

        state.remove_player("p1")

        assert "p1" not in state.players

    def test_create_tokens_for_player(self):
        """Test creating tokens for a player."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)

        tokens = state.create_tokens_for_player("p1")

        assert len(tokens) == 20  # 5 of each health value (10, 8, 6, 4)
        assert len(state.tokens) == 20

        # Check token health distribution
        health_counts = {}
        for token in tokens:
            health = token.max_health
            health_counts[health] = health_counts.get(health, 0) + 1

        assert health_counts[10] == 5
        assert health_counts[8] == 5
        assert health_counts[6] == 5
        assert health_counts[4] == 5

    def test_create_tokens_for_player_invalid(self):
        """Test creating tokens for non-existent player raises error."""
        state = GameState()

        with pytest.raises(ValueError):
            state.create_tokens_for_player("nonexistent")

    def test_create_tokens_assigns_to_player(self):
        """Test that created tokens are assigned to player."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)

        state.create_tokens_for_player("p1")

        player = state.get_player("p1")
        assert len(player.token_ids) == 20

    def test_create_tokens_starting_position(self):
        """Test that tokens start at correct position."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)

        tokens = state.create_tokens_for_player("p1")

        # Player 1 (CYAN, color value 0) starts at (0, 0)
        expected_pos = state.board.get_starting_position(0)
        for token in tokens:
            assert token.position == expected_pos

    def test_get_token(self):
        """Test getting token by ID."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        tokens = state.create_tokens_for_player("p1")

        token_id = tokens[0].id
        retrieved = state.get_token(token_id)

        assert retrieved is not None
        assert retrieved.id == token_id

    def test_get_token_invalid(self):
        """Test getting non-existent token returns None."""
        state = GameState()

        assert state.get_token(999) is None

    def test_get_player(self):
        """Test getting player by ID."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)

        player = state.get_player("p1")

        assert player is not None
        assert player.id == "p1"

    def test_get_player_invalid(self):
        """Test getting non-existent player returns None."""
        state = GameState()

        assert state.get_player("nonexistent") is None

    def test_get_tokens_at_position(self):
        """Test getting all tokens at a position."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        tokens = state.create_tokens_for_player("p1")

        # All tokens start at same position
        start_pos = tokens[0].position
        tokens_at_pos = state.get_tokens_at_position(start_pos)

        assert len(tokens_at_pos) == 20

    def test_get_player_tokens(self):
        """Test getting deployed tokens for a player."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.add_player("p2", "Bob", PlayerColor.MAGENTA)

        state.create_tokens_for_player("p1")
        state.create_tokens_for_player("p2")

        # Initially, no tokens are deployed
        p1_tokens = state.get_player_tokens("p1")
        assert len(p1_tokens) == 0

        # Deploy some tokens for p1
        health_values = [10, 8, 6, 4, 10]  # Deploy variety of token types
        for i, health in enumerate(health_values):
            state.deploy_token("p1", health, (i, i))

        # Now should get 5 deployed tokens
        p1_tokens = state.get_player_tokens("p1")
        assert len(p1_tokens) == 5

        # All p1 tokens should belong to p1
        for token in p1_tokens:
            assert token.player_id == "p1"
            assert token.is_deployed is True
            assert token.is_alive is True

    def test_move_token(self):
        """Test moving a token."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        tokens = state.create_tokens_for_player("p1")

        token = tokens[0]
        old_pos = token.position
        new_pos = (5, 5)

        success = state.move_token(token.id, new_pos)

        assert success is True
        assert token.position == new_pos
        assert token.id in state.board.get_cell_at(new_pos).occupants
        assert len(state.board.get_cell_at(old_pos).occupants) == 0

    def test_move_token_invalid(self):
        """Test moving non-existent token fails."""
        state = GameState()

        success = state.move_token(999, (5, 5))

        assert success is False

    def test_move_token_dead(self):
        """Test moving dead token fails."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        tokens = state.create_tokens_for_player("p1")

        token = tokens[0]
        token.is_alive = False

        success = state.move_token(token.id, (5, 5))

        assert success is False

    def test_remove_token(self):
        """Test removing a dead token."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        tokens = state.create_tokens_for_player("p1")

        token = tokens[0]
        token_id = token.id
        position = token.position

        state.remove_token(token_id)

        assert token.is_alive is False
        assert len(state.board.get_cell_at(position).occupants) == 0

        player = state.get_player("p1")
        assert token_id not in player.token_ids

    def test_start_game(self):
        """Test starting the game."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.add_player("p2", "Bob", PlayerColor.MAGENTA)

        state.start_game()

        assert state.phase == GamePhase.PLAYING
        assert state.turn_number == 1
        assert state.current_turn_player_id is not None
        assert len(state.tokens) == 40  # 20 per player

    def test_start_game_sets_first_player(self):
        """Test that starting game sets first player."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)

        state.start_game()

        assert state.current_turn_player_id == "p1"

    def test_start_game_auto_deploys_three_tokens(self):
        """Test that starting game auto-deploys exactly 3 tokens per player."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.add_player("p2", "Bob", PlayerColor.MAGENTA)

        state.start_game()

        # Each player should have exactly 3 deployed tokens
        p1_deployed = state.get_player_tokens("p1")
        p2_deployed = state.get_player_tokens("p2")

        assert len(p1_deployed) == 3, f"Player 1 should have 3 deployed tokens, got {len(p1_deployed)}"
        assert len(p2_deployed) == 3, f"Player 2 should have 3 deployed tokens, got {len(p2_deployed)}"

        # Check that 17 tokens remain in reserve for each player
        p1_reserve = state.get_reserve_tokens("p1")
        p2_reserve = state.get_reserve_tokens("p2")

        assert len(p1_reserve) == 17, f"Player 1 should have 17 reserve tokens, got {len(p1_reserve)}"
        assert len(p2_reserve) == 17, f"Player 2 should have 17 reserve tokens, got {len(p2_reserve)}"

    def test_end_turn(self):
        """Test ending turn and advancing to next player."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.add_player("p2", "Bob", PlayerColor.MAGENTA)

        state.start_game()
        assert state.current_turn_player_id == "p1"

        state.end_turn()
        assert state.current_turn_player_id == "p2"

        state.end_turn()
        assert state.current_turn_player_id == "p1"  # Wrapped around

    def test_end_turn_increments_turn_number(self):
        """Test that turn number increments when wrapping around."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.add_player("p2", "Bob", PlayerColor.MAGENTA)

        state.start_game()
        assert state.turn_number == 1

        state.end_turn()  # p1 -> p2
        assert state.turn_number == 1

        state.end_turn()  # p2 -> p1 (new round)
        assert state.turn_number == 2

    def test_end_turn_skips_inactive_players(self):
        """Test that end_turn skips inactive players."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.add_player("p2", "Bob", PlayerColor.MAGENTA)
        state.add_player("p3", "Charlie", PlayerColor.YELLOW)

        state.start_game()

        # Deactivate p2
        state.players["p2"].is_active = False

        state.end_turn()
        # Should skip p2 and go to p3
        assert state.current_turn_player_id == "p3"

    def test_set_winner(self):
        """Test setting the game winner."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.start_game()

        state.set_winner("p1")

        assert state.winner_id == "p1"
        assert state.phase == GamePhase.ENDED

    def test_game_state_serialization(self):
        """Test serializing game state to dict."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.create_tokens_for_player("p1")

        data = state.to_dict()

        assert "board" in data
        assert "players" in data
        assert "tokens" in data
        assert data["phase"] == "SETUP"
        assert data["turn_number"] == 0

    def test_game_state_json_serialization(self):
        """Test serializing game state to JSON."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)

        json_str = state.to_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert "board" in data
        assert "players" in data

    def test_game_state_deserialization(self):
        """Test deserializing game state from dict."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.add_player("p2", "Bob", PlayerColor.MAGENTA)
        state.start_game()  # Creates tokens for both players

        # Serialize
        data = state.to_dict()

        # Deserialize
        restored = GameState.from_dict(data)

        assert len(restored.players) == 2
        assert len(restored.tokens) == 40  # 20 per player
        assert restored.phase == GamePhase.PLAYING
        assert restored.turn_number == 1

    def test_game_state_json_roundtrip(self):
        """Test full JSON serialization roundtrip."""
        state = GameState()
        state.add_player("p1", "Alice", PlayerColor.CYAN)
        state.create_tokens_for_player("p1")
        state.start_game()

        # Serialize to JSON
        json_str = state.to_json()

        # Deserialize from JSON
        restored = GameState.from_json(json_str)

        assert len(restored.players) == len(state.players)
        assert len(restored.tokens) == len(state.tokens)
        assert restored.phase == state.phase
        assert restored.turn_number == state.turn_number
