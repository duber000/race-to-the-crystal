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

    def __init__(
        self, host: str, port: int, unified: bool = False, http_port: int = 8081
    ):
        """
        Initialize server runner.

        Args:
            host: Host address to bind to
            port: Port to listen on
            unified: Whether to run unified server (TCP + HTTP/WebSocket)
            http_port: HTTP/WebSocket port for unified server
        """
        self.server = GameServer(host, port)
        self.shutdown_event = asyncio.Event()
        self.unified = unified
        self.http_port = http_port

    async def run(self) -> None:
        """Run the server with graceful shutdown handling."""
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        logger.info("Starting Race to the Crystal server...")

        # Create server start task
        if self.unified:
            server_task = asyncio.create_task(
                self.server.start_unified_server(self.server.port, self.http_port)
            )
        else:
            server_task = asyncio.create_task(self.server.start())

        try:
            # Wait for either server to complete or shutdown signal
            done, pending = await asyncio.wait(
                [server_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # If shutdown was triggered, cancel the server task
            if self.shutdown_event.is_set():
                logger.info("Shutdown triggered, stopping server...")
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass

        except asyncio.CancelledError:
            logger.info("Server task cancelled")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            await self.server.stop()
            if self.unified:
                await self.server.stop_aiohttp_server()

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
        help="Host address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port to listen on for TCP game server (default: 8888)",
    )
    parser.add_argument(
        "--unified",
        action="store_true",
        help="Run unified server with both TCP and HTTP/WebSocket (web client support)",
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=8081,
        help="HTTP/WebSocket port for unified server (default: 8081)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create and run server
    runner = ServerRunner(args.host, args.port, args.unified, args.http_port)

    if args.unified:
        logger.info("Running in UNIFIED mode (TCP + HTTP/WebSocket)")
        logger.info(f"  TCP port: {args.port}")
        logger.info(f"  HTTP/WebSocket port: {args.http_port}")
        logger.info(
            "  Access web client at: http://localhost:{}/".format(args.http_port)
        )
        logger.info("  WebSocket endpoint: ws://localhost:{}/ws".format(args.http_port))

    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


def main_unified():
    """Entry point for unified server (defaults to --unified flag)."""
    import sys

    # Insert --unified flag if not already present
    if "--unified" not in sys.argv:
        sys.argv.insert(1, "--unified")

    main()


if __name__ == "__main__":
    main()
