"""
TCP Connection wrapper for Race to the Crystal networking.

Provides async connection management with message framing.
"""
import asyncio
import logging
from typing import Optional, Callable, Awaitable

from network.protocol import NetworkMessage, MessageFraming


logger = logging.getLogger(__name__)


class Connection:
    """
    Wrapper around an asyncio TCP connection with message framing.

    Handles sending/receiving NetworkMessages over TCP with proper
    framing and async I/O.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        connection_id: str = "unknown"
    ):
        """
        Initialize connection.

        Args:
            reader: AsyncIO stream reader
            writer: AsyncIO stream writer
            connection_id: Identifier for logging
        """
        self.reader = reader
        self.writer = writer
        self.connection_id = connection_id
        self.buffer = b""  # Buffer for incomplete messages
        self.closed = False

        # Get remote address
        try:
            peername = writer.get_extra_info('peername')
            self.remote_address = f"{peername[0]}:{peername[1]}" if peername else "unknown"
        except Exception:
            self.remote_address = "unknown"

        logger.info(f"Connection created: {connection_id} from {self.remote_address}")

    async def send_message(self, message: NetworkMessage) -> bool:
        """
        Send a NetworkMessage over the connection.

        Args:
            message: NetworkMessage to send

        Returns:
            True if sent successfully, False if connection closed
        """
        if self.closed:
            logger.warning(f"Attempted to send on closed connection {self.connection_id}")
            return False

        try:
            # Serialize message to JSON
            json_str = message.to_json()

            # Frame the message
            framed_data = MessageFraming.frame_message(json_str)

            # Send over TCP
            self.writer.write(framed_data)
            await self.writer.drain()

            logger.debug(
                f"Sent {message.type.value} to {self.connection_id} "
                f"({len(framed_data)} bytes)"
            )
            return True

        except Exception as e:
            logger.error(f"Error sending message to {self.connection_id}: {e}")
            await self.close()
            return False

    async def receive_message(self) -> Optional[NetworkMessage]:
        """
        Receive the next NetworkMessage from the connection.

        Returns:
            NetworkMessage if received, None if connection closed or error

        Note: This method blocks until a complete message is received.
        """
        if self.closed:
            return None

        try:
            while True:
                # Try to parse a message from buffer
                message_bytes, self.buffer = MessageFraming.parse_frame(self.buffer)

                if message_bytes:
                    # We have a complete message
                    json_str = message_bytes.decode('utf-8')
                    message = NetworkMessage.from_json(json_str)

                    logger.debug(
                        f"Received {message.type.value} from {self.connection_id} "
                        f"({len(message_bytes)} bytes)"
                    )
                    return message

                # Need more data - read from network
                chunk = await self.reader.read(4096)

                if not chunk:
                    # Connection closed
                    logger.info(f"Connection closed by peer: {self.connection_id}")
                    await self.close()
                    return None

                self.buffer += chunk

        except Exception as e:
            logger.error(f"Error receiving message from {self.connection_id}: {e}")
            await self.close()
            return None

    async def start_message_loop(
        self,
        handler: Callable[[NetworkMessage], Awaitable[None]]
    ) -> None:
        """
        Start an async loop that receives messages and calls handler.

        Args:
            handler: Async function to call with each received message

        Note: This runs until the connection closes.
        """
        logger.info(f"Starting message loop for {self.connection_id}")

        try:
            while not self.closed:
                message = await self.receive_message()

                if message is None:
                    # Connection closed
                    break

                # Call handler
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(
                        f"Error in message handler for {self.connection_id}: {e}",
                        exc_info=True
                    )

        except Exception as e:
            logger.error(f"Message loop error for {self.connection_id}: {e}")
        finally:
            await self.close()

    async def close(self) -> None:
        """Close the connection gracefully."""
        if self.closed:
            return

        self.closed = True

        try:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info(f"Connection closed: {self.connection_id}")
        except Exception as e:
            logger.error(f"Error closing connection {self.connection_id}: {e}")

    def is_closed(self) -> bool:
        """Check if connection is closed."""
        return self.closed


class ConnectionPool:
    """
    Manages multiple active connections.

    Used by the server to track all connected clients.
    """

    def __init__(self):
        """Initialize empty connection pool."""
        self.connections: dict[str, Connection] = {}
        logger.info("Connection pool created")

    def add_connection(self, connection_id: str, connection: Connection) -> None:
        """
        Add a connection to the pool.

        Args:
            connection_id: Unique identifier for the connection
            connection: Connection object
        """
        self.connections[connection_id] = connection
        logger.info(f"Added connection to pool: {connection_id} (total: {len(self.connections)})")

    def remove_connection(self, connection_id: str) -> Optional[Connection]:
        """
        Remove a connection from the pool.

        Args:
            connection_id: Connection to remove

        Returns:
            Removed Connection object, or None if not found
        """
        connection = self.connections.pop(connection_id, None)
        if connection:
            logger.info(
                f"Removed connection from pool: {connection_id} "
                f"(remaining: {len(self.connections)})"
            )
        return connection

    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """
        Get a connection by ID.

        Args:
            connection_id: Connection to retrieve

        Returns:
            Connection object, or None if not found
        """
        return self.connections.get(connection_id)

    async def broadcast(
        self,
        message: NetworkMessage,
        exclude: Optional[set[str]] = None
    ) -> int:
        """
        Broadcast a message to all connections (optionally excluding some).

        Args:
            message: NetworkMessage to broadcast
            exclude: Set of connection IDs to exclude from broadcast

        Returns:
            Number of connections that received the message
        """
        exclude = exclude or set()
        sent_count = 0

        # Send to all connections not in exclude set
        for conn_id, conn in list(self.connections.items()):
            if conn_id not in exclude and not conn.is_closed():
                success = await conn.send_message(message)
                if success:
                    sent_count += 1

        logger.debug(
            f"Broadcasted {message.type.value} to {sent_count}/{len(self.connections)} connections"
        )
        return sent_count

    async def close_all(self) -> None:
        """Close all connections in the pool."""
        logger.info(f"Closing all connections in pool ({len(self.connections)} total)")

        for connection in list(self.connections.values()):
            await connection.close()

        self.connections.clear()

    def __len__(self) -> int:
        """Return number of active connections."""
        return len(self.connections)
