"""
Unit tests for MysterySquareSystem.
"""

from unittest.mock import MagicMock

from game.mystery_square import MysterySquareSystem, MysteryEventResult
from game.token import Token
from shared.enums import MysteryEffect


class TestMysteryEventResult:
    """Test cases for MysteryEventResult dataclass."""

    def test_creation(self):
        """Test creating a MysteryEventResult."""
        result = MysteryEventResult(
            effect=MysteryEffect.HEAL,
            token_id=1,
            old_position=(5, 5),
            new_position=(5, 5),
            old_health=5,
            new_health=10,
        )
        assert result.effect == MysteryEffect.HEAL
        assert result.token_id == 1
        assert result.old_position == (5, 5)
        assert result.new_position == (5, 5)
        assert result.old_health == 5
        assert result.new_health == 10

    def test_to_dict_heal(self):
        """Test serialization for heal effect."""
        result = MysteryEventResult(
            effect=MysteryEffect.HEAL,
            token_id=1,
            old_position=(5, 5),
            new_position=(5, 5),
            old_health=5,
            new_health=10,
        )
        data = result.to_dict()
        assert data["effect"] == "HEAL"
        assert data["token_id"] == 1
        assert data["old_position"] == [5, 5]
        assert data["new_position"] == [5, 5]
        assert data["old_health"] == 5
        assert data["new_health"] == 10

    def test_to_dict_teleport(self):
        """Test serialization for teleport effect."""
        result = MysteryEventResult(
            effect=MysteryEffect.TELEPORT,
            token_id=2,
            old_position=(10, 10),
            new_position=(2, 2),
            old_health=8,
            new_health=8,
        )
        data = result.to_dict()
        assert data["effect"] == "TELEPORT"
        assert data["token_id"] == 2
        assert data["old_position"] == [10, 10]
        assert data["new_position"] == [2, 2]
        assert data["old_health"] == 8
        assert data["new_health"] == 8

    def test_repr_heal(self):
        """Test string representation for heal effect."""
        result = MysteryEventResult(
            effect=MysteryEffect.HEAL,
            token_id=1,
            old_position=(5, 5),
            new_position=(5, 5),
            old_health=5,
            new_health=10,
        )
        assert "healed from 5 to 10" in repr(result)
        assert "Token 1" in repr(result)

    def test_repr_teleport(self):
        """Test string representation for teleport effect."""
        result = MysteryEventResult(
            effect=MysteryEffect.TELEPORT,
            token_id=2,
            old_position=(10, 10),
            new_position=(2, 2),
            old_health=8,
            new_health=8,
        )
        assert "teleported from (10, 10) to (2, 2)" in repr(result)
        assert "Token 2" in repr(result)


class TestMysterySquareSystemTrigger:
    """Test cases for trigger_mystery_event."""

    def test_trigger_heal_effect(self, monkeypatch):
        """Test that heal effect restores token to full health."""
        # Force heads (heal)
        monkeypatch.setattr("random.choice", lambda x: True)

        token = Token(id=1, player_id="p1", health=5, max_health=10, position=(5, 5))
        board = MagicMock()

        result = MysterySquareSystem.trigger_mystery_event(token, board, player_index=0)

        assert result.effect == MysteryEffect.HEAL
        assert result.token_id == 1
        assert result.old_health == 5
        assert result.new_health == 10
        assert token.health == 10
        assert result.old_position == result.new_position  # Position unchanged

    def test_trigger_teleport_effect(self, monkeypatch):
        """Test that teleport effect moves token to deployment area."""
        # Force tails (teleport)
        monkeypatch.setattr("random.choice", lambda x: False)

        token = Token(id=1, player_id="p1", health=8, max_health=10, position=(10, 10))
        board = MagicMock()
        board.get_deployable_positions.return_value = [(2, 2), (2, 3), (3, 2)]

        # Mock cell as unoccupied
        cell = MagicMock()
        cell.is_occupied.return_value = False
        board.get_cell_at.return_value = cell

        result = MysterySquareSystem.trigger_mystery_event(token, board, player_index=0)

        assert result.effect == MysteryEffect.TELEPORT
        assert result.token_id == 1
        assert result.old_position == (10, 10)
        assert result.new_position == (2, 2)  # First empty position
        assert token.position == (2, 2)

    def test_teleport_finds_first_empty_cell(self, monkeypatch):
        """Test that teleport finds the first empty cell in deployment area."""
        monkeypatch.setattr("random.choice", lambda x: False)

        token = Token(id=1, player_id="p1", health=8, max_health=10, position=(10, 10))
        board = MagicMock()
        board.get_deployable_positions.return_value = [(2, 2), (2, 3), (3, 2), (3, 3)]

        # First two cells occupied, third is empty
        def mock_get_cell(pos):
            cell = MagicMock()
            if pos in [(2, 2), (2, 3)]:
                cell.is_occupied.return_value = True
            else:
                cell.is_occupied.return_value = False
            return cell

        board.get_cell_at.side_effect = mock_get_cell

        result = MysterySquareSystem.trigger_mystery_event(token, board, player_index=0)

        assert result.new_position == (3, 2)  # First empty cell

    def test_teleport_fallback_to_corner(self, monkeypatch):
        """Test that teleport falls back to corner when all deployment cells occupied."""
        monkeypatch.setattr("random.choice", lambda x: False)

        token = Token(id=1, player_id="p1", health=8, max_health=10, position=(10, 10))
        board = MagicMock()
        board.get_deployable_positions.return_value = [(2, 2), (2, 3)]
        board.get_starting_position.return_value = (0, 0)

        # All cells occupied
        cell = MagicMock()
        cell.is_occupied.return_value = True
        board.get_cell_at.return_value = cell

        result = MysterySquareSystem.trigger_mystery_event(token, board, player_index=0)

        assert result.new_position == (0, 0)  # Corner fallback
        board.get_starting_position.assert_called_once_with(0)

    def test_trigger_preserves_health_on_teleport(self, monkeypatch):
        """Test that teleport doesn't change token health."""
        monkeypatch.setattr("random.choice", lambda x: False)

        token = Token(id=1, player_id="p1", health=6, max_health=10, position=(10, 10))
        board = MagicMock()
        board.get_deployable_positions.return_value = [(2, 2)]

        cell = MagicMock()
        cell.is_occupied.return_value = False
        board.get_cell_at.return_value = cell

        result = MysterySquareSystem.trigger_mystery_event(token, board, player_index=0)

        assert result.effect == MysteryEffect.TELEPORT
        assert result.old_health == 6
        assert result.new_health == 6  # Health unchanged
        assert token.health == 6

    def test_trigger_uses_player_index_for_deployment(self, monkeypatch):
        """Test that player_index is used to get deployment positions."""
        monkeypatch.setattr("random.choice", lambda x: False)

        token = Token(id=1, player_id="p1", health=8, max_health=10, position=(10, 10))
        board = MagicMock()
        board.get_deployable_positions.return_value = [(20, 20)]

        cell = MagicMock()
        cell.is_occupied.return_value = False
        board.get_cell_at.return_value = cell

        MysterySquareSystem.trigger_mystery_event(token, board, player_index=2)

        board.get_deployable_positions.assert_called_once_with(2)


