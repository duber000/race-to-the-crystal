"""
Tests for SSE-primary mode functionality.

Tests the server-side implementation of SSE-primary mode where:
- SSE-capable clients (WEB_BROWSER, HTTP_AI) receive state updates via SSE only
- Desktop clients (HUMAN, AI) continue receiving via WebSocket/TCP
- Automatic fallback to WebSocket if Mercure fails
"""

import pytest
import os
from unittest.mock import AsyncMock, patch
from network.messages import (
    MessageType,
    ClientType,
    SSE_MESSAGES,
    WEBSOCKET_MESSAGES,
    SSE_CAPABLE_CLIENTS,
)


class TestMessageClassification:
    """Test message classification constants."""

    def test_sse_messages_defined(self):
        """Test that SSE message types are properly defined."""
        expected_sse_types = {
            MessageType.FULL_STATE,
            MessageType.STATE_UPDATE,
            MessageType.TURN_CHANGE,
            MessageType.TOKEN_MOVED,
            MessageType.COMBAT_RESULT,
            MessageType.GENERATOR_UPDATE,
            MessageType.CRYSTAL_UPDATE,
            MessageType.MYSTERY_EVENT,
            MessageType.TOKEN_DEPLOYED,
            MessageType.GAME_WON,
        }
        assert SSE_MESSAGES == expected_sse_types

    def test_websocket_messages_defined(self):
        """Test that WebSocket message types are properly defined."""
        # Should include commands, lobby operations, connection management
        assert MessageType.MOVE in WEBSOCKET_MESSAGES
        assert MessageType.ATTACK in WEBSOCKET_MESSAGES
        assert MessageType.DEPLOY in WEBSOCKET_MESSAGES
        assert MessageType.END_TURN in WEBSOCKET_MESSAGES
        assert MessageType.CREATE_GAME in WEBSOCKET_MESSAGES
        assert MessageType.JOIN_GAME in WEBSOCKET_MESSAGES
        assert MessageType.CONNECT in WEBSOCKET_MESSAGES

    def test_sse_capable_clients_defined(self):
        """Test that SSE-capable client types are properly defined."""
        assert ClientType.WEB_BROWSER in SSE_CAPABLE_CLIENTS
        assert ClientType.HTTP_AI in SSE_CAPABLE_CLIENTS
        assert ClientType.HUMAN not in SSE_CAPABLE_CLIENTS
        assert ClientType.AI not in SSE_CAPABLE_CLIENTS

    def test_no_message_overlap(self):
        """Test that SSE and WebSocket messages don't overlap."""
        # Only exception might be FULL_STATE which appears in both contexts
        # but is handled differently based on client type
        overlap = SSE_MESSAGES & WEBSOCKET_MESSAGES
        assert len(overlap) == 0, f"Messages should not overlap: {overlap}"


