"""
Tests for lobby message handling logic without Arcade dependencies.
"""
import pytest
from unittest.mock import Mock
from network.messages import MessageType
from network.protocol import NetworkMessage
import time


class MockLobbyView:
    """Mock LobbyView for testing message handling logic."""

    def __init__(self):
        self.players = {}
        self.game_name = "Test Lobby"
        self.title_text = None

    async def _handle_create_game(self, message):
        """Handle CREATE_GAME response - initialize lobby with host player."""
        data = message.data or {}

        # Update lobby info
        self.game_name = data.get("game_name", "Lobby")
        players_list = data.get("players", [])

        # Clear and populate player list
        self.players.clear()

        for player_info in players_list:
            player_id = player_info.get("player_id")
            if player_id:
                self.players[player_id] = {
                    "player_name": player_info.get("player_name", "Unknown"),
                    "is_ready": player_info.get("is_ready", False),
                    "color_index": player_info.get("color_index", 0)
                }

    async def _handle_player_joined(self, message):
        """Handle PLAYER_JOINED message."""
        data = message.data or {}
        player_id = data.get("player_id")
        player_name = data.get("player_name", "Unknown")
        lobby_data = data.get("lobby", {})
        
        # Try to get color_index from lobby data if available
        color_index = data.get("color_index", 0)
        
        # If lobby data is available, use it to get the complete player info
        if lobby_data:
            players_list = lobby_data.get("players", [])
            # Find the player in the lobby's player list
            for player_info in players_list:
                if player_info.get("player_id") == player_id:
                    color_index = player_info.get("color_index", 0)
                    break

        if player_id:
            self.players[player_id] = {
                "player_name": player_name,
                "is_ready": False,
                "color_index": color_index
            }
    
    async def _handle_full_state(self, message):
        """Handle FULL_STATE message."""
        data = message.data or {}
        lobby_data = data.get("lobby", {})

        # Update lobby info
        if lobby_data:
            self.game_name = lobby_data.get("game_name", "Lobby")
            players_list = lobby_data.get("players", [])

            # Update player list
            # Clear existing players first
            self.players.clear()
            
            # Add players from the list
            for player_info in players_list:
                player_id = player_info.get("player_id")
                if player_id:
                    self.players[player_id] = {
                        "player_name": player_info.get("player_name", "Unknown"),
                        "is_ready": player_info.get("is_ready", False),
                        "color_index": player_info.get("color_index", 0)
                    }


