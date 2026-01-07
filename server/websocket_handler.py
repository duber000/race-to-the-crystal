"""
WebSocket Handler for Race to the Crystal web clients.

Handles WebSocket connections from Babylon.js web clients,
integrating with the main game server for lobby and game actions.
"""

import json
import logging
import time
import uuid
from typing import Dict, Optional
from dataclasses import dataclass, field

from aiohttp import WSMsgType, web

from network.messages import MessageType, ClientType
from network.protocol import NetworkMessage, ProtocolHandler


logger = logging.getLogger(__name__)


@dataclass
class WebSocketClient:
    """Represents a connected web browser client."""

    client_id: str
    player_id: Optional[str] = None
    player_name: str = "Unknown"
    client_type: ClientType = ClientType.WEB_BROWSER
    websocket: web.WebSocketResponse = None
    game_id: Optional[str] = None
    connected_at: float = field(default_factory=time.time)

    def is_in_game(self) -> bool:
        """Check if client is in an active game."""
        return self.game_id is not None


class WebSocketHandler:
    """
    Handles WebSocket connections from web browser clients.

    Bridges the gap between WebSocket protocol (web clients) and
    the existing TCP-based game server infrastructure.
    """

    def __init__(self, game_server=None):
        """
        Initialize the WebSocket handler.

        Args:
            game_server: Reference to main GameServer for delegating actions
        """
        self.game_server = game_server
        self.clients: Dict[str, WebSocketClient] = {}
        self.protocol = ProtocolHandler()
        self._runner = None

    def set_game_server(self, game_server) -> None:
        """Set reference to main game server."""
        self.game_server = game_server

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """
        Main WebSocket endpoint handler.

        Args:
            request: HTTP request

        Returns:
            WebSocket response for connection
        """
        ws = web.WebSocketResponse(max_msg_size=10 * 1024 * 1024)
        await ws.prepare(request)

        client_id = str(uuid.uuid4())
        client = WebSocketClient(client_id=client_id, websocket=ws)
        self.clients[client_id] = client

        logger.info(f"WebSocket client connected: {client_id}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(client, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
                elif msg.type == WSMsgType.CLOSE:
                    logger.info(f"WebSocket client {client_id} requested close")
                    break

        except Exception as e:
            logger.error(f"WebSocket handler error for {client_id}: {e}", exc_info=True)
        finally:
            await self._handle_disconnect(client)
            if client_id in self.clients:
                del self.clients[client_id]

        return ws

    async def _handle_message(self, client: WebSocketClient, raw_data: str) -> None:
        """
        Handle incoming WebSocket message.

        Args:
            client: Client that sent the message
            raw_data: Raw JSON string
        """
        try:
            data = json.loads(raw_data)
            msg_type = data.get("type")

            logger.debug(f"WebSocket message from {client.client_id}: {msg_type}")

            if msg_type == "CONNECT":
                await self._handle_connect(client, data)
            elif msg_type == "CREATE_GAME":
                await self._handle_create_game(client, data)
            elif msg_type == "JOIN_GAME":
                await self._handle_join_game(client, data)
            elif msg_type == "LEAVE_GAME":
                await self._handle_leave_game(client, data)
            elif msg_type == "LIST_GAMES":
                await self._handle_list_games(client)
            elif msg_type == "READY":
                await self._handle_ready(client, data)
            elif msg_type == "START_GAME":
                await self._handle_start_game(client, data)
            elif msg_type in ["MOVE", "ATTACK", "DEPLOY", "END_TURN"]:
                await self._handle_game_action(client, data)
            elif msg_type == "CHAT":
                await self._handle_chat(client, data)
            elif msg_type == "DISCONNECT":
                await self._handle_client_disconnect(client)
            else:
                logger.warning(f"Unknown WebSocket message type: {msg_type}")
                await self._send_error(client, f"Unknown message type: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {client.client_id}: {e}")
            await self._send_error(client, "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
            await self._send_error(client, f"Server error: {e}")

    async def _handle_connect(self, client: WebSocketClient, data: dict) -> None:
        """Handle web client connection."""
        if not self.game_server:
            await self._send_error(client, "Server not initialized")
            return

        player_name = data.get("player_name", "WebPlayer")
        client_id = str(uuid.uuid4())

        client.player_id = client_id
        client.player_name = player_name
        client.client_type = ClientType.WEB_BROWSER

        response = {
            "type": "CONNECT_ACK",
            "player_id": client_id,
            "player_name": player_name,
            "client_type": "WEB_BROWSER",
            "server_version": "1.0.0",
        }

        await client.websocket.send_json(response)
        logger.info(f"WebSocket player connected: {player_name} ({client_id[:8]})")

    async def _handle_create_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle create game request from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected")
            return

        game_name = data.get("game_name", "Web Game")
        max_players = data.get("max_players", 4)

        try:
            lobby = self.game_server.lobby_manager.create_lobby(
                player_id=client.player_id,
                player_name=client.player_name,
                game_name=game_name,
                client_type=ClientType.WEB_BROWSER,
                max_players=max_players,
            )
            client.game_id = lobby.game_id

            response = {
                "type": "CREATE_GAME",
                "game_id": lobby.game_id,
                "game_name": lobby.game_name,
                "host_player_id": lobby.host_player_id,
                "max_players": lobby.max_players,
                "current_players": len(lobby.players),
                "status": lobby.status.value,
            }
            await client.websocket.send_json(response)
            logger.info(f"WebSocket player created game: {lobby.game_name}")

        except ValueError as e:
            await self._send_error(client, f"Invalid game: {e}")

    async def _handle_join_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle join game request from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected")
            return

        game_id = data.get("game_id")
        if not game_id:
            await self._send_error(client, "No game_id provided")
            return

        lobby = self.game_server.lobby_manager.join_lobby(
            game_id=game_id,
            player_id=client.player_id,
            player_name=client.player_name,
            client_type=ClientType.WEB_BROWSER,
        )

        if not lobby:
            await self._send_error(client, "Cannot join game")
            return

        client.game_id = lobby.game_id

        response = {
            "type": "JOIN_GAME",
            "game_id": lobby.game_id,
            "game_name": lobby.game_name,
            "host_player_id": lobby.host_player_id,
            "max_players": lobby.max_players,
            "current_players": len(lobby.players),
            "status": lobby.status.value,
        }
        await client.websocket.send_json(response)

        join_event = {
            "type": "PLAYER_JOINED",
            "game_id": game_id,
            "player_id": client.player_id,
            "player_name": client.player_name,
        }
        await self._broadcast_to_lobby(game_id, join_event, exclude_client=client)

    async def _handle_leave_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle leave game request from web client."""
        if not self.game_server or not client.game_id:
            return

        game_id = client.game_id
        player_id = client.player_id

        self.game_server.lobby_manager.leave_lobby(game_id, player_id)

        response = {"type": "LEAVE_GAME", "game_id": game_id}
        await client.websocket.send_json(response)

        leave_event = {
            "type": "PLAYER_LEFT",
            "game_id": game_id,
            "player_id": player_id,
        }
        await self._broadcast_to_lobby(game_id, leave_event)

        client.game_id = None

    async def _handle_list_games(self, client: WebSocketClient) -> None:
        """Handle list games request from web client."""
        if not self.game_server:
            await self._send_error(client, "Server not initialized")
            return

        lobbies = self.game_server.lobby_manager.list_available_lobbies()
        response = {"type": "GAME_LIST", "games": lobbies}
        await client.websocket.send_json(response)

    async def _handle_ready(self, client: WebSocketClient, data: dict) -> None:
        """Handle ready status update from web client."""
        if not self.game_server or not client.game_id:
            await self._send_error(client, "Not in a game")
            return

        is_ready = data.get("ready", True)
        self.game_server.lobby_manager.set_ready(
            client.game_id, client.player_id, is_ready
        )

        lobby = self.game_server.lobby_manager.get_lobby(client.game_id)

        ready_event = {
            "type": "READY",
            "game_id": client.game_id,
            "player_id": client.player_id,
            "ready": is_ready,
            "lobby": lobby.to_dict() if lobby else None,
        }
        await self._broadcast_to_lobby(client.game_id, ready_event)

    async def _handle_start_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle start game request from web client."""
        if not self.game_server or not client.game_id:
            await self._send_error(client, "Not in a game")
            return

        lobby = self.game_server.lobby_manager.get_player_lobby(client.player_id)
        if not lobby:
            await self._send_error(client, "Not in a lobby")
            return

        if client.player_id != lobby.host_player_id:
            await self._send_error(client, "Only host can start game")
            return

        self.game_server.lobby_manager.start_game(client.game_id)
        game_session = self.game_server.game_coordinator.create_game(lobby)
        self.game_server.lobby_manager.set_game_in_progress(client.game_id)

        for net_player_id in lobby.players.keys():
            state_dict = game_session.get_game_state_for_player(net_player_id)
            if self.clients.get(net_player_id):
                ws_client = self.clients[net_player_id]
                response = {"type": "FULL_STATE", "game_state": state_dict}
                await ws_client.websocket.send_json(response)
            else:
                msg = self.protocol.create_full_state_message(state_dict, net_player_id)
                await self.game_server._send_to_player(net_player_id, msg)

        start_event = {"type": "START_GAME", "game_id": client.game_id}
        await self._broadcast_to_lobby(client.game_id, start_event)

    async def _handle_game_action(self, client: WebSocketClient, data: dict) -> None:
        """Handle game action from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected")
            return

        msg_type = data.get("type")
        if not msg_type:
            await self._send_error(client, "Missing message type")
            return

        action_data = {
            "type": msg_type.lower(),
            "token_id": data.get("token_id"),
            "destination": data.get("destination"),
            "attacker_id": data.get("attacker_id"),
            "target_id": data.get("target_id"),
            "position": data.get("position"),
            "player_id": client.player_id,
        }

        message = NetworkMessage(
            type=MessageType(msg_type),
            timestamp=time.time(),
            player_id=client.player_id,
            data=action_data,
        )

        success, msg, result_data, game_session = (
            self.game_server.game_coordinator.execute_action(
                client.player_id, self.protocol.message_to_action(message)
            )
        )

        if not success:
            error_response = {
                "type": "INVALID_ACTION",
                "action_type": msg_type,
                "reason": msg,
            }
            await client.websocket.send_json(error_response)
            return

        if game_session:
            await self._broadcast_game_state(game_session)

            if game_session.is_game_over():
                await self._handle_game_over(game_session)

    async def _handle_chat(self, client: WebSocketClient, data: dict) -> None:
        """Handle chat message from web client."""
        if not self.game_server or not client.game_id:
            return

        chat_message = data.get("message", "")
        if not chat_message:
            return

        chat_event = {
            "type": "CHAT",
            "player_id": client.player_id,
            "player_name": client.player_name,
            "message": chat_message,
        }
        await self._broadcast_to_lobby(client.game_id, chat_event)

    async def _handle_client_disconnect(self, client: WebSocketClient) -> None:
        """Handle explicit disconnect from web client."""
        await self._handle_disconnect(client)

    async def _handle_disconnect(self, client: WebSocketClient) -> None:
        """Handle client disconnection."""
        if not self.game_server:
            return

        if client.player_id:
            game_session = self.game_server.game_coordinator.get_player_game(
                client.player_id
            )
            lobby = self.game_server.lobby_manager.get_lobby_by_player(client.player_id)

            self.game_server.player_connections.pop(client.player_id, None)
            self.game_server.lobby_manager.remove_player_from_all(client.player_id)
            self.game_server.game_coordinator.remove_player(client.player_id)

            if game_session:
                disconnect_event = {
                    "type": "PLAYER_DISCONNECTED",
                    "player_id": client.player_id,
                    "player_name": client.player_name,
                    "can_reconnect": False,
                }
                await self._broadcast_to_game(
                    lobby.game_id if lobby else None, disconnect_event
                )

        logger.info(f"WebSocket client disconnected: {client.client_id}")

    async def _broadcast_to_lobby(
        self,
        game_id: str,
        message: dict,
        exclude_client: Optional[WebSocketClient] = None,
    ) -> None:
        """Broadcast message to all clients in a lobby."""
        for client in self.clients.values():
            if client.game_id == game_id and client != exclude_client:
                try:
                    await client.websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")

    async def _broadcast_to_game(self, game_id: Optional[str], message: dict) -> None:
        """Broadcast message to all clients in an active game."""
        if not game_id:
            return

        for client in self.clients.values():
            if client.game_id == game_id:
                try:
                    await client.websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")

    async def _broadcast_game_state(self, game_session) -> None:
        """Broadcast updated game state to all clients in the game."""
        if not self.game_server:
            return

        for net_player_id in game_session.network_to_game_id.keys():
            if net_player_id in self.clients:
                client = self.clients[net_player_id]
                state_dict = game_session.get_game_state_for_player(net_player_id)
                response = {"type": "FULL_STATE", "game_state": state_dict}
                try:
                    await client.websocket.send_json(response)
                except Exception as e:
                    logger.error(f"Error sending state to client: {e}")
            else:
                await self.game_server._broadcast_game_state(game_session)
                break

    async def _handle_game_over(self, game_session) -> None:
        """Handle game ending."""
        if not self.game_server:
            return

        winner_id = game_session.get_winner_network_id()
        winner_name = "Unknown"

        if winner_id:
            game_player_id = game_session.network_to_game_id[winner_id]
            winner_player = game_session.game_state.get_player(game_player_id)
            if winner_player:
                winner_name = winner_player.name

        won_msg = {
            "type": "GAME_WON",
            "winner_id": winner_id or "",
            "winner_name": winner_name,
        }
        await self._broadcast_to_game(game_session.game_id, won_msg)

        self.game_server.lobby_manager.finish_game(game_session.game_id)
        logger.info(f"Game {game_session.game_id} ended. Winner: {winner_name}")

    async def _send_error(self, client: WebSocketClient, error_msg: str) -> None:
        """Send error message to client."""
        response = {"type": "ERROR", "error": error_msg}
        try:
            await client.websocket.send_json(response)
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)

    def get_clients_in_game(self, game_id: str) -> list:
        """Get all clients in a specific game."""
        return [c for c in self.clients.values() if c.game_id == game_id]
