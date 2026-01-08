"""
HTTP Handler for Race to the Crystal web server.

Serves static files (HTML, JS, CSS) for the web client.
Includes Vulcain Link headers for resource preloading.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from aiohttp import web


logger = logging.getLogger(__name__)


class HTTPHandler:
    """
    Handles HTTP requests for static file serving.

    Provides routes for:
    - / -> index.html
    - /static/* -> static files from web_server/static/
    """

    def __init__(self, static_dir: Optional[Path] = None):
        """
        Initialize HTTP handler.

        Args:
            static_dir: Directory containing static files
        """
        if static_dir is None:
            # Default to web_server/static relative to project root
            # server/http_handler.py -> server/ -> project_root/
            project_root = Path(__file__).parent.parent
            static_dir = project_root / "web_server" / "static"

        self.static_dir = Path(static_dir)
        self.templates_dir = self.static_dir.parent / "templates"

        # Mercure configuration for Link headers
        self.mercure_hub_url = os.getenv(
            "MERCURE_HUB_URL", "http://localhost:3000/.well-known/mercure"
        )
        # Public URL for browser (goes through Caddy reverse proxy)
        self.mercure_public_url = os.getenv(
            "MERCURE_PUBLIC_URL", "http://127.0.0.1:8880/.well-known/mercure"
        )
        self.mercure_topic_prefix = os.getenv(
            "MERCURE_TOPIC_PREFIX", "https://api.game.com/game"
        )

        logger.info(f"HTTP handler initialized with static dir: {self.static_dir}")

    def create_app(self) -> web.Application:
        """
        Create aiohttp application with routes.

        Returns:
            Configured web application
        """
        app = web.Application()

        app.router.add_get("/", self.handle_index)
        app.router.add_get("/index.html", self.handle_index)
        app.router.add_get("/game", self.handle_game)
        app.router.add_get("/game.html", self.handle_game)
        app.router.add_get("/api/config", self.handle_api_config)

        app.router.add_static("/static", self.static_dir, follow_symlinks=True)

        return app

    def _add_vulcain_headers(
        self, response: web.Response, game_id: str | None = None
    ) -> None:
        """
        Add Vulcain Link headers for resource preloading.

        Args:
            response: Response to add headers to
            game_id: Optional game ID for Mercure topic
        """
        link_headers = []

        # Preload critical JavaScript files
        link_headers.append('</static/babylon.js>; rel="preload"; as="script"')
        link_headers.append('</static/game_client.js>; rel="preload"; as="script"')
        link_headers.append('</static/mercure_client.js>; rel="preload"; as="script"')

        # Preload Mercure hub connection if game_id provided
        if game_id:
            mercure_topic = f"{self.mercure_topic_prefix}/{game_id}"
            link_headers.append(
                f'<{self.mercure_hub_url}?topic={mercure_topic}>; rel="mercure"'
            )

        # Set Link header (multiple values separated by commas)
        if link_headers:
            response.headers["Link"] = ", ".join(link_headers)
            logger.debug(f"Added Vulcain Link headers: {len(link_headers)} resources")

    async def handle_index(self, request: web.Request) -> web.FileResponse:
        """Serve the main index.html page."""
        index_file = self.templates_dir / "index.html"

        if index_file.exists():
            response = web.FileResponse(index_file)
            self._add_vulcain_headers(response)
            return response

        logger.error(f"index.html not found at {index_file}")
        response = web.Response(
            text="<html><body><h1>Race to the Crystal</h1>"
            "<p>Web server running. Open /game for the 3D client.</p>"
            "</body></html>",
            content_type="text/html",
        )
        self._add_vulcain_headers(response)
        return response

    async def handle_game(self, request: web.Request) -> web.FileResponse:
        """Serve the game page."""
        game_file = self.templates_dir / "index.html"

        # Extract game_id from query params if available
        game_id = request.query.get("game_id")

        if game_file.exists():
            response = web.FileResponse(game_file)
            self._add_vulcain_headers(response, game_id)
            return response

        logger.error(f"game.html not found at {game_file}")
        response = web.Response(
            text="<html><body><h1>Race to the Crystal - 3D Game</h1>"
            "<p>Game client loading...</p>"
            "</body></html>",
            content_type="text/html",
        )
        self._add_vulcain_headers(response, game_id)
        return response

    async def handle_api_config(self, request: web.Request) -> web.Response:
        """
        Serve Mercure configuration for web clients.

        Returns JSON with:
        - mercure_enabled: Whether Mercure is enabled
        - mercure_hub_url: Mercure hub URL for EventSource
        - mercure_topic: Topic to subscribe to (requires game_id param)
        """
        game_id = request.query.get("game_id", "")
        mercure_enabled = bool(os.getenv("MERCURE_PUBLISHER_JWT"))

        config = {
            "mercure_enabled": mercure_enabled,
            "mercure_hub_url": self.mercure_public_url,
            "mercure_topic": f"{self.mercure_topic_prefix}/{game_id}"
            if game_id
            else self.mercure_topic_prefix,
        }

        return web.json_response(config)

    @property
    def static_path(self) -> Path:
        """Get the static file directory path."""
        return self.static_dir

    @property
    def templates_path(self) -> Path:
        """Get the templates directory path."""
        return self.templates_dir


def create_app(static_dir: Optional[Path] = None) -> web.Application:
    """
    Create and configure aiohttp application.

    Args:
        static_dir: Directory containing static files

    Returns:
        Configured web application
    """
    handler = HTTPHandler(static_dir)
    return handler.create_app()
