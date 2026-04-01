"""
Unit tests for Player class.
"""

from game.player import Player
from shared.enums import PlayerColor


class TestPlayerCreation:
    """Test cases for Player creation and initialization."""

    def test_basic_creation(self):
        """Test creating a player with basic attributes."""
        player = Player(id="player1", name="Test Player", color=PlayerColor.CYAN)
        assert player.id == "player1"
        assert player.name == "Test Player"
        assert player.color == PlayerColor.CYAN
        assert player.token_ids == []
        assert player.is_ready is False
        assert player.is_active is True
        assert player.team is None

    def test_creation_with_team(self):
        """Test creating a player with a team assignment."""
        player = Player(
            id="player1", name="Test Player", color=PlayerColor.MAGENTA, team=1
        )
        assert player.team == 1

    def test_creation_with_tokens(self):
        """Test creating a player with initial tokens."""
        player = Player(
            id="player1",
            name="Test Player",
            color=PlayerColor.YELLOW,
            token_ids=[1, 2, 3],
        )
        assert player.token_ids == [1, 2, 3]
        assert player.token_count == 3


class TestPlayerTokenManagement:
    """Test cases for token management methods."""

    def test_add_token(self):
        """Test adding a token to player."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN)
        player.add_token(1)
        assert 1 in player.token_ids
        assert player.token_count == 1

    def test_add_multiple_tokens(self):
        """Test adding multiple tokens."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN)
        player.add_token(1)
        player.add_token(2)
        player.add_token(3)
        assert player.token_ids == [1, 2, 3]
        assert player.token_count == 3

    def test_add_duplicate_token_ignored(self):
        """Test that adding duplicate token is ignored."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN)
        player.add_token(1)
        player.add_token(1)  # Duplicate
        assert player.token_ids == [1]  # Still just one
        assert player.token_count == 1

    def test_remove_token(self):
        """Test removing a token from player."""
        player = Player(
            id="p1", name="Player", color=PlayerColor.CYAN, token_ids=[1, 2, 3]
        )
        player.remove_token(2)
        assert 2 not in player.token_ids
        assert player.token_ids == [1, 3]

    def test_remove_nonexistent_token_ignored(self):
        """Test removing a token player doesn't have."""
        player = Player(
            id="p1", name="Player", color=PlayerColor.CYAN, token_ids=[1, 2]
        )
        player.remove_token(99)  # Doesn't exist
        assert player.token_ids == [1, 2]  # Unchanged

    def test_has_token_true(self):
        """Test checking if player has a token they own."""
        player = Player(
            id="p1", name="Player", color=PlayerColor.CYAN, token_ids=[1, 2, 3]
        )
        assert player.has_token(2) is True

    def test_has_token_false(self):
        """Test checking if player has a token they don't own."""
        player = Player(
            id="p1", name="Player", color=PlayerColor.CYAN, token_ids=[1, 2]
        )
        assert player.has_token(99) is False