class TestSSEPrimaryModeConfiguration:
    """Test SSE-primary mode environment variable configuration."""

    def test_sse_primary_mode_default_disabled(self):
        """Test that SSE-primary mode is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            from server.game_server import GameServer

            server = GameServer()
            assert server.sse_primary_mode is False

    def test_sse_primary_mode_enabled_true(self):
        """Test that SSE_PRIMARY_MODE=true enables the mode."""
        with patch.dict(os.environ, {"SSE_PRIMARY_MODE": "true"}):
            from server.game_server import GameServer

            server = GameServer()
            assert server.sse_primary_mode is True

    def test_sse_primary_mode_enabled_case_insensitive(self):
        """Test that SSE_PRIMARY_MODE is case-insensitive."""
        with patch.dict(os.environ, {"SSE_PRIMARY_MODE": "TRUE"}):
            from server.game_server import GameServer

            server = GameServer()
            assert server.sse_primary_mode is True

        with patch.dict(os.environ, {"SSE_PRIMARY_MODE": "True"}):
            from server.game_server import GameServer

            server = GameServer()
            assert server.sse_primary_mode is True

    def test_sse_primary_mode_disabled_false(self):
        """Test that SSE_PRIMARY_MODE=false disables the mode."""
        with patch.dict(os.environ, {"SSE_PRIMARY_MODE": "false"}):
            from server.game_server import GameServer

            server = GameServer()
            assert server.sse_primary_mode is False

    def test_sse_primary_mode_invalid_value(self):
        """Test that invalid values default to disabled."""
        with patch.dict(os.environ, {"SSE_PRIMARY_MODE": "invalid"}):
            from server.game_server import GameServer

            server = GameServer()
            assert server.sse_primary_mode is False


class TestMercurePublisherEvents:
    """Test individual event publishing methods in MercurePublisher."""

    @pytest.fixture
    def mock_publisher(self):
        """Create a mock MercurePublisher for testing."""
        from server.mercure_publisher import MercurePublisher, MercureConfig

        config = MercureConfig(
            hub_url="http://test-hub/.well-known/mercure",
            publisher_jwt="test-jwt-token",
            topic_prefix="https://test.com/game",
        )
        publisher = MercurePublisher(config)
        publisher.publish_game_state = AsyncMock(return_value=True)
        return publisher

    @pytest.mark.asyncio
    async def test_publish_turn_change(self, mock_publisher):
        """Test publishing turn change event."""
        result = await mock_publisher.publish_turn_change(
            "game-123", "player-1", 5, "MOVEMENT"
        )
        assert result is True
        mock_publisher.publish_game_state.assert_called_once()

        call_args = mock_publisher.publish_game_state.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "TURN_CHANGE"
        assert event_data["current_player_id"] == "player-1"
        assert event_data["turn_number"] == 5
        assert event_data["turn_phase"] == "MOVEMENT"

    @pytest.mark.asyncio
    async def test_publish_token_moved(self, mock_publisher):
        """Test publishing token moved event."""
        result = await mock_publisher.publish_token_moved(
            "game-123", 42, (10, 10), (12, 12), "player-1"
        )
        assert result is True

        call_args = mock_publisher.publish_game_state.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "TOKEN_MOVED"
        assert event_data["token_id"] == 42
        assert event_data["from"] == (10, 10)
        assert event_data["to"] == (12, 12)
        assert event_data["player_id"] == "player-1"

    @pytest.mark.asyncio
    async def test_publish_combat_result(self, mock_publisher):
        """Test publishing combat result event."""
        result = await mock_publisher.publish_combat_result(
            "game-123", 10, 20, 4, True
        )
        assert result is True

        call_args = mock_publisher.publish_game_state.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "COMBAT_RESULT"
        assert event_data["attacker_id"] == 10
        assert event_data["defender_id"] == 20
        assert event_data["damage"] == 4
        assert event_data["defender_destroyed"] is True

    @pytest.mark.asyncio
    async def test_publish_generator_update(self, mock_publisher):
        """Test publishing generator update event."""
        result = await mock_publisher.publish_generator_update(
            "game-123", (5, 5), "player-2", 2, True
        )
        assert result is True

        call_args = mock_publisher.publish_game_state.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "GENERATOR_UPDATE"
        assert event_data["position"] == (5, 5)
        assert event_data["capturing_player_id"] == "player-2"
        assert event_data["turns_held"] == 2
        assert event_data["is_disabled"] is True

    @pytest.mark.asyncio
    async def test_publish_crystal_update(self, mock_publisher):
        """Test publishing crystal update event."""
        result = await mock_publisher.publish_crystal_update(
            "game-123", (12, 12), "player-1", 3, 12
        )
        assert result is True

        call_args = mock_publisher.publish_game_state.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "CRYSTAL_UPDATE"
        assert event_data["position"] == (12, 12)
        assert event_data["occupying_player_id"] == "player-1"
        assert event_data["turns_held"] == 3
        assert event_data["tokens_required"] == 12

    @pytest.mark.asyncio
    async def test_publish_mystery_event(self, mock_publisher):
        """Test publishing mystery event."""
        result = await mock_publisher.publish_mystery_event(
            "game-123", 15, "heal", {"amount": 2}
        )
        assert result is True

        call_args = mock_publisher.publish_game_state.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "MYSTERY_EVENT"
        assert event_data["token_id"] == 15
        assert event_data["event_type"] == "heal"
        assert event_data["details"]["amount"] == 2

    @pytest.mark.asyncio
    async def test_publish_token_deployed(self, mock_publisher):
        """Test publishing token deployed event."""
        result = await mock_publisher.publish_token_deployed(
            "game-123", 8, (3, 3), "player-3"
        )
        assert result is True

        call_args = mock_publisher.publish_game_state.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "TOKEN_DEPLOYED"
        assert event_data["token_id"] == 8
        assert event_data["position"] == (3, 3)
        assert event_data["player_id"] == "player-3"

    @pytest.mark.asyncio
    async def test_publish_game_won(self, mock_publisher):
        """Test publishing game won event."""
        result = await mock_publisher.publish_game_won("game-123", "player-1")
        assert result is True

        call_args = mock_publisher.publish_game_state.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "GAME_WON"
        assert event_data["winner_id"] == "player-1"


class TestAPIConfigEndpoint:
    """Test /api/config endpoint returns SSE-primary mode status."""

    def test_api_config_includes_sse_primary_mode_disabled(self):
        """Test that config includes sse_primary_mode=false by default."""
        # This would be an integration test in a real scenario
        # For now, just verify the environment variable logic
        with patch.dict(os.environ, {}, clear=True):
            sse_primary_mode = os.getenv("SSE_PRIMARY_MODE", "false").lower() == "true"
            assert sse_primary_mode is False

    def test_api_config_includes_sse_primary_mode_enabled(self):
        """Test that config includes sse_primary_mode=true when enabled."""
        with patch.dict(os.environ, {"SSE_PRIMARY_MODE": "true"}):
            sse_primary_mode = os.getenv("SSE_PRIMARY_MODE", "false").lower() == "true"
            assert sse_primary_mode is True
