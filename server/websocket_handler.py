"""
WebSocket Handler for Race to the Crystal web clients.

Handles WebSocket connections from Babylon.js web clients,
integrating with the main game server for lobby and game actions.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field

import aiohttp
from aiohttp import WSMsgType, web

from network.messages import MessageType, ClientType
from network.protocol import NetworkMessage
from server.rate_limiter import RateLimiter
from server.lobby import validate_player_name
from server.action_validation import validate_action_fields, normalize_action_data
from shared.errors import (
    ServerError,
    ErrorCode,
    format_websocket_error,
)


logger = logging.getLogger(__name__)


@dataclass
class WebSocketClient:
    """Represents a connected web browser client."""

    client_id: str
    player_id: str | None = None
    player_name: str = "Unknown"
    client_type: ClientType = ClientType.WEB_BROWSER
    websocket: web.WebSocketResponse | None = None
    game_id: str | None = None
    connected_at: float = field(default_factory=time.time)
    ip_address: str | None = None

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
        self.clients: dict[str, WebSocketClient] = {}
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
            await ws.send_json({"type": "ERROR", "message": error_msg})
            await ws.close()
            return ws

        # Accept connection with 64KB message size limit (reduced from 10MB)
        ws = web.WebSocketResponse(max_msg_size=64 * 1024)
        await ws.prepare(request)

        client_id = str(uuid.uuid7())
        client = WebSocketClient(
            client_id=client_id, websocket=ws, ip_address=ip_address
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

        except aiohttp.WSServerHandshakeError as e:
            logger.error(f"WebSocket handshake failed for {client_id}: {e}")
        except ConnectionResetError as e:
            logger.warning(f"Connection reset by {client_id}: {e}")
        except aiohttp.ClientError as e:
            logger.error(f"WebSocket client error for {client_id}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected WebSocket error for {client_id}: {e}", exc_info=True
            )
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
            elif msg_type == "SSE_FALLBACK_REQUEST":
                await self._handle_sse_fallback_request(client, data)
            elif msg_type == "DISCONNECT":
                await self._handle_client_disconnect(client)
            else:
                logger.warning(f"Unknown WebSocket message type: {msg_type}")
                await self._send_error(
                    client, f"Unknown message type: {msg_type}", ErrorCode.INVALID_VALUE
                )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {client.client_id}: {e}")
            await self._send_error(
                client, "Invalid JSON format", ErrorCode.INVALID_VALUE
            )
        except ValueError as e:
            logger.warning(f"Invalid message data from {client.client_id}: {e}")
            await self._send_error(
                client, f"Invalid request: {e}", ErrorCode.INVALID_VALUE
            )
        except KeyError as e:
            logger.warning(f"Missing message field from {client.client_id}: {e}")
            await self._send_error(
                client, f"Missing field: {e}", ErrorCode.MISSING_FIELD
            )
        except Exception as e:
            logger.error(
                f"Unexpected error handling WebSocket message: {e}", exc_info=True
            )
            await self._send_error(
                client, f"Server error: {e}", ErrorCode.INTERNAL_ERROR
            )

    async def _delegate_to_server(
        self, client: WebSocketClient, message: NetworkMessage
    ) -> None:
        """Delegate a NetworkMessage to the main server for handling."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected", ErrorCode.UNAUTHORIZED)
            return

        await self.game_server._handle_message(client.player_id, message)

    def _sync_client_game_id(self, client: WebSocketClient) -> None:
        """Sync client game_id from lobby manager after server-side updates."""
        if not self.game_server or not client.player_id:
            return

        lobby = self.game_server.lobby_manager.get_player_lobby(client.player_id)
        client.game_id = lobby.game_id if lobby else None

    async def _handle_connect(self, client: WebSocketClient, data: dict) -> None:
        """Handle web client connection."""
        if not self.game_server:
            await self._send_error(
                client, "Server not initialized", ErrorCode.SERVER_NOT_INITIALIZED
            )
            return

        player_name = data.get("player_name", "WebPlayer")

        # Validate player name
        try:
            validate_player_name(player_name)
        except ValueError as e:
            await self._send_error(
                client, f"Invalid player name: {e}", ErrorCode.INVALID_VALUE
            )
            logger.warning(f"Invalid player name rejected: {player_name} - {e}")
            return

        player_id = str(uuid.uuid7())

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

        if client.websocket:
            await client.websocket.send_json(response)
        logger.info(f"WebSocket player connected: {player_name} ({player_id[:8]})")

    async def _handle_create_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle create game request from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected", ErrorCode.UNAUTHORIZED)
            return

        # Check game creation rate limit
        allowed, error_msg = self.rate_limiter.check_game_creation(client.player_id)
        if not allowed:
            await self._send_error(client, error_msg, ErrorCode.FORBIDDEN)
            return

        game_name = data.get("game_name", "Web Game")
        max_players = data.get("max_players", 4)

        # Validate max_players
        if not isinstance(max_players, int) or max_players < 2 or max_players > 4:
            await self._send_error(
                client,
                "Invalid max_players: must be between 2 and 4",
                ErrorCode.INVALID_VALUE,
            )
            return

        message = NetworkMessage(
            type=MessageType.CREATE_GAME,
            timestamp=time.time(),
            player_id=client.player_id,
            data={
                "game_name": game_name,
                "max_players": max_players,
                "player_name": client.player_name,
            },
        )
        await self._delegate_to_server(client, message)
        self._sync_client_game_id(client)

    async def _handle_join_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle join game request from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected", ErrorCode.UNAUTHORIZED)
            return

        game_id = data.get("game_id")
        if not game_id:
            await self._send_error(
                client, "No game_id provided", ErrorCode.MISSING_FIELD
            )
            return
        message = NetworkMessage(
            type=MessageType.JOIN_GAME,
            timestamp=time.time(),
            player_id=client.player_id,
            data={"game_id": game_id, "player_name": client.player_name},
        )
        await self._delegate_to_server(client, message)
        self._sync_client_game_id(client)

    async def _handle_leave_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle leave game request from web client."""
        if not self.game_server or not client.game_id:
            return

        message = NetworkMessage(
            type=MessageType.LEAVE_GAME,
            timestamp=time.time(),
            player_id=client.player_id,
            data={"game_id": client.game_id},
        )
        await self._delegate_to_server(client, message)
        self._sync_client_game_id(client)

    async def _handle_list_games(self, client: WebSocketClient) -> None:
        """Handle list games request from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected", ErrorCode.UNAUTHORIZED)
            return

        message = NetworkMessage(
            type=MessageType.LIST_GAMES,
            timestamp=time.time(),
            player_id=client.player_id,
        )
        await self._delegate_to_server(client, message)

    async def _handle_ready(self, client: WebSocketClient, data: dict) -> None:
        """Handle ready status update from web client."""
        if not self.game_server or not client.game_id:
            await self._send_error(
                client, "Not in a game", ErrorCode.PLAYER_NOT_IN_GAME
            )
            return

        is_ready = data.get("ready", True)
        message = NetworkMessage(
            type=MessageType.READY,
            timestamp=time.time(),
            player_id=client.player_id,
            data={"ready": is_ready},
        )
        await self._delegate_to_server(client, message)

    async def _handle_start_game(self, client: WebSocketClient, data: dict) -> None:
        """Handle start game request from web client - delegates to main server."""
        if not self.game_server or not client.game_id:
            await self._send_error(
                client, "Not in a game", ErrorCode.PLAYER_NOT_IN_GAME
            )
            return

        message = NetworkMessage(
            type=MessageType.START_GAME,
            timestamp=time.time(),
            player_id=client.player_id,
            data={"game_id": client.game_id},
        )
        await self._delegate_to_server(client, message)

    async def _handle_game_action(self, client: WebSocketClient, data: dict) -> None:
        """Handle game action from web client."""
        if not self.game_server or not client.player_id:
            await self._send_error(client, "Not connected", ErrorCode.UNAUTHORIZED)
            return

        # Check action rate limit
        allowed, error_msg = self.rate_limiter.check_action(client.player_id)
        if not allowed:
            await self._send_error(client, error_msg, ErrorCode.FORBIDDEN)
            return

        msg_type = data.get("type")
        if not msg_type:
            await self._send_error(
                client, "Missing message type", ErrorCode.MISSING_FIELD
            )
            return

        # Validate action data using shared validation
        validation_result = validate_action_fields(msg_type, data)
        if validation_result:
            _, error_code, error_msg = validation_result
            await self._send_error(client, error_msg, error_code)
            return

        action_data = normalize_action_data(data)
        action_data["player_id"] = client.player_id

        message = NetworkMessage(
            type=MessageType(msg_type),
            timestamp=time.time(),
            player_id=client.player_id,
            data=action_data,
        )
        await self._delegate_to_server(client, message)

    async def _handle_sse_fallback_request(
        self, client: WebSocketClient, data: dict
    ) -> None:
        """Handle SSE fallback request from web client - re-enable WebSocket state updates."""
        if not self.game_server or not client.game_id or not client.player_id:
            await self._send_error(client, "Not in a game")
            return

        game_id = client.game_id
        player_id = client.player_id

        logger.info(f"SSE fallback request from {player_id[:8]} for game {game_id}")

        # Send current game state immediately via WebSocket
        game_session = self.game_server.game_coordinator.get_game(game_id)
        if game_session:
            state_dict = game_session.get_game_state_for_player(player_id)
            if state_dict is None:
                logger.warning(f"Could not get game state for player {player_id[:8]}")
                return
            response = {"type": "FULL_STATE", "game_state": state_dict}
            try:
                if client.websocket:
                    await client.websocket.send_json(response)
                    logger.info(
                        f"[WebSocket] Sent FULL_STATE to {player_id[:8]} (fallback mode)"
                    )
            except aiohttp.ClientError as e:
                logger.warning(f"WebSocket error sending fallback state: {e}")
            except ConnectionError as e:
                logger.warning(f"Connection lost sending fallback state: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error sending fallback state: {e}", exc_info=True
                )

    async def _handle_chat(self, client: WebSocketClient, data: dict) -> None:
        """Handle chat message from web client."""
        if not self.game_server or not client.game_id:
            return

        chat_message = data.get("message", "")
        if not chat_message:
            return

        message = NetworkMessage(
            type=MessageType.CHAT,
            timestamp=time.time(),
            player_id=client.player_id,
            data={"message": chat_message},
        )
        await self._delegate_to_server(client, message)

    async def _handle_client_disconnect(self, client: WebSocketClient) -> None:
        """Handle explicit disconnect from web client."""
        await self._handle_disconnect(client)

    async def _handle_disconnect(self, client: WebSocketClient) -> None:
        """Handle client disconnection by delegating to GameServer."""
        if not self.game_server:
            return

        if client.player_id:
            await self.game_server.handle_player_disconnect(
                client.player_id, explicit=False, allow_reconnect=False
            )

        logger.info(f"WebSocket client disconnected: {client.client_id}")

    async def _broadcast_to_game(self, game_id: str | None, message: dict) -> None:
        """Broadcast message to all clients in an active game."""
        if not game_id:
            return

        for client in self.clients.values():
            if client.game_id == game_id:
                try:
                    if client.websocket:
                        await client.websocket.send_json(message)
                except aiohttp.ClientError as e:
                    logger.warning(f"WebSocket error broadcasting: {e}")
                except ConnectionError as e:
                    logger.warning(f"Connection lost broadcasting: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error broadcasting: {e}", exc_info=True)

    async def _broadcast_game_state(self, game_session) -> None:
        """Broadcast updated game state to all clients in the game.

        Delegates to the main game server to avoid duplication.
        """
        if not self.game_server:
            return

        await self.game_server._broadcast_game_state(game_session)

    async def _handle_game_over(self, game_session) -> None:
        """Handle game ending.

        Delegates to the main game server to avoid duplication.
        """
        if not self.game_server:
            return

        await self.game_server._handle_game_over(game_session)

    async def _send_error(
        self,
        client: WebSocketClient,
        error_msg: str | None,
        error_code: str = "unknown_error",
    ) -> None:
        """Send error message to client using standardized format."""
        error = ServerError(error_code, error_msg or "Unknown error")
        response = format_websocket_error(error)
        try:
            if client.websocket:
                await client.websocket.send_json(response)
        except aiohttp.ClientError as e:
            logger.warning(f"WebSocket error sending error message: {e}")
        except ConnectionError as e:
            logger.warning(f"Connection lost sending error message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending error message: {e}", exc_info=True)

    def get_client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.clients)

    def get_clients_in_game(self, game_id: str) -> list:
        """Get all clients in a specific game."""
        return [c for c in self.clients.values() if c.game_id == game_id]
