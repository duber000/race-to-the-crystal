"""
TCP Game Server for Race to the Crystal.

Main server that handles client connections, lobby management,
and game coordination.
"""
import asyncio
import logging
import time
import uuid
from typing import Dict, Optional, Set

from network.connection import Connection, ConnectionPool
from network.protocol import ProtocolHandler, NetworkMessage
from network.messages import MessageType, ClientType
from server.lobby import LobbyManager, GameStatus
from server.game_coordinator import GameCoordinator


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GameServer:
    """
    Main game server handling all network communication and game logic.

    Manages:
    - TCP connections from clients
    - Lobby system (game creation, joining, ready)
    - Active game sessions
    - Message routing and broadcasting
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8888):
        """
        Initialize the game server.

        Args:
            host: Host address to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port

        # Connection management
        self.connection_pool = ConnectionPool()
        self.player_connections: Dict[str, Connection] = {}  # player_id -> Connection

        # Game management
        self.lobby_manager = LobbyManager()
        self.game_coordinator = GameCoordinator()

        # Protocol handler
        self.protocol = ProtocolHandler()

        # Server state
        self.running = False
        self.server = None

        logger.info(f"Game server initialized on {host}:{port}")

    async def start(self) -> None:
        """Start the TCP server."""
        self.running = True

        self.server = await asyncio.start_server(
            self._handle_new_connection,
            self.host,
            self.port
        )

        addr = self.server.sockets[0].getsockname()
        logger.info(f"Server listening on {addr[0]}:{addr[1]}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self) -> None:
        """Stop the server gracefully."""
        logger.info("Stopping server...")
        self.running = False

        # Close all connections
        await self.connection_pool.close_all()

        # Stop server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("Server stopped")

    async def _handle_new_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle a new TCP connection.

        Args:
            reader: Stream reader
            writer: Stream writer
        """
        # Create connection wrapper
        conn_id = str(uuid.uuid4())
        connection = Connection(reader, writer, conn_id)

        # Add to connection pool
        self.connection_pool.add_connection(conn_id, connection)

        # Wait for CONNECT message
        try:
            connect_msg = await asyncio.wait_for(
                connection.receive_message(),
                timeout=10.0  # 10 second timeout for initial connect
            )

            if not connect_msg or connect_msg.type != MessageType.CONNECT:
                logger.warning(f"Invalid CONNECT message from {conn_id}")
                await connection.close()
                return

            # Process connection
            player_id = await self._handle_connect(connection, connect_msg, conn_id)

            if not player_id:
                await connection.close()
                return

            # Start message loop
            await connection.start_message_loop(
                lambda msg: self._handle_message(player_id, msg)
            )

        except asyncio.TimeoutError:
            logger.warning(f"Connection timeout for {conn_id}")
            await connection.close()
        except Exception as e:
            logger.error(f"Error handling connection {conn_id}: {e}", exc_info=True)
            await connection.close()
        finally:
            self.connection_pool.remove_connection(conn_id)

    async def _handle_connect(
        self,
        connection: Connection,
        message: NetworkMessage,
        conn_id: str
    ) -> Optional[str]:
        """
        Handle initial CONNECT message.

        Args:
            connection: Client connection
            message: CONNECT message
            conn_id: Connection ID

        Returns:
            Assigned player_id, or None if connection failed
        """
        data = message.data or {}
        player_name = data.get("player_name", "Unknown")
        client_type_str = data.get("client_type", "HUMAN")

        try:
            client_type = ClientType(client_type_str)
        except ValueError:
            client_type = ClientType.HUMAN

        # Assign player ID
        player_id = str(uuid.uuid4())

        # Store connection
        self.player_connections[player_id] = connection

        # Send CONNECT_ACK
        session_data = {
            "player_id": player_id,
            "player_name": player_name,
            "client_type": client_type.value,
            "server_version": "1.0.0",
        }

        ack_msg = self.protocol.create_connect_ack_message(player_id, session_data)
        await connection.send_message(ack_msg)

        logger.info(
            f"Player connected: {player_name} ({client_type.value}) "
            f"ID: {player_id[:8]}"
        )

        return player_id

    async def _handle_disconnect(self, player_id: str) -> None:
        """
        Handle player disconnection.

        Args:
            player_id: Disconnecting player
        """
        logger.info(f"Player disconnected: {player_id[:8]}")

        # Remove from lobby if in one
        self.lobby_manager.remove_player_from_all(player_id)

        # Remove from game if in one
        game_id = self.game_coordinator.remove_player(player_id)

        # Remove connection
        self.player_connections.pop(player_id, None)

        # TODO: Notify other players in lobby/game

    async def _handle_message(
        self,
        player_id: str,
        message: NetworkMessage
    ) -> None:
        """
        Route and handle a message from a player.

        Args:
            player_id: Sending player
            message: Received message
        """
        logger.debug(f"Received {message.type.value} from {player_id[:8]}")

        try:
            # Route message based on type
            if message.type == MessageType.DISCONNECT:
                await self._handle_disconnect(player_id)

            elif message.type == MessageType.HEARTBEAT:
                await self._handle_heartbeat(player_id)

            elif message.type == MessageType.CREATE_GAME:
                await self._handle_create_game(player_id, message)

            elif message.type == MessageType.JOIN_GAME:
                await self._handle_join_game(player_id, message)

            elif message.type == MessageType.LEAVE_GAME:
                await self._handle_leave_game(player_id, message)

            elif message.type == MessageType.LIST_GAMES:
                await self._handle_list_games(player_id)

            elif message.type == MessageType.READY:
                await self._handle_ready(player_id, message)

            elif message.type == MessageType.START_GAME:
                await self._handle_start_game(player_id, message)

            # Game actions
            elif message.type in [MessageType.MOVE, MessageType.ATTACK, MessageType.DEPLOY, MessageType.END_TURN]:
                await self._handle_game_action(player_id, message)

            else:
                logger.warning(f"Unhandled message type: {message.type.value}")

        except Exception as e:
            logger.error(f"Error handling message {message.type.value}: {e}", exc_info=True)
            await self._send_error(player_id, f"Server error: {e}")

    async def _handle_heartbeat(self, player_id: str) -> None:
        """Respond to heartbeat."""
        connection = self.player_connections.get(player_id)
        if connection:
            ack_msg = NetworkMessage(
                type=MessageType.HEARTBEAT_ACK,
                timestamp=message.timestamp
            )
            await connection.send_message(ack_msg)

    async def _handle_create_game(self, player_id: str, message: NetworkMessage) -> None:
        """Handle CREATE_GAME request."""
        data = message.data or {}
        game_name = data.get("game_name", "New Game")
        max_players = data.get("max_players", 4)

        # Get player info (need to determine client type)
        # For now, assume from connection metadata
        player_name = data.get("player_name", "Player")
        client_type = ClientType.HUMAN  # Default

        # Create lobby
        lobby = self.lobby_manager.create_lobby(
            player_id=player_id,
            player_name=player_name,
            game_name=game_name,
            client_type=client_type,
            max_players=max_players
        )

        # Send confirmation
        response = NetworkMessage(
            type=MessageType.CREATE_GAME,
            timestamp=message.timestamp,
            player_id=player_id,
            data=lobby.to_dict()
        )

        await self._send_to_player(player_id, response)

    async def _handle_join_game(self, player_id: str, message: NetworkMessage) -> None:
        """Handle JOIN_GAME request."""
        data = message.data or {}
        game_id = data.get("game_id")

        if not game_id:
            await self._send_error(player_id, "No game_id provided")
            return

        player_name = data.get("player_name", "Player")
        client_type = ClientType.HUMAN

        lobby = self.lobby_manager.join_lobby(game_id, player_id, player_name, client_type)

        if not lobby:
            await self._send_error(player_id, "Cannot join game (full or not found)")
            return

        # Send confirmation to joiner
        response = NetworkMessage(
            type=MessageType.JOIN_GAME,
            timestamp=message.timestamp,
            player_id=player_id,
            data=lobby.to_dict()
        )
        await self._send_to_player(player_id, response)

        # Broadcast PLAYER_JOINED to all players in lobby
        join_event = NetworkMessage(
            type=MessageType.PLAYER_JOINED,
            timestamp=message.timestamp,
            data={
                "game_id": game_id,
                "player_id": player_id,
                "player_name": player_name,
                "lobby": lobby.to_dict()
            }
        )
        await self._broadcast_to_lobby(game_id, join_event)

    async def _handle_leave_game(self, player_id: str, message: NetworkMessage) -> None:
        """Handle LEAVE_GAME request."""
        lobby = self.lobby_manager.get_player_lobby(player_id)

        if not lobby:
            await self._send_error(player_id, "Not in a game")
            return

        game_id = lobby.game_id
        self.lobby_manager.leave_lobby(game_id, player_id)

        # Notify player
        response = NetworkMessage(
            type=MessageType.LEAVE_GAME,
            timestamp=message.timestamp,
            player_id=player_id,
            data={"game_id": game_id}
        )
        await self._send_to_player(player_id, response)

        # Broadcast to remaining players
        leave_event = NetworkMessage(
            type=MessageType.PLAYER_LEFT,
            timestamp=message.timestamp,
            data={"game_id": game_id, "player_id": player_id}
        )
        await self._broadcast_to_lobby(game_id, leave_event)

    async def _handle_list_games(self, player_id: str) -> None:
        """Handle LIST_GAMES request."""
        available_lobbies = self.lobby_manager.list_available_lobbies()

        response = NetworkMessage(
            type=MessageType.GAME_LIST,
            timestamp=time.time(),
            player_id=player_id,
            data={"games": available_lobbies}
        )

        await self._send_to_player(player_id, response)

    async def _handle_ready(self, player_id: str, message: NetworkMessage) -> None:
        """Handle READY message."""
        data = message.data or {}
        is_ready = data.get("ready", True)

        lobby = self.lobby_manager.get_player_lobby(player_id)
        if not lobby:
            await self._send_error(player_id, "Not in a lobby")
            return

        self.lobby_manager.set_ready(lobby.game_id, player_id, is_ready)

        # Broadcast ready status to all players
        ready_event = NetworkMessage(
            type=MessageType.READY,
            timestamp=message.timestamp,
            data={
                "game_id": lobby.game_id,
                "player_id": player_id,
                "ready": is_ready,
                "lobby": lobby.to_dict()
            }
        )
        await self._broadcast_to_lobby(lobby.game_id, ready_event)

    async def _handle_start_game(self, player_id: str, message: NetworkMessage) -> None:
        """Handle START_GAME request."""
        lobby = self.lobby_manager.get_player_lobby(player_id)

        if not lobby:
            await self._send_error(player_id, "Not in a lobby")
            return

        if player_id != lobby.host_player_id:
            await self._send_error(player_id, "Only host can start game")
            return

        # Try to start the game
        lobby = self.lobby_manager.start_game(lobby.game_id)
        if not lobby:
            await self._send_error(player_id, "Cannot start game (not all players ready)")
            return

        # Create game session
        game_session = self.game_coordinator.create_game(lobby)

        # Mark lobby as in progress
        self.lobby_manager.set_game_in_progress(lobby.game_id)

        # Send full game state to all players
        for net_player_id in lobby.players.keys():
            state_dict = game_session.get_game_state_for_player(net_player_id)

            state_msg = self.protocol.create_full_state_message(state_dict, net_player_id)
            await self._send_to_player(net_player_id, state_msg)

        # Broadcast START_GAME event
        start_event = NetworkMessage(
            type=MessageType.START_GAME,
            timestamp=message.timestamp,
            data={"game_id": lobby.game_id}
        )
        await self._broadcast_to_lobby(lobby.game_id, start_event)

        logger.info(f"Started game {lobby.game_id} ({lobby.game_name})")

    async def _handle_game_action(self, player_id: str, message: NetworkMessage) -> None:
        """Handle game action (MOVE, ATTACK, DEPLOY, END_TURN)."""
        # Convert message to action
        action = self.protocol.message_to_action(message)

        # Execute action
        success, msg, result_data, game_session = self.game_coordinator.execute_action(
            player_id, action
        )

        if not success:
            # Send error to player
            error_msg = self.protocol.create_invalid_action_message(
                action.action_type, msg, player_id
            )
            await self._send_to_player(player_id, error_msg)
            return

        # Action successful - broadcast state update to all players in game
        if game_session:
            await self._broadcast_game_state(game_session)

            # Check for game over
            if game_session.is_game_over():
                await self._handle_game_over(game_session)

    async def _broadcast_game_state(self, game_session) -> None:
        """Broadcast updated game state to all players in a game."""
        for net_player_id in game_session.network_to_game_id.keys():
            state_dict = game_session.get_game_state_for_player(net_player_id)

            state_msg = self.protocol.create_full_state_message(state_dict, net_player_id)
            await self._send_to_player(net_player_id, state_msg)

    async def _handle_game_over(self, game_session) -> None:
        """Handle game ending."""
        winner_id = game_session.get_winner_network_id()
        winner_name = "Unknown"

        if winner_id:
            # Get winner name
            game_player_id = game_session.network_to_game_id[winner_id]
            winner_player = game_session.game_state.get_player(game_player_id)
            if winner_player:
                winner_name = winner_player.name

        # Broadcast game won
        won_msg = self.protocol.create_game_won_message(winner_id or "", winner_name)
        await self._broadcast_to_game(game_session.game_id, won_msg)

        # Mark game as finished
        self.lobby_manager.finish_game(game_session.game_id)

        logger.info(f"Game {game_session.game_id} ended. Winner: {winner_name}")

    async def _send_to_player(self, player_id: str, message: NetworkMessage) -> bool:
        """Send a message to a specific player."""
        connection = self.player_connections.get(player_id)
        if not connection:
            return False

        return await connection.send_message(message)

    async def _send_error(self, player_id: str, error_msg: str) -> None:
        """Send an error message to a player."""
        error = self.protocol.create_error_message(error_msg, player_id)
        await self._send_to_player(player_id, error)

    async def _broadcast_to_lobby(self, game_id: str, message: NetworkMessage) -> None:
        """Broadcast a message to all players in a lobby."""
        lobby = self.lobby_manager.get_lobby(game_id)
        if not lobby:
            return

        for player_id in lobby.players.keys():
            await self._send_to_player(player_id, message)

    async def _broadcast_to_game(self, game_id: str, message: NetworkMessage) -> None:
        """Broadcast a message to all players in an active game."""
        game_session = self.game_coordinator.get_game(game_id)
        if not game_session:
            return

        for player_id in game_session.network_to_game_id.keys():
            await self._send_to_player(player_id, message)
