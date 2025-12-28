"""
Server entry point for Race to the Crystal.

Starts the TCP game server and handles shutdown gracefully.
"""
import asyncio
import argparse
import logging
import signal

from server.game_server import GameServer


logger = logging.getLogger(__name__)


class ServerRunner:
    """Handles server startup and graceful shutdown."""

    def __init__(self, host: str, port: int):
        """
        Initialize server runner.

        Args:
            host: Host address to bind to
            port: Port to listen on
        """
        self.server = GameServer(host, port)
        self.shutdown_event = asyncio.Event()

    async def run(self) -> None:
        """Run the server with graceful shutdown handling."""
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.shutdown())
            )

        logger.info("Starting Race to the Crystal server...")

        try:
            # Start server (runs until shutdown)
            await self.server.start()

        except asyncio.CancelledError:
            logger.info("Server task cancelled")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            await self.server.stop()

    async def shutdown(self) -> None:
        """Trigger graceful shutdown."""
        logger.info("Shutdown signal received")
        self.shutdown_event.set()


def main():
    """Main entry point for the server."""
    parser = argparse.ArgumentParser(
        description="Race to the Crystal - Multiplayer Game Server"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port to listen on (default: 8888)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and run server
    runner = ServerRunner(args.host, args.port)

    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()