class TestPlayerStateManagement:
    """Test cases for player state changes."""

    def test_set_ready_true(self):
        """Test setting player as ready."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN)
        player.set_ready(True)
        assert player.is_ready is True

    def test_set_ready_false(self):
        """Test setting player as not ready."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN, is_ready=True)
        player.set_ready(False)
        assert player.is_ready is False

    def test_set_ready_default_true(self):
        """Test set_ready defaults to True."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN)
        player.set_ready()
        assert player.is_ready is True

    def test_eliminate(self):
        """Test eliminating a player."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN)
        player.eliminate()
        assert player.is_active is False

    def test_eliminate_already_inactive(self):
        """Test eliminating an already inactive player."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN, is_active=False)
        player.eliminate()
        assert player.is_active is False  # Still inactive


class TestPlayerSerialization:
    """Test cases for serialization methods."""

    def test_to_dict_basic(self):
        """Test basic serialization to dict."""
        player = Player(
            id="player1",
            name="Test Player",
            color=PlayerColor.CYAN,
            token_ids=[1, 2, 3],
            is_ready=True,
            is_active=True,
            team=2,
        )
        data = player.to_dict()
        assert data["id"] == "player1"
        assert data["name"] == "Test Player"
        assert data["color"] == 0  # CYAN.value
        assert data["token_ids"] == [1, 2, 3]
        assert data["is_ready"] is True
        assert data["is_active"] is True
        assert data["team"] == 2

    def test_to_dict_defaults(self):
        """Test serialization with default values."""
        player = Player(id="p1", name="Player", color=PlayerColor.MAGENTA)
        data = player.to_dict()
        assert data["token_ids"] == []
        assert data["is_ready"] is False
        assert data["is_active"] is True
        assert data["team"] is None

    def test_from_dict_basic(self):
        """Test deserialization from dict."""
        data = {
            "id": "player1",
            "name": "Test Player",
            "color": 0,  # CYAN.value
            "token_ids": [1, 2, 3],
            "is_ready": True,
            "is_active": True,
            "team": 2,
        }
        player = Player.from_dict(data)
        assert player.id == "player1"
        assert player.name == "Test Player"
        assert player.color == PlayerColor.CYAN
        assert player.token_ids == [1, 2, 3]
        assert player.is_ready is True
        assert player.is_active is True
        assert player.team == 2

    def test_from_dict_all_colors(self):
        """Test deserialization with all player colors."""
        for color in PlayerColor:
            data = {
                "id": "p1",
                "name": "Player",
                "color": color.value,
                "token_ids": [],
                "is_ready": False,
                "is_active": True,
                "team": None,
            }
            player = Player.from_dict(data)
            assert player.color == color

    def test_roundtrip_serialization(self):
        """Test that to_dict -> from_dict preserves all data."""
        original = Player(
            id="player1",
            name="Test Player",
            color=PlayerColor.YELLOW,
            token_ids=[10, 20, 30],
            is_ready=True,
            is_active=False,
            team=1,
        )
        data = original.to_dict()
        restored = Player.from_dict(data)
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.color == original.color
        assert restored.token_ids == original.token_ids
        assert restored.is_ready == original.is_ready
        assert restored.is_active == original.is_active
        assert restored.team == original.team


class TestPlayerProperties:
    """Test cases for player properties."""

    def test_token_count_empty(self):
        """Test token count with no tokens."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN)
        assert player.token_count == 0

    def test_token_count_with_tokens(self):
        """Test token count with tokens."""
        player = Player(
            id="p1", name="Player", color=PlayerColor.CYAN, token_ids=[1, 2, 3, 4, 5]
        )
        assert player.token_count == 5

    def test_token_count_after_add(self):
        """Test token count updates after adding tokens."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN)
        assert player.token_count == 0
        player.add_token(1)
        assert player.token_count == 1
        player.add_token(2)
        assert player.token_count == 2

    def test_token_count_after_remove(self):
        """Test token count updates after removing tokens."""
        player = Player(
            id="p1", name="Player", color=PlayerColor.CYAN, token_ids=[1, 2, 3]
        )
        assert player.token_count == 3
        player.remove_token(2)
        assert player.token_count == 2


class TestPlayerRepresentation:
    """Test cases for string representation."""

    def test_repr_basic(self):
        """Test basic string representation."""
        player = Player(
            id="p1", name="TestPlayer", color=PlayerColor.CYAN, token_ids=[1, 2, 3]
        )
        repr_str = repr(player)
        assert "TestPlayer" in repr_str
        assert "CYAN" in repr_str
        assert "Tokens=3" in repr_str

    def test_repr_no_tokens(self):
        """Test representation with no tokens."""
        player = Player(id="p1", name="TestPlayer", color=PlayerColor.MAGENTA)
        repr_str = repr(player)
        assert "Tokens=0" in repr_str

    def test_repr_all_colors(self):
        """Test representation with each color."""
        for color in PlayerColor:
            player = Player(id="p1", name="Player", color=color)
            assert color.name in repr(player)


class TestPlayerEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_string_name(self):
        """Test player with empty string name."""
        player = Player(id="p1", name="", color=PlayerColor.CYAN)
        assert player.name == ""

    def test_long_name(self):
        """Test player with very long name."""
        long_name = "A" * 1000
        player = Player(id="p1", name=long_name, color=PlayerColor.CYAN)
        assert player.name == long_name

    def test_special_characters_in_name(self):
        """Test player with special characters in name."""
        special_name = "Player!@#$%^&*()_+-=[]{}|;':\",./<>?"
        player = Player(id="p1", name=special_name, color=PlayerColor.CYAN)
        assert player.name == special_name

    def test_unicode_name(self):
        """Test player with unicode characters in name."""
        unicode_name = "プレイヤー 🎮 Ñoño"
        player = Player(id="p1", name=unicode_name, color=PlayerColor.CYAN)
        assert player.name == unicode_name

    def test_negative_team_id(self):
        """Test player with negative team ID."""
        player = Player(id="p1", name="Player", color=PlayerColor.CYAN, team=-1)
        assert player.team == -1

    def test_large_token_ids(self):
        """Test player with large token IDs."""
        large_ids = [1000000, 2000000, 3000000]
        player = Player(
            id="p1", name="Player", color=PlayerColor.CYAN, token_ids=large_ids
        )
        assert player.has_token(2000000) is True
        assert player.token_count == 3
