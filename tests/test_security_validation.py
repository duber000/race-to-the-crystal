"""
Security validation tests for Race to the Crystal.

Tests input validation to prevent command injection and other security issues.
"""
import pytest
from server.lobby import validate_game_name, validate_player_name, LobbyManager
from network.messages import ClientType


class TestSecurityValidation:
    """Test security validation functions."""

    def test_valid_game_names(self):
        """Test that valid game names pass validation."""
        valid_names = [
            "My Game",
            "Game_1",
            "Game-2",
            "Game.3",
            "Game 4",
            "A" * 50,  # Max length
            "Test_Game-123.456",
        ]
        
        for name in valid_names:
            assert validate_game_name(name) is True

    def test_invalid_game_names(self):
        """Test that invalid game names are rejected."""
        invalid_cases = [
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("A" * 51, "too long"),
            ("Game;Name", "semicolon"),
            ("Game&Name", "ampersand"),
            ("Game|Name", "pipe"),
            ("Game$Name", "dollar sign"),
            ("Game>Name", "greater than"),
            ("Game<Name", "less than"),
            ("Game`Name", "backtick"),
            ("Game\\Name", "backslash"),
            ("Game..Name", "double dots"),
            (" Game", "leading space"),
            ("Game ", "trailing space"),
            ("Game\nName", "newline"),
            ("Game\tName", "tab"),
        ]

        for name, description in invalid_cases:
            with pytest.raises(ValueError) as exc_info:
                validate_game_name(name)
            # Just verify that a ValueError was raised with a non-empty message
            assert str(exc_info.value), f"Expected error message for {description}"

    def test_valid_player_names(self):
        """Test that valid player names pass validation."""
        valid_names = [
            "Player1",
            "Player_Name",
            "Player-Name",
            "Player.Name",
            "Player Name",
            "A" * 30,  # Max length
            "Test_Player-123.456",
        ]
        
        for name in valid_names:
            assert validate_player_name(name) is True

    def test_invalid_player_names(self):
        """Test that invalid player names are rejected."""
        invalid_cases = [
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("A" * 31, "too long"),
            ("Player;Name", "semicolon"),
            ("Player&Name", "ampersand"),
            ("Player|Name", "pipe"),
            ("Player$Name", "dollar sign"),
            ("Player>Name", "greater than"),
            ("Player<Name", "less than"),
            ("Player`Name", "backtick"),
            ("Player\\Name", "backslash"),
            (" Player", "leading space"),
            ("Player ", "trailing space"),
            ("Player\nName", "newline"),
            ("Player\tName", "tab"),
        ]

        for name, description in invalid_cases:
            with pytest.raises(ValueError) as exc_info:
                validate_player_name(name)
            # Just verify that a ValueError was raised with a non-empty message
            assert str(exc_info.value), f"Expected error message for {description}"


class TestLobbySecurity:
    """Test lobby security features."""

    def test_lobby_creation_with_invalid_names(self):
        """Test that lobby creation rejects invalid game names."""
        manager = LobbyManager()
        
        # Test invalid game names
        invalid_game_names = [
            "Game;rm -rf /",
            "Game&Name",
            "Game|Name",
            "" * 100,  # Too long
        ]
        
        for game_name in invalid_game_names:
            with pytest.raises(ValueError):
                manager.create_lobby(
                    player_id="test_player",
                    player_name="Test Player",
                    game_name=game_name,
                    client_type=ClientType.HUMAN
                )
        
        # Test invalid player names
        invalid_player_names = [
            "Player;Name",
            "Player&Name",
            "Player|Name",
            "" * 100,  # Too long
        ]
        
        for player_name in invalid_player_names:
            with pytest.raises(ValueError):
                manager.create_lobby(
                    player_id="test_player",
                    player_name=player_name,
                    game_name="Valid Game",
                    client_type=ClientType.HUMAN
                )

    def test_player_joining_with_invalid_names(self):
        """Test that player joining rejects invalid player names."""
        manager = LobbyManager()
        
        # Create a valid lobby first
        lobby = manager.create_lobby(
            player_id="host_player",
            player_name="Host Player",
            game_name="Valid Game",
            client_type=ClientType.HUMAN
        )
        
        # Test invalid player names when joining
        invalid_player_names = [
            "Player;Name",
            "Player&Name",
            "Player|Name",
            "" * 100,  # Too long
        ]
        
        for player_name in invalid_player_names:
            with pytest.raises(ValueError):
                lobby.add_player(
                    player_id="test_player",
                    player_name=player_name,
                    client_type=ClientType.HUMAN
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])