class TestMysterySquareSystemCanTrigger:
    """Test cases for can_trigger_mystery_event."""

    def test_alive_token_can_trigger(self):
        """Test that alive tokens can trigger mystery events."""
        token = Token(id=1, player_id="p1", health=5, max_health=10, position=(5, 5))
        assert token.is_alive is True
        assert MysterySquareSystem.can_trigger_mystery_event(token) is True

    def test_dead_token_cannot_trigger(self):
        """Test that dead tokens cannot trigger mystery events."""
        token = Token(id=1, player_id="p1", health=0, max_health=10, position=(5, 5))
        token.is_alive = False
        assert MysterySquareSystem.can_trigger_mystery_event(token) is False


class TestMysterySquareSystemDescriptions:
    """Test cases for description methods."""

    def test_get_effect_description_heal(self):
        """Test description for heal effect."""
        desc = MysterySquareSystem.get_effect_description(MysteryEffect.HEAL)
        assert desc == "Healed to full health!"

    def test_get_effect_description_teleport(self):
        """Test description for teleport effect."""
        desc = MysterySquareSystem.get_effect_description(MysteryEffect.TELEPORT)
        assert desc == "Teleported back to deployment area!"

    def test_get_effect_description_unknown(self):
        """Test description for unknown effect."""

        # Create a mock effect not in the enum
        class MockEffect:
            name = "UNKNOWN"

        desc = MysterySquareSystem.get_effect_description(MockEffect())
        assert desc == "Unknown effect"

    def test_simulate_effect_heal(self):
        """Test simulation description for heal."""
        desc = MysterySquareSystem.simulate_effect(MysteryEffect.HEAL)
        assert "healed to maximum health" in desc

    def test_simulate_effect_teleport(self):
        """Test simulation description for teleport."""
        desc = MysterySquareSystem.simulate_effect(MysteryEffect.TELEPORT)
        assert "sent back to deployment area" in desc

    def test_simulate_effect_unknown(self):
        """Test simulation description for unknown effect."""

        class MockEffect:
            name = "UNKNOWN"

        desc = MysterySquareSystem.simulate_effect(MockEffect())
        assert desc == "Unknown"


class TestMysterySquareEdgeCases:
    """Test edge cases and error conditions."""

    def test_heal_already_full_health(self, monkeypatch):
        """Test healing a token already at full health."""
        monkeypatch.setattr("random.choice", lambda x: True)

        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        board = MagicMock()

        result = MysterySquareSystem.trigger_mystery_event(token, board, player_index=0)

        assert result.effect == MysteryEffect.HEAL
        assert result.old_health == 10
        assert result.new_health == 10  # No change

    def test_teleport_to_same_position(self, monkeypatch):
        """Test teleport when token is already in deployment area."""
        monkeypatch.setattr("random.choice", lambda x: False)

        token = Token(id=1, player_id="p1", health=8, max_health=10, position=(2, 2))
        board = MagicMock()
        board.get_deployable_positions.return_value = [(2, 2), (2, 3)]

        # First cell is where token already is (occupied by this token)
        cell = MagicMock()
        cell.is_occupied.return_value = True
        board.get_cell_at.return_value = cell
        board.get_starting_position.return_value = (0, 0)

        result = MysterySquareSystem.trigger_mystery_event(token, board, player_index=0)

        # Should skip occupied (2,2) and try next, or fallback
        assert result.old_position == (2, 2)

    def test_random_distribution(self):
        """Test that random choice is called with correct options."""
        import random

        token = Token(id=1, player_id="p1", health=5, max_health=10, position=(5, 5))
        board = MagicMock()

        # Track what random.choice was called with
        called_with = []
        original_choice = random.choice

        def mock_choice(options):
            called_with.append(options)
            return original_choice(options)

        random.choice = mock_choice
        try:
            MysterySquareSystem.trigger_mystery_event(token, board, player_index=0)
        finally:
            random.choice = original_choice

        assert called_with == [[True, False]]
