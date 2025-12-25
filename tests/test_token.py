"""
Unit tests for Token class.
"""
import pytest
from game.token import Token


class TestToken:
    """Test cases for Token class."""

    def test_token_creation(self):
        """Test creating a token."""
        token = Token(
            id=1,
            player_id="player1",
            health=10,
            max_health=10,
            position=(5, 5)
        )
        assert token.id == 1
        assert token.player_id == "player1"
        assert token.health == 10
        assert token.max_health == 10
        assert token.position == (5, 5)
        assert token.is_alive is True

    def test_movement_range(self):
        """Test that all tokens have movement range of 2."""
        token_10 = Token(id=1, player_id="p1", health=10, max_health=10, position=(0, 0))
        token_8 = Token(id=2, player_id="p1", health=8, max_health=8, position=(0, 0))
        token_6 = Token(id=3, player_id="p1", health=6, max_health=6, position=(0, 0))
        token_4 = Token(id=4, player_id="p1", health=4, max_health=4, position=(0, 0))

        assert token_10.movement_range == 2
        assert token_8.movement_range == 2
        assert token_6.movement_range == 2
        assert token_4.movement_range == 2

    def test_attack_power(self):
        """Test attack power calculation (health // 2)."""
        token_10 = Token(id=1, player_id="p1", health=10, max_health=10, position=(0, 0))
        token_8 = Token(id=2, player_id="p1", health=8, max_health=8, position=(0, 0))
        token_6 = Token(id=3, player_id="p1", health=6, max_health=6, position=(0, 0))
        token_4 = Token(id=4, player_id="p1", health=4, max_health=4, position=(0, 0))

        assert token_10.attack_power == 5
        assert token_8.attack_power == 4
        assert token_6.attack_power == 3
        assert token_4.attack_power == 2

    def test_attack_power_when_damaged(self):
        """Test attack power decreases with damage."""
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(0, 0))
        assert token.attack_power == 5

        token.take_damage(3)
        assert token.health == 7
        assert token.attack_power == 3  # 7 // 2 = 3

    def test_take_damage(self):
        """Test taking damage."""
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(0, 0))

        killed = token.take_damage(4)
        assert token.health == 6
        assert killed is False
        assert token.is_alive is True

    def test_take_damage_killed(self):
        """Test token is killed when health reaches 0."""
        token = Token(id=1, player_id="p1", health=4, max_health=4, position=(0, 0))

        killed = token.take_damage(4)
        assert token.health == 0
        assert killed is True
        assert token.is_alive is False

    def test_take_damage_overkill(self):
        """Test token is killed when damage exceeds health."""
        token = Token(id=1, player_id="p1", health=4, max_health=4, position=(0, 0))

        killed = token.take_damage(10)
        assert token.health == 0
        assert killed is True
        assert token.is_alive is False

    def test_heal_to_full(self):
        """Test healing to full health."""
        token = Token(id=1, player_id="p1", health=3, max_health=10, position=(0, 0))

        token.heal_to_full()
        assert token.health == 10
        assert token.max_health == 10

    def test_move_to(self):
        """Test moving token to new position."""
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        token.move_to((7, 8))
        assert token.position == (7, 8)

    def test_distance_to_manhattan(self):
        """Test Manhattan distance calculation."""
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        assert token.distance_to((5, 5)) == 0
        assert token.distance_to((6, 5)) == 1
        assert token.distance_to((5, 6)) == 1
        assert token.distance_to((7, 7)) == 4  # |5-7| + |5-7| = 2 + 2
        assert token.distance_to((3, 3)) == 4  # |5-3| + |5-3| = 2 + 2

    def test_is_adjacent_to(self):
        """Test adjacency checking (8 directions)."""
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        # All 8 adjacent cells
        assert token.is_adjacent_to((4, 4)) is True  # Top-left
        assert token.is_adjacent_to((5, 4)) is True  # Top
        assert token.is_adjacent_to((6, 4)) is True  # Top-right
        assert token.is_adjacent_to((4, 5)) is True  # Left
        assert token.is_adjacent_to((6, 5)) is True  # Right
        assert token.is_adjacent_to((4, 6)) is True  # Bottom-left
        assert token.is_adjacent_to((5, 6)) is True  # Bottom
        assert token.is_adjacent_to((6, 6)) is True  # Bottom-right

        # Not adjacent
        assert token.is_adjacent_to((5, 5)) is False  # Same position
        assert token.is_adjacent_to((7, 7)) is False  # Too far
        assert token.is_adjacent_to((3, 3)) is False  # Too far

    def test_serialization_to_dict(self):
        """Test converting token to dictionary."""
        token = Token(
            id=42,
            player_id="player123",
            health=7,
            max_health=10,
            position=(3, 4),
            is_alive=True
        )

        data = token.to_dict()
        assert data["id"] == 42
        assert data["player_id"] == "player123"
        assert data["health"] == 7
        assert data["max_health"] == 10
        assert data["position"] == [3, 4]
        assert data["is_alive"] is True

    def test_deserialization_from_dict(self):
        """Test creating token from dictionary."""
        data = {
            "id": 42,
            "player_id": "player123",
            "health": 7,
            "max_health": 10,
            "position": [3, 4],
            "is_alive": True
        }

        token = Token.from_dict(data)
        assert token.id == 42
        assert token.player_id == "player123"
        assert token.health == 7
        assert token.max_health == 10
        assert token.position == (3, 4)
        assert token.is_alive is True

    def test_serialization_roundtrip(self):
        """Test serialization and deserialization preserves data."""
        original = Token(
            id=99,
            player_id="test_player",
            health=5,
            max_health=8,
            position=(10, 20),
            is_alive=False
        )

        data = original.to_dict()
        restored = Token.from_dict(data)

        assert restored.id == original.id
        assert restored.player_id == original.player_id
        assert restored.health == original.health
        assert restored.max_health == original.max_health
        assert restored.position == original.position
        assert restored.is_alive == original.is_alive
