"""
Network client for Race to the Crystal.

Handles connection to game server and message exchange.
"""
import asyncio
import logging
from typing import Optional, Callable, Awaitable, Dict

from network.connection import Connection
from network.protocol import ProtocolHandler, NetworkMessage
from network.messages import MessageType, ClientType
from game.ai_actions import AIAction


logger = logging.getLogger(__name__)


class NetworkClient:
    """
    Network client for connecting to Race to the Crystal server.

    Can be used by both human players (with GUI) and AI players.
    """

    def __init__(self, player_name: str, client_type: ClientType = ClientType.HUMAN):
        """
        Initialize network client.

        Args:
            player_name: Display name for this player
            client_type: HUMAN or AI
        """
        self.player_name = player_name
        self.client_type = client_type

        # Connection state
        self.connection: Optional[Connection] = None
        self.player_id: Optional[str] = None
        self.connected = False

        # Protocol handler
        self.protocol = ProtocolHandler()

        # Message handlers (can be set by user)
        self.on_message: Optional[Callable[[NetworkMessage], Awaitable[None]]] = None
        self.on_disconnect: Optional[Callable[[], Awaitable[None]]] = None

        # Current game state
        self.game_id: Optional[str] = None
        self.current_game_state: Optional[Dict] = None

        logger.info(f"Network client created: {player_name} ({client_type.value})")

    async def connect(self, host: str, port: int) -> bool:
        """
        Connect to the game server.

        Args:
            host: Server hostname or IP
            port: Server port

        Returns:
            True if connected successfully
        """
        try:
            logger.info(f"Connecting to {host}:{port}...")

            # Open TCP connection
            reader, writer = await asyncio.open_connection(host, port)

            # Create connection wrapper
            self.connection = Connection(reader, writer, f"client-{self.player_name}")

            # Send CONNECT message
            connect_msg = self.protocol.create_connect_message(
                self.player_name,
                self.client_type
            )
            await self.connection.send_message(connect_msg)

            # Wait for CONNECT_ACK
            ack_msg = await asyncio.wait_for(
                self.connection.receive_message(),
                timeout=5.0
            )

            if not ack_msg or ack_msg.type != MessageType.CONNECT_ACK:
                logger.error("Invalid CONNECT_ACK received")
                await self.disconnect()
                return False

            # Extract player_id from ACK
            self.player_id = ack_msg.player_id
            self.connected = True

            logger.info(
                f"Connected successfully as {self.player_name} "
                f"(ID: {self.player_id[:8]})"
            )

            # Start message receive loop
            asyncio.create_task(self._message_loop())

            return True

        except asyncio.TimeoutError:
            logger.error("Connection timeout")
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            return False

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if not self.connected:
            return

        logger.info("Disconnecting from server...")

        # Send DISCONNECT message
        if self.connection and self.player_id:
            disconnect_msg = self.protocol.create_disconnect_message(self.player_id)
            await self.connection.send_message(disconnect_msg)

        # Close connection
        if self.connection:
            await self.connection.close()

        self.connected = False
        self.player_id = None

        # Call disconnect callback
        if self.on_disconnect:
            await self.on_disconnect()

        logger.info("Disconnected")

    async def _message_loop(self) -> None:
        """Internal loop for receiving messages from server."""
        try:
            while self.connected and self.connection:
                message = await self.connection.receive_message()

                if message is None:
                    # Connection closed
                    logger.info("Server closed connection")
                    break

                # Handle message
                await self._handle_message(message)

        except Exception as e:
            logger.error(f"Message loop error: {e}", exc_info=True)
        finally:
            await self.disconnect()

    async def _handle_message(self, message: NetworkMessage) -> None:
        """
        Handle a received message from server.

        Args:
            message: Received message
        """
        logger.debug(f"Received {message.type.value}")

        # Update internal state based on message type
        if message.type == MessageType.FULL_STATE:
            # Full game state received
            data = message.data or {}
            self.current_game_state = data.get("game_state")

        elif message.type == MessageType.ERROR:
            data = message.data or {}
            error_msg = data.get("error", "Unknown error")
            logger.error(f"Server error: {error_msg}")

        # Call user-provided message handler
        if self.on_message:
            await self.on_message(message)

    # --- LOBBY OPERATIONS ---

    async def create_game(self, game_name: str, max_players: int = 4) -> bool:
        """
        Create a new game lobby.

        Args:
            game_name: Name for the game
            max_players: Maximum number of players (2-4)

        Returns:
            True if game created successfully
        """
        if not self.connected:
            logger.error("Not connected to server")
            return False

        msg = self.protocol.create_game_message(
            self.player_id,
            game_name,
            max_players
        )

        return await self.connection.send_message(msg)

    async def join_game(self, game_id: str) -> bool:
        """
        Join an existing game lobby.

        Args:
            game_id: ID of game to join

        Returns:
            True if join request sent successfully
        """
        if not self.connected:
            logger.error("Not connected to server")
            return False

        msg = self.protocol.join_game_message(self.player_id, game_id)
        success = await self.connection.send_message(msg)

        if success:
            self.game_id = game_id

        return success

    async def leave_game(self) -> bool:
        """
        Leave current game lobby.

        Returns:
            True if leave request sent successfully
        """
        if not self.connected or not self.game_id:
            return False

        msg = NetworkMessage(
            type=MessageType.LEAVE_GAME,
            timestamp=asyncio.get_event_loop().time(),
            player_id=self.player_id,
            data={"game_id": self.game_id}
        )

        success = await self.connection.send_message(msg)

        if success:
            self.game_id = None

        return success

    async def set_ready(self, is_ready: bool = True) -> bool:
        """
        Set ready status in lobby.

        Args:
            is_ready: Ready status

        Returns:
            True if request sent successfully
        """
        if not self.connected:
            return False

        msg = self.protocol.ready_message(self.player_id, is_ready)
        return await self.connection.send_message(msg)

    async def list_games(self) -> bool:
        """
        Request list of available games.

        Returns:
            True if request sent successfully
        """
        if not self.connected:
            return False

        msg = self.protocol.list_games_message(self.player_id)
        return await self.connection.send_message(msg)

    # --- GAME ACTIONS ---

    async def send_action(self, action: AIAction) -> bool:
        """
        Send a game action to the server.

        Args:
            action: AIAction to execute

        Returns:
            True if action sent successfully
        """
        if not self.connected:
            logger.error("Not connected to server")
            return False

        # Convert action to network message
        msg = self.protocol.action_to_message(action, self.player_id)

        return await self.connection.send_message(msg)

    # --- UTILITY METHODS ---

    def get_current_game_state(self) -> Optional[Dict]:
        """
        Get the most recent game state.

        Returns:
            Game state dictionary, or None if not available
        """
        return self.current_game_state

    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self.connected

    def get_player_id(self) -> Optional[str]:
        """Get assigned player ID."""
        return self.player_id