class TestLobbyMessageHandling:
    """Test lobby message handling logic."""

    def test_player_joined_message_handling(self):
        """Test that PLAYER_JOINED messages correctly update player list."""
        lobby_view = MockLobbyView()
        
        # Create a PLAYER_JOINED message with lobby data
        message = NetworkMessage(
            type=MessageType.PLAYER_JOINED,
            timestamp=time.time(),
            player_id="test-player-2",
            data={
                "game_id": "test-game",
                "player_id": "test-player-2", 
                "player_name": "Player 2",
                "lobby": {
                    "game_id": "test-game",
                    "game_name": "Test Game",
                    "players": [
                        {
                            "player_id": "test-player-1",
                            "player_name": "Player 1",
                            "is_ready": False,
                            "color_index": 0
                        },
                        {
                            "player_id": "test-player-2",
                            "player_name": "Player 2", 
                            "is_ready": False,
                            "color_index": 1
                        }
                    ]
                }
            }
        )
        
        # Process the message
        import asyncio
        asyncio.run(lobby_view._handle_player_joined(message))
        
        # Verify player was added with correct color index
        assert len(lobby_view.players) == 1
        assert "test-player-2" in lobby_view.players
        player_info = lobby_view.players["test-player-2"]
        assert player_info["player_name"] == "Player 2"
        assert player_info["color_index"] == 1  # Should get color_index from lobby data
        assert player_info["is_ready"] == False

    def test_full_state_message_handling(self):
        """Test that FULL_STATE messages correctly update player list."""
        lobby_view = MockLobbyView()
        
        # Add some initial players to simulate existing state
        lobby_view.players["existing-player"] = {
            "player_name": "Existing Player",
            "is_ready": True,
            "color_index": 0
        }
        
        # Create a FULL_STATE message with lobby data
        message = NetworkMessage(
            type=MessageType.FULL_STATE,
            timestamp=time.time(),
            player_id="test-player-1",
            data={
                "lobby": {
                    "game_id": "test-game",
                    "game_name": "Test Game",
                    "players": [
                        {
                            "player_id": "test-player-1",
                            "player_name": "Player 1",
                            "is_ready": False,
                            "color_index": 0
                        },
                        {
                            "player_id": "test-player-2",
                            "player_name": "Player 2", 
                            "is_ready": True,
                            "color_index": 1
                        }
                    ]
                }
            }
        )
        
        # Process the message
        import asyncio
        asyncio.run(lobby_view._handle_full_state(message))
        
        # Verify player list was updated correctly
        assert len(lobby_view.players) == 2
        assert "test-player-1" in lobby_view.players
        assert "test-player-2" in lobby_view.players
        
        # Verify existing player was cleared (should only have players from FULL_STATE)
        assert "existing-player" not in lobby_view.players
        
        # Verify player info is correct
        player1 = lobby_view.players["test-player-1"]
        assert player1["player_name"] == "Player 1"
        assert player1["color_index"] == 0
        assert player1["is_ready"] == False
        
        player2 = lobby_view.players["test-player-2"]
        assert player2["player_name"] == "Player 2"
        assert player2["color_index"] == 1
        assert player2["is_ready"] == True

    def test_player_joined_without_lobby_data(self):
        """Test PLAYER_JOINED message handling when no lobby data is provided."""
        lobby_view = MockLobbyView()
        
        # Create a PLAYER_JOINED message without lobby data (fallback case)
        message = NetworkMessage(
            type=MessageType.PLAYER_JOINED,
            timestamp=time.time(),
            player_id="test-player-1",
            data={
                "game_id": "test-game",
                "player_id": "test-player-1", 
                "player_name": "Player 1",
                "color_index": 2  # Direct color_index in message data
            }
        )
        
        # Process the message
        import asyncio
        asyncio.run(lobby_view._handle_player_joined(message))
        
        # Verify player was added with fallback color index
        assert len(lobby_view.players) == 1
        assert "test-player-1" in lobby_view.players
        player_info = lobby_view.players["test-player-1"]
        assert player_info["player_name"] == "Player 1"
        assert player_info["color_index"] == 2  # Should use fallback color_index
        assert player_info["is_ready"] == False

    def test_create_game_message_handling(self):
        """Test that CREATE_GAME response correctly initializes lobby with host player."""
        lobby_view = MockLobbyView()

        # Create a CREATE_GAME response message with lobby data including host
        message = NetworkMessage(
            type=MessageType.CREATE_GAME,
            timestamp=time.time(),
            player_id="host-player-id",
            data={
                "game_id": "new-game-123",
                "game_name": "My Awesome Game",
                "host_player_id": "host-player-id",
                "max_players": 4,
                "min_players": 2,
                "current_players": 1,
                "status": "WAITING",
                "players": [
                    {
                        "player_id": "host-player-id",
                        "player_name": "Host Player",
                        "is_ready": False,
                        "color_index": 0
                    }
                ]
            }
        )

        # Process the message
        import asyncio
        asyncio.run(lobby_view._handle_create_game(message))

        # Verify lobby was initialized with host player
        assert lobby_view.game_name == "My Awesome Game"
        assert len(lobby_view.players) == 1
        assert "host-player-id" in lobby_view.players

        # Verify host player info
        host_info = lobby_view.players["host-player-id"]
        assert host_info["player_name"] == "Host Player"
        assert host_info["is_ready"] == False
        assert host_info["color_index"] == 0

    def test_create_game_message_with_empty_players(self):
        """Test CREATE_GAME handling when players list is empty (shouldn't happen but test robustness)."""
        lobby_view = MockLobbyView()

        # Add some existing player data
        lobby_view.players["old-player"] = {
            "player_name": "Old Player",
            "is_ready": True,
            "color_index": 2
        }

        # Create a CREATE_GAME message with empty players list
        message = NetworkMessage(
            type=MessageType.CREATE_GAME,
            timestamp=time.time(),
            player_id="host-player-id",
            data={
                "game_id": "new-game-123",
                "game_name": "Empty Game",
                "players": []
            }
        )

        # Process the message
        import asyncio
        asyncio.run(lobby_view._handle_create_game(message))

        # Verify old players were cleared and list is empty
        assert lobby_view.game_name == "Empty Game"
        assert len(lobby_view.players) == 0
        assert "old-player" not in lobby_view.players


if __name__ == "__main__":
    pytest.main([__file__, "-v"])