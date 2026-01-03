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
from server.ai_spawner import AISpawner


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
        self.player_client_types: Dict[str, ClientType] = {}  # player_id -> ClientType

        # Reconnection support
        self.disconnected_players: Dict[str, Dict] = {}  # player_id -> disconnect info
        self.reconnect_timeout = 300.0  # 5 minutes

        # Game management
        self.lobby_manager = LobbyManager()
        self.game_coordinator = GameCoordinator()
        self.ai_spawner = AISpawner()

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

        # Cleanup all AI processes
        await self.ai_spawner.cleanup_all()

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

        # Wait for CONNECT or RECONNECT message
        try:
            initial_msg = await asyncio.wait_for(
                connection.receive_message(),
                timeout=10.0  # 10 second timeout for initial connect
            )

            if not initial_msg:
                logger.warning(f"No message received from {conn_id}")
                await connection.close()
                return

            # Handle CONNECT or RECONNECT
            player_id = None
            if initial_msg.type == MessageType.CONNECT:
                player_id = await self._handle_connect(connection, initial_msg, conn_id)
            elif initial_msg.type == MessageType.RECONNECT:
                player_id = await self._handle_reconnect(connection, initial_msg, conn_id)
            else:
                logger.warning(f"Invalid initial message type from {conn_id}: {initial_msg.type}")
                await connection.close()
                return

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

        # Store connection and client type
        self.player_connections[player_id] = connection
        self.player_client_types[player_id] = client_type

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

    async def _handle_reconnect(
        self,
        connection: Connection,
        message: NetworkMessage,
        conn_id: str
    ) -> Optional[str]:
        """
        Handle RECONNECT message from a returning player.

        Args:
            connection: Client connection
            message: RECONNECT message
            conn_id: Connection ID

        Returns:
            Player ID if reconnection successful, None otherwise
        """
        player_id = message.player_id
        data = message.data or {}
        game_id = data.get("game_id")

        logger.info(f"Reconnection attempt from {player_id[:8] if player_id else 'unknown'}")

        # Validate player_id
        if not player_id:
            await connection.send_message(
                self.protocol.create_reconnect_failed_message(
                    "", "No player ID provided"
                )
            )
            return None

        # Check if player is in disconnected list
        if player_id not in self.disconnected_players:
            await connection.send_message(
                self.protocol.create_reconnect_failed_message(
                    player_id, "Player not found or reconnection timeout expired"
                )
            )
            return None

        # Check timeout
        disconnect_info = self.disconnected_players[player_id]
        disconnect_time = disconnect_info["disconnect_time"]
        if time.time() - disconnect_time > self.reconnect_timeout:
            # Timeout expired - remove player completely
            self.disconnected_players.pop(player_id)
            self.lobby_manager.remove_player_from_all(player_id)
            self.game_coordinator.remove_player(player_id)
            self.player_client_types.pop(player_id, None)

            await connection.send_message(
                self.protocol.create_reconnect_failed_message(
                    player_id, "Reconnection timeout expired"
                )
            )
            return None

        # Validate game_id if provided
        saved_game_id = disconnect_info.get("game_id")
        if game_id and saved_game_id and game_id != saved_game_id:
            await connection.send_message(
                self.protocol.create_reconnect_failed_message(
                    player_id, f"Game ID mismatch (expected {saved_game_id})"
                )
            )
            return None

        # Reconnection successful - restore connection
        self.player_connections[player_id] = connection
        self.disconnected_players.pop(player_id)

        # Get current game state
        game_session = disconnect_info.get("game_session")
        session_data = {
            "player_id": player_id,
            "game_id": saved_game_id,
            "reconnected": True,
        }

        # Send RECONNECT_ACK with current game state
        ack_msg = self.protocol.create_reconnect_ack_message(
            player_id, saved_game_id or "", session_data
        )
        await connection.send_message(ack_msg)

        # Send full state sync
        if game_session and saved_game_id:
            lobby = self.lobby_manager.get_lobby(saved_game_id)
            if lobby:
                await self._send_full_state(player_id, lobby)

        logger.info(
            f"Player {player_id[:8]} successfully reconnected to game {saved_game_id[:8] if saved_game_id else 'N/A'}"
        )

        # Notify other players that player reconnected
        if game_session:
            reconnect_msg = NetworkMessage(
                type=MessageType.PLAYER_RECONNECTED,
                timestamp=time.time(),
                data={"player_id": player_id, "player_name": player_name}
            )
            await self._broadcast_to_game(saved_game_id, reconnect_msg)
        elif saved_game_id:
            # Still in lobby
            lobby = self.lobby_manager.get_lobby(saved_game_id)
            if lobby:
                reconnect_msg = NetworkMessage(
                    type=MessageType.PLAYER_RECONNECTED,
                    timestamp=time.time(),
                    data={"player_id": player_id, "player_name": player_name}
                )
                await self._broadcast_to_lobby(saved_game_id, reconnect_msg)

        return player_id

    async def _handle_disconnect(self, player_id: str, explicit: bool = False) -> None:
        """
        Handle player disconnection.

        Args:
            player_id: Disconnecting player
            explicit: True if player explicitly disconnected, False if connection lost
        """
        logger.info(f"Player disconnected: {player_id[:8]} (explicit={explicit})")

        # Remove connection
        self.player_connections.pop(player_id, None)

        # Check if player is in an active game
        game_session = self.game_coordinator.get_player_game(player_id)

        if game_session and not explicit:
            # Keep client_type for reconnection
            # Save disconnection info for reconnection
            lobby = self.lobby_manager.get_lobby_by_player(player_id)
            self.disconnected_players[player_id] = {
                "disconnect_time": time.time(),
                "game_id": lobby.game_id if lobby else None,
                "game_session": game_session,
            }
            logger.info(f"Player {player_id[:8]} marked for reconnection (timeout in {self.reconnect_timeout}s)")

            # Notify other players that player disconnected but can reconnect
            if lobby:
                player_name = lobby.players.get(player_id, {}).get("name", "Unknown")
                disconnect_msg = NetworkMessage(
                    type=MessageType.PLAYER_DISCONNECTED,
                    timestamp=time.time(),
                    data={"player_id": player_id, "player_name": player_name, "can_reconnect": True}
                )

                if game_session:
                    # In active game
                    await self._broadcast_to_game(lobby.game_id, disconnect_msg)
                else:
                    # In lobby
                    await self._broadcast_to_lobby(lobby.game_id, disconnect_msg)
        else:
            # Explicit disconnect or not in game - remove completely
            # Get player info before removing
            lobby = self.lobby_manager.get_lobby_by_player(player_id)
            player_name = "Unknown"
            game_id = None

            if lobby:
                player_name = lobby.players.get(player_id, {}).get("name", "Unknown")
                game_id = lobby.game_id
                in_active_game = lobby.status == GameStatus.IN_PROGRESS

            # Remove from lobby/game and client type tracking
            self.lobby_manager.remove_player_from_all(player_id)
            self.game_coordinator.remove_player(player_id)
            self.player_client_types.pop(player_id, None)
            logger.info(f"Player {player_id[:8]} removed from all games")

            # Notify other players in lobby/game
            if game_id:
                disconnect_msg = NetworkMessage(
                    type=MessageType.PLAYER_LEFT,
                    timestamp=time.time(),
                    data={"player_id": player_id, "player_name": player_name}
                )

                if lobby and lobby.status == GameStatus.IN_PROGRESS:
                    # Was in active game
                    game_session = self.game_coordinator.get_game(game_id)
                    if game_session:
                        await self._broadcast_to_game(game_id, disconnect_msg)
                else:
                    # Was in lobby
                    await self._broadcast_to_lobby(game_id, disconnect_msg)

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

            # Chat
            elif message.type == MessageType.CHAT:
                await self._handle_chat(player_id, message)

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

        # Get player info from stored client type
        player_name = data.get("player_name", "Player")
        client_type = self.player_client_types.get(player_id, ClientType.HUMAN)

        # Create lobby with validation
        try:
            lobby = self.lobby_manager.create_lobby(
                player_id=player_id,
                player_name=player_name,
                game_name=game_name,
                client_type=client_type,
                max_players=max_players
            )
        except ValueError as e:
            logger.warning(f"Invalid game creation attempt by {player_id}: {e}")
            await self._send_error(player_id, f"Invalid game name: {e}")
            return

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
        # Use the client type stored during connection
        client_type = self.player_client_types.get(player_id, ClientType.HUMAN)

        # Join lobby with validation
        try:
            lobby = self.lobby_manager.join_lobby(game_id, player_id, player_name, client_type)
        except ValueError as e:
            logger.warning(f"Invalid join attempt by {player_id}: {e}")
            await self._send_error(player_id, f"Invalid player name: {e}")
            return

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
        """Handle START_GAME request with automatic AI player filling."""
        lobby = self.lobby_manager.get_player_lobby(player_id)

        if not lobby:
            await self._send_error(player_id, "Not in a lobby")
            return

        if player_id != lobby.host_player_id:
            await self._send_error(player_id, "Only host can start game")
            return

        # Check if we need to spawn AI players to fill empty slots
        ai_needed = lobby.get_ai_needed_count()

        if ai_needed > 0:
            logger.info(
                f"Spawning {ai_needed} AI player{'s' if ai_needed > 1 else ''} "
                f"for game {lobby.game_id[:8]}"
            )

            # Spawn AI clients
            spawned = await self.ai_spawner.spawn_ai_for_game(
                game_id=lobby.game_id,
                num_ai=ai_needed,
                host="localhost",  # AI clients connect to localhost
                port=self.port
            )

            if not spawned:
                logger.warning(
                    f"Failed to spawn AI players for game {lobby.game_id[:8]}, "
                    "continuing with current players"
                )
            else:
                # Wait for AI to join and ready up (with timeout)
                timeout = 10.0  # 10 seconds
                start_time = time.time()

                logger.info(f"Waiting for {len(spawned)} AI player(s) to join...")

                while time.time() - start_time < timeout:
                    # Refresh lobby to check player count and ready status
                    lobby = self.lobby_manager.get_lobby(lobby.game_id)

                    if not lobby:
                        logger.error("Lobby disappeared while waiting for AI")
                        await self._send_error(player_id, "Lobby error")
                        return

                    # Check if all players are ready
                    if lobby.all_players_ready():
                        logger.info(
                            f"All {len(lobby.players)} players ready "
                            f"(including {len(spawned)} AI)"
                        )
                        break

                    await asyncio.sleep(0.2)
                else:
                    # Timeout reached
                    logger.warning(
                        f"Timeout waiting for AI players to join game {lobby.game_id[:8]}"
                    )

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
        logger.info(f"Sending FULL_STATE to {len(lobby.players)} players")
        for net_player_id in lobby.players.keys():
            state_dict = game_session.get_game_state_for_player(net_player_id)
            logger.info(f"  -> Sending FULL_STATE to player {net_player_id}")

            state_msg = self.protocol.create_full_state_message(state_dict, net_player_id)
            await self._send_to_player(net_player_id, state_msg)
            logger.info(f"  -> FULL_STATE sent to player {net_player_id}")

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
        logger.info(f"Broadcasting game state to {len(game_session.network_to_game_id)} players in game {game_session.game_id}")
        logger.info(f"  Game state before broadcast - current_turn: {game_session.game_state.current_turn_player_id}, turn_phase: {game_session.game_state.turn_phase.name}, turn_number: {game_session.game_state.turn_number}")
        for net_player_id in game_session.network_to_game_id.keys():
            state_dict = game_session.get_game_state_for_player(net_player_id)
            if state_dict:
                logger.info(f"  State dict for {net_player_id[:8]}: turn_phase={state_dict.get('turn_phase')}")

            state_msg = self.protocol.create_full_state_message(state_dict, net_player_id)
            logger.info(f"  -> Sending FULL_STATE to player {net_player_id[:8]}...")
            await self._send_to_player(net_player_id, state_msg)
            logger.info(f"  -> FULL_STATE sent to player {net_player_id[:8]}")

    async def _send_full_state(self, player_id: str, lobby: GameLobby) -> None:
        """
        Send full game state to a single player.

        Args:
            player_id: Network player ID to send state to
            lobby: Game lobby with active game
        """
        game_session = self.game_coordinator.get_game(lobby.game_id)
        if not game_session:
            logger.warning(f"Cannot send state: Game {lobby.game_id} not found")
            return

        state_dict = game_session.get_game_state_for_player(player_id)
        state_msg = self.protocol.create_full_state_message(state_dict, player_id)
        await self._send_to_player(player_id, state_msg)

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

        # Cleanup AI processes for this game
        await self.ai_spawner.cleanup_ai_for_game(game_session.game_id)

        logger.info(f"Game {game_session.game_id} ended. Winner: {winner_name}")

    async def _handle_chat(self, player_id: str, message: NetworkMessage) -> None:
        """
        Handle chat message from a player.

        Args:
            player_id: Player sending the chat message
            message: CHAT message
        """
        data = message.data or {}
        chat_message = data.get("message", "")

        if not chat_message:
            return

        # Get player's name
        lobby = self.lobby_manager.get_lobby_by_player(player_id)
        player_name = "Unknown"

        if lobby and player_id in lobby.players:
            player_name = lobby.players[player_id].player_name

        logger.info(f"Chat from {player_name}: {chat_message}")

        # Create chat message to broadcast
        chat_msg = self.protocol.create_chat_message(
            player_id,
            player_name,
            chat_message
        )

        # Broadcast to all players in the game/lobby
        if lobby:
            await self._broadcast_to_lobby(lobby.game_id, chat_msg)

    async def _send_to_player(self, player_id: str, message: NetworkMessage) -> bool:
        """Send a message to a specific player."""
        connection = self.player_connections.get(player_id)
        if not connection:
            logger.warning(f"Cannot send {message.type.value} to {player_id[:8]}: No connection found")
            return False

        try:
            result = await connection.send_message(message)
            if not result:
                logger.warning(f"Failed to send {message.type.value} to {player_id[:8]}")
            return result
        except Exception as e:
            logger.error(f"Error sending {message.type.value} to {player_id[:8]}: {e}", exc_info=True)
            return False

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
