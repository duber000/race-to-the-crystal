import asyncio
import pytest
import os
import json
from unittest.mock import AsyncMock, patch, MagicMock
from server.game_server import GameServer
from network.messages import MessageType, ClientType
from network.protocol import NetworkMessage

class MockStreamWriter:
    def __init__(self):
        self.sent_data = []
        self._closed = False

    def write(self, data):
        self.sent_data.append(data)

    async def drain(self):
        pass

    def close(self):
        self._closed = True

    async def wait_closed(self):
        pass

    def get_extra_info(self, name):
        if name == 'peername':
            return ('127.0.0.1', 12345)
        return None

@pytest.mark.asyncio
async def test_sse_primary_mode_broadcast_filtering():
    """
    Verify that in SSE_PRIMARY_MODE=true:
    1. WEB_BROWSER clients do NOT receive state updates via WebSocket.
    2. HUMAN (Desktop) clients DO receive state updates via WebSocket.
    """
    with patch.dict(os.environ, {"SSE_PRIMARY_MODE": "true"}):
        server = GameServer(host="localhost", port=0)
        server.mercure_publisher = AsyncMock()
        server.mercure_publisher.publish_full_state.return_value = True
        server.mercure_publisher.publish_state_update.return_value = True

        # Setup Web client (SSE capable)
        web_player_id = "player_web_id"
        web_conn = MagicMock()
        server.player_connections[web_player_id] = web_conn
        server.player_client_types[web_player_id] = ClientType.WEB_BROWSER

        # Setup Desktop client
        desktop_player_id = "player_desktop_id"
        desktop_conn = MagicMock()
        server.player_connections[desktop_player_id] = desktop_conn
        server.player_client_types[desktop_player_id] = ClientType.HUMAN

        # Create game session via coordinator
        lobby = MagicMock()
        lobby.game_id = "game_123"
        lobby.players = {
            web_player_id: MagicMock(player_id=web_player_id, color_index=0),
            desktop_player_id: MagicMock(player_id=desktop_player_id, color_index=1)
        }
        
        session = server.game_coordinator.create_game(lobby)
        # Register players in session
        session.network_to_game_id[web_player_id] = "g_web"
        session.network_to_game_id[desktop_player_id] = "g_desktop"

        with patch.object(server, '_send_to_player', AsyncMock()) as mock_send:
            await server._broadcast_game_state(session)
            
            # Verify calls
            sent_player_ids = [call.args[0] for call in mock_send.call_args_list]
            
            assert desktop_player_id in sent_player_ids, "Desktop client should have received WebSocket update"
            assert web_player_id not in sent_player_ids, "Web client should NOT have received WebSocket update in SSE-primary mode"
            
            # Verify Mercure publish
            # Can be either full state (first time) or delta
            assert (server.mercure_publisher.publish_full_state.called or 
                    server.mercure_publisher.publish_state_update.called)

@pytest.mark.asyncio
async def test_sse_failure_fallback():
    """
    Verify fallback to WebSocket when SSE fails.
    """
    with patch.dict(os.environ, {"SSE_PRIMARY_MODE": "true"}):
        server = GameServer(host="localhost", port=0)
        server.mercure_publisher = AsyncMock()
        server.mercure_publisher.publish_full_state.return_value = False # FAIL
        server.mercure_publisher.publish_state_update.return_value = False # FAIL

        web_player_id = "player_web_id"
        web_conn = MagicMock()
        server.player_connections[web_player_id] = web_conn
        server.player_client_types[web_player_id] = ClientType.WEB_BROWSER

        web_player_id2 = "player_web_id2"
        lobby = MagicMock()
        lobby.game_id = "game_123"
        lobby.players = {
            web_player_id: MagicMock(player_id=web_player_id, color_index=0),
            web_player_id2: MagicMock(player_id=web_player_id2, color_index=1)
        }
        
        session = server.game_coordinator.create_game(lobby)
        session.network_to_game_id[web_player_id] = "g_web"
        session.network_to_game_id[web_player_id2] = "g_web2"
        server.player_client_types[web_player_id2] = ClientType.WEB_BROWSER

        with patch.object(server, '_send_to_player', AsyncMock()) as mock_send:
            await server._broadcast_game_state(session)
            
            sent_player_ids = [call.args[0] for call in mock_send.call_args_list]
            assert web_player_id in sent_player_ids, "Web client should receive WebSocket fallback if SSE fails"
