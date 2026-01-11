"""
WebSocket Handler for Race to the Crystal web clients.

Handles WebSocket connections from Babylon.js web clients,
integrating with the main game server for lobby and game actions.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Optional
from dataclasses import dataclass, field

from aiohttp import WSMsgType, web

from network.messages import MessageType, ClientType
from network.protocol import NetworkMessage, ProtocolHandler
from server.rate_limiter import RateLimiter
from server.lobby import validate_player_name, validate_game_name


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
    ip_address: Optional[str] = None

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
        self.rate_limiter = RateLimiter()

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
        # Get client IP address
        ip_address = request.remote or "unknown"
        if "X-Real-IP" in request.headers:
            ip_address = request.headers["X-Real-IP"]
        elif "X-Forwarded-For" in request.headers:
            ip_address = request.headers["X-Forwarded-For"].split(",")[0].strip()

        # Check rate limit for connections
        allowed, error_msg = self.rate_limiter.check_connection(ip_address)
        if not allowed:
            logger.warning(f"Rate limited connection from {ip_address}: {error_msg}")
            # Return error response
            ws = web.WebSocketResponse(max_msg_size=64 * 1024)  # 64KB limit
            await ws.prepare(request)
            await ws.send_json({
                "type": "ERROR",
                "message": error_msg
            })
            await ws.close()
            return ws

        # Accept connection with 64KB message size limit (reduced from 10MB)
        ws = web.WebSocketResponse(max_msg_size=64 * 1024)
        await ws.prepare(request)

        client_id = str(uuid.uuid4())
        client = WebSocketClient(
            client_id=client_id,
            websocket=ws,
            ip_address=ip_address
        )
        self.clients[client_id] = client

        logger.info(f"WebSocket client connected: {client_id} from {ip_address}")

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
            # Release connection rate limit slot
            if client.ip_address:
                self.rate_limiter.release_connection(client.ip_address)
            # Remove client using player_id if set, otherwise use client_id
            cleanup_id = client.player_id if client.player_id else client_id
            if cleanup_id in self.clients:
                del self.clients[cleanup_id]

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

        # Validate player name
        try:
            validate_player_name(player_name)
        except ValueError as e:
            await self._send_error(client, f"Invalid player name: {e}")
            logger.warning(f"Invalid player name rejected: {player_name} - {e}")
            return

        player_id = str(uuid.uuid4())

        # Update client with player info
        client.player_id = player_id
        client.player_name = player_name
        client.client_type = ClientType.WEB_BROWSER

        # Re-register client with player_id as key (remove old client_id key)
        old_client_id = client.client_id
        if old_client_id in self.clients:
            del self.clients[old_client_id]
        self.clients[player_id] = client

        # Register client type with game server for mixed-client support
        self.game_server.player_client_types[player_id] = ClientType.WEB_BROWSER

        response = {
            "type": "CONNECT_ACK",
            "player_id": player_id,
            "player_name": player_name,
            "client_type": "WEB_BROWSER",
            "server_version": "1.0.0",
        }

        await client.websocket.send_json(response)
        logger.info(f"WebSocket player connected: {player_name} ({player_id[:8]})")

    async def _handle_create_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle create game request from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected")
            return

        # Check game creation rate limit
        allowed, error_msg = self.rate_limiter.check_game_creation(client.player_id)
        if not allowed:
            await self._send_error(client, error_msg)
            return

        game_name = data.get("game_name", "Web Game")
        max_players = data.get("max_players", 4)

        # Validate game name
        try:
            validate_game_name(game_name)
        except ValueError as e:
            await self._send_error(client, f"Invalid game name: {e}")
            logger.warning(f"Invalid game name rejected: {game_name} - {e}")
            return

        # Validate max_players
        if not isinstance(max_players, int) or max_players < 2 or max_players > 4:
            await self._send_error(client, "Invalid max_players: must be between 2 and 4")
            return

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
                "players": lobby.get_player_list(),
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
            "players": lobby.get_player_list(),
        }
        await client.websocket.send_json(response)

        join_event = {
            "type": "PLAYER_JOINED",
            "game_id": game_id,
            "player_id": client.player_id,
            "player_name": client.player_name,
            "lobby": lobby.to_dict(),
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
        """Handle start game request from web client - delegates to main server."""
        if not self.game_server or not client.game_id:
            await self._send_error(client, "Not in a game")
            return

        # Create NetworkMessage and delegate to main TCP server's handler
        # This ensures consistent behavior and proper broadcasting to all client types
        message = NetworkMessage(
            type=MessageType.START_GAME,
            timestamp=time.time(),
            player_id=client.player_id,
            data={"game_id": client.game_id},
        )

        # Delegate to main server's start game handler (which handles AI spawning & broadcasting)
        await self.game_server._handle_start_game(client.player_id, message)

    async def _handle_game_action(self, client: WebSocketClient, data: dict) -> None:
        """Handle game action from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected")
            return

        # Check action rate limit
        allowed, error_msg = self.rate_limiter.check_action(client.player_id)
        if not allowed:
            await self._send_error(client, error_msg)
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
            "defender_id": data.get("defender_id") or data.get("target_id"),
            "position": data.get("position"),
            "health_value": data.get("health_value"),
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

            # Clean up game server tracking
            self.game_server.player_connections.pop(client.player_id, None)
            self.game_server.player_client_types.pop(client.player_id, None)
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

        logger.info(
            f"[WebSocket] Broadcasting game state to {len(game_session.network_to_game_id)} players"
        )
        logger.info(
            f"[WebSocket] Game state - turn_phase: {game_session.game_state.turn_phase.name}, "
            f"current_turn: {game_session.game_state.current_turn_player_id}"
        )

        for net_player_id in game_session.network_to_game_id.keys():
            if net_player_id in self.clients:
                client = self.clients[net_player_id]
                state_dict = game_session.get_game_state_for_player(net_player_id)
                logger.info(
                    f"[WebSocket] Sending state to {net_player_id[:8]} - turn_phase: {state_dict.get('turn_phase')}"
                )
                response = {"type": "FULL_STATE", "game_state": state_dict}
                try:
                    await client.websocket.send_json(response)
                    logger.info(f"[WebSocket] Successfully sent state to {net_player_id[:8]}")
                except Exception as e:
                    logger.error(f"Error sending state to client: {e}")
            else:
                logger.warning(
                    f"[WebSocket] Player {net_player_id[:8]} not in clients dict, delegating to game_server"
                )
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
