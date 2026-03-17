"""
HTTP Handler for Race to the Crystal web server.

Serves static files (HTML, JS, CSS) for the web client and provides
REST API endpoints for HTTP AI clients.
"""

import logging
import os
import uuid
import jwt
from pathlib import Path
from typing import Optional

from aiohttp import web

from network.messages import MessageType, ClientType
from network.protocol import ProtocolHandler
from server.auth import (
    create_player_token,
    verify_player_token,
    extract_token_from_header,
    validate_token_for_game,
)
from server.lobby import validate_player_name
from shared.errors import (
    ValidationError,
    ServerError,
    ActionError,
    ErrorCode,
    format_error_response,
)


logger = logging.getLogger(__name__)


class HTTPHandler:
    """
    Handles HTTP requests for static file serving and REST API endpoints.

    Provides routes for:
    - / -> index.html
    - /static/* -> static files from web_server/static/
    - /api/game/{game_id}/join -> Join game via HTTP POST
    - /api/game/{game_id}/action -> Execute game action via HTTP POST
    """

    def __init__(
        self,
        static_dir: Optional[Path] = None,
        game_server=None,
        jwt_secret: Optional[str] = None,
    ):
        """
        Initialize HTTP handler.

        Args:
            static_dir: Directory containing static files
            game_server: Reference to main GameServer for API endpoints
            jwt_secret: Secret key for JWT token signing
        """
        if static_dir is None:
            # Default to web_server/static relative to project root
            # server/http_handler.py -> server/ -> project_root/
            project_root = Path(__file__).parent.parent
            static_dir = project_root / "web_server" / "static"

        self.static_dir = Path(static_dir)
        self.templates_dir = self.static_dir.parent / "templates"

        # Game server reference for API endpoints
        self.game_server = game_server

        # JWT authentication
        self.jwt_secret = jwt_secret or os.getenv(
            "JWT_SECRET_KEY", "dev-secret-key-CHANGE-IN-PRODUCTION"
        )
        if self.jwt_secret == "dev-secret-key-CHANGE-IN-PRODUCTION":
            logger.warning(
                "Using default JWT secret - CHANGE JWT_SECRET_KEY in production!"
            )

        # Protocol handler for action conversion
        self.protocol = ProtocolHandler()

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

    @web.middleware
    async def _no_cache_middleware(self, request, handler):
        """Add no-cache headers to JS/HTML responses to prevent stale code."""
        response = await handler(request)
        if request.path.endswith((".js", ".html")):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response

    def create_app(self) -> web.Application:
        """
        Create aiohttp application with routes.

        Returns:
            Configured web application
        """
        app = web.Application(middlewares=[self._no_cache_middleware])

        # Static files and web client
        app.router.add_get("/", self.handle_index)
        app.router.add_get("/index.html", self.handle_index)
        app.router.add_get("/game", self.handle_game)
        app.router.add_get("/game.html", self.handle_game)
        app.router.add_get("/api/config", self.handle_api_config)

        # REST API endpoints for HTTP AI clients
        app.router.add_post("/api/game/{game_id}/join", self.handle_join_game_http)
        app.router.add_post("/api/game/{game_id}/action", self.handle_action_http)

        app.router.add_static("/static", self.static_dir, follow_symlinks=True)

        return app

    async def handle_index(
        self, request: web.Request
    ) -> web.FileResponse | web.Response:
        """Serve the main index.html page."""
        index_file = self.templates_dir / "index.html"

        if index_file.exists():
            return web.FileResponse(index_file)

        logger.error(f"index.html not found at {index_file}")
        return web.Response(
            text="<html><body><h1>Race to the Crystal</h1>"
            "<p>Web server running. Open /game for the 3D client.</p>"
            "</body></html>",
            content_type="text/html",
        )

    async def handle_game(
        self, request: web.Request
    ) -> web.FileResponse | web.Response:
        """Serve the game page."""
        game_file = self.templates_dir / "index.html"

        if game_file.exists():
            return web.FileResponse(game_file)

        logger.error(f"game.html not found at {game_file}")
        return web.Response(
            text="<html><body><h1>Race to the Crystal - 3D Game</h1>"
            "<p>Game client loading...</p>"
            "</body></html>",
            content_type="text/html",
        )

    async def handle_api_config(self, request: web.Request) -> web.Response:
        """
        Serve Mercure configuration for web clients.

        Returns JSON with:
        - mercure_enabled: Whether Mercure is enabled
        - mercure_hub_url: Mercure hub URL for EventSource
        - mercure_topic: Topic to subscribe to (requires game_id param)
        - sse_primary_mode: Whether SSE-primary mode is enabled (state updates via SSE only)
        """
        game_id = request.query.get("game_id", "")
        mercure_enabled = bool(os.getenv("MERCURE_PUBLISHER_JWT"))
        sse_primary_mode = os.getenv("SSE_PRIMARY_MODE", "false").lower() == "true"

        config = {
            "mercure_enabled": mercure_enabled,
            "mercure_hub_url": self.mercure_public_url,
            "mercure_topic": f"{self.mercure_topic_prefix}/{game_id}"
            if game_id
            else self.mercure_topic_prefix,
            "sse_primary_mode": sse_primary_mode,
        }

        # Prevent browser caching to ensure clients always get current config
        return web.json_response(
            config,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    async def handle_join_game_http(self, request: web.Request) -> web.Response:
        """
        Handle HTTP POST /api/game/{game_id}/join.

        Allows HTTP AI clients to join an existing game. Automatically marks
        the player as ready (HTTP clients don't need manual ready).

        Request body:
            {"player_name": "AI_Bot"}

        Returns:
            200: {"player_id": "...", "token": "...", "sse_url": "..."}
            400: Invalid player_name
            404: Game not found
            410: Game already started
            500: Server error
        """
        if not self.game_server:
            error = ServerError(
                ErrorCode.SERVER_NOT_INITIALIZED, "Server not initialized"
            )
            return web.json_response(format_error_response(error, 500), status=500)

        game_id = request.match_info["game_id"]

        try:
            data = await request.json()
            player_name = data.get("player_name")

            if not player_name:
                error = ValidationError("player_name", ErrorCode.MISSING_FIELD)
                return web.json_response(format_error_response(error, 400), status=400)

            # Validate player name
            try:
                validate_player_name(player_name)
            except ValueError as e:
                error = ValidationError(
                    "player_name", ErrorCode.INVALID_VALUE, {"details": str(e)}
                )
                return web.json_response(format_error_response(error, 400), status=400)

            # Check if game exists
            lobby = self.game_server.lobby_manager.get_lobby(game_id)
            if not lobby:
                error = ServerError(
                    ErrorCode.GAME_NOT_FOUND, "Game not found", {"game_id": game_id}
                )
                return web.json_response(format_error_response(error, 404), status=404)

            # Check if game already started
            from server.lobby import GameStatus

            if lobby.status != GameStatus.WAITING:
                error = ServerError(
                    ErrorCode.GAME_ALREADY_STARTED, "Game already started or finished"
                )
                return web.json_response(format_error_response(error, 410), status=410)

            # Generate player ID
            player_id = str(uuid.uuid7())

            # Join lobby
            updated_lobby = self.game_server.lobby_manager.join_lobby(
                game_id=game_id,
                player_id=player_id,
                player_name=player_name,
                client_type=ClientType.HTTP_AI,
            )

            if not updated_lobby:
                error = ServerError(
                    ErrorCode.LOBBY_FULL, "Failed to join game (may be full)"
                )
                return web.json_response(format_error_response(error, 400), status=400)

            # Automatically mark as ready (HTTP clients auto-ready)
            self.game_server.lobby_manager.set_ready(game_id, player_id, True)

            # Register client type in game server
            self.game_server.player_client_types[player_id] = ClientType.HTTP_AI

            # Generate JWT token
            token = create_player_token(player_id, game_id, self.jwt_secret)

            # Build SSE URL
            sse_url = (
                f"{self.mercure_public_url}?topic={self.mercure_topic_prefix}/{game_id}"
            )

            logger.info(
                f"HTTP AI client joined game {game_id[:8]}: "
                f"{player_name} ({player_id[:8]}) - auto-ready"
            )

            return web.json_response(
                {
                    "player_id": player_id,
                    "token": token,
                    "sse_url": sse_url,
                    "game_id": game_id,
                    "player_name": player_name,
                }
            )

        except ValueError as e:
            logger.error(f"Validation error in HTTP join: {e}")
            error = ValidationError(
                "request", ErrorCode.INVALID_VALUE, {"details": str(e)}
            )
            return web.json_response(format_error_response(error, 400), status=400)
        except KeyError as e:
            logger.error(f"Missing field in HTTP join: {e}")
            error = ValidationError(
                "request", ErrorCode.MISSING_FIELD, {"field": str(e)}
            )
            return web.json_response(format_error_response(error, 400), status=400)
        except jwt.InvalidTokenError as e:
            if "exp" in str(e).lower():
                logger.warning(f"Token expired: {e}")
                error = ServerError(ErrorCode.TOKEN_EXPIRED, "Token expired")
                return web.json_response(format_error_response(error, 401), status=401)
            logger.warning(f"Invalid JWT token: {e}")
            error = ServerError(ErrorCode.TOKEN_INVALID, "Invalid token")
            return web.json_response(format_error_response(error, 401), status=401)
        except Exception as e:
            logger.error(f"Unexpected error in HTTP join: {e}", exc_info=True)
            error = ServerError(
                ErrorCode.INTERNAL_ERROR, "Internal server error", {"details": str(e)}
            )
            return web.json_response(format_error_response(error, 500), status=500)

    async def handle_action_http(self, request: web.Request) -> web.Response:
        """
        Handle HTTP POST /api/game/{game_id}/action.

        Executes a game action (MOVE, ATTACK, DEPLOY, END_TURN) from an
        HTTP AI client. Requires JWT authentication.

        Headers:
            Authorization: Bearer {token}

        Request body:
            {
                "type": "MOVE",
                "token_id": 5,
                "destination": [12, 12]
            }

        Returns:
            200: {"success": true, "message": "...", "data": {...}}
            400: Invalid request data
            401: Missing/invalid JWT token
            403: Token not valid for this game
            404: Game not found
            422: Action validation failed
            500: Server error
        """
        if not self.game_server:
            error = ServerError(
                ErrorCode.SERVER_NOT_INITIALIZED, "Server not initialized"
            )
            return web.json_response(format_error_response(error, 500), status=500)

        game_id = request.match_info["game_id"]

        # Extract and verify JWT token
        auth_header = request.headers.get("Authorization", "")
        token = extract_token_from_header(auth_header)

        if not token:
            error = ServerError(
                ErrorCode.UNAUTHORIZED, "Missing or invalid Authorization header"
            )
            return web.json_response(format_error_response(error, 401), status=401)

        try:
            payload = verify_player_token(token, self.jwt_secret)
        except jwt.ExpiredSignatureError:
            error = ServerError(ErrorCode.TOKEN_EXPIRED, "Token expired")
            return web.json_response(format_error_response(error, 401), status=401)
        except jwt.InvalidTokenError:
            error = ServerError(ErrorCode.TOKEN_INVALID, "Invalid token")
            return web.json_response(format_error_response(error, 401), status=401)

        if not payload:
            error = ServerError(ErrorCode.TOKEN_INVALID, "Invalid token payload")
            return web.json_response(format_error_response(error, 401), status=401)

        # Validate token is for this game
        if not validate_token_for_game(payload, game_id):
            error = ServerError(
                ErrorCode.FORBIDDEN,
                "Token not valid for this game",
                {"game_id": game_id},
            )
            return web.json_response(format_error_response(error, 403), status=403)

        player_id = payload.player_id

        try:
            # Parse action data
            action_data = await request.json()
            action_type = action_data.get("type", "").strip()

            if not action_type:
                error = ValidationError("type", ErrorCode.MISSING_FIELD)
                return web.json_response(format_error_response(error, 400), status=400)

            # Validate action data based on type
            if action_type in ["MOVE", "move"]:
                token_id = action_data.get("token_id")
                destination = action_data.get("destination")
                if token_id is None:
                    error = ValidationError(
                        "token_id", ErrorCode.MISSING_FIELD, {"action": "MOVE"}
                    )
                    return web.json_response(
                        format_error_response(error, 400), status=400
                    )
                if (
                    not destination
                    or not isinstance(destination, list)
                    or len(destination) != 2
                ):
                    error = ValidationError(
                        "destination",
                        ErrorCode.INVALID_VALUE,
                        {"expected": "[x, y] coordinates"},
                    )
                    return web.json_response(
                        format_error_response(error, 400), status=400
                    )
            elif action_type in ["ATTACK", "attack"]:
                attacker_id = action_data.get("attacker_id")
                defender_id = action_data.get("defender_id") or action_data.get(
                    "target_id"
                )
                if attacker_id is None:
                    error = ValidationError(
                        "attacker_id", ErrorCode.MISSING_FIELD, {"action": "ATTACK"}
                    )
                    return web.json_response(
                        format_error_response(error, 400), status=400
                    )
                if defender_id is None:
                    error = ValidationError(
                        "defender_id",
                        ErrorCode.MISSING_FIELD,
                        {"action": "ATTACK", "alternative": "target_id"},
                    )
                    return web.json_response(
                        format_error_response(error, 400), status=400
                    )
            elif action_type in ["DEPLOY", "deploy"]:
                health_value = action_data.get("health_value")
                position = action_data.get("position")
                if health_value is None:
                    error = ValidationError(
                        "health_value", ErrorCode.MISSING_FIELD, {"action": "DEPLOY"}
                    )
                    return web.json_response(
                        format_error_response(error, 400), status=400
                    )
                if not position or not isinstance(position, list) or len(position) != 2:
                    error = ValidationError(
                        "position",
                        ErrorCode.INVALID_VALUE,
                        {"expected": "[x, y] coordinates"},
                    )
                    return web.json_response(
                        format_error_response(error, 400), status=400
                    )
            elif action_type not in ["END_TURN", "end_turn"]:
                error = ValidationError(
                    "type",
                    ErrorCode.INVALID_VALUE,
                    {
                        "value": action_type,
                        "allowed": ["MOVE", "ATTACK", "DEPLOY", "END_TURN"],
                    },
                )
                return web.json_response(format_error_response(error, 400), status=400)

            # Convert action type to MessageType enum
            try:
                msg_type = MessageType(action_type)
            except ValueError:
                error = ValidationError(
                    "type", ErrorCode.INVALID_VALUE, {"value": action_type}
                )
                return web.json_response(format_error_response(error, 400), status=400)

            # Create network message for action conversion
            from network.protocol import NetworkMessage
            import time

            message = NetworkMessage(
                type=msg_type,
                timestamp=time.time(),
                player_id=player_id,
                data=action_data,
            )

            # Convert message to AIAction
            try:
                action = self.protocol.message_to_action(message)
            except (KeyError, ValueError) as e:
                error = ValidationError(
                    "action_data", ErrorCode.INVALID_VALUE, {"details": str(e)}
                )
                return web.json_response(format_error_response(error, 400), status=400)

            # Execute action via game coordinator
            success, message_text, result_data, game_session = (
                self.game_server.game_coordinator.execute_action(player_id, action)
            )

            if not success:
                error = ActionError(
                    action_type.upper(), "validation_failed", {"message": message_text}
                )
                return web.json_response(
                    {
                        "success": False,
                        **format_error_response(error, 422),
                        "action_type": action_type,
                    },
                    status=422,  # Unprocessable Entity (valid request, invalid action)
                )

            # Broadcast state update (happens via existing flow)
            if game_session:
                await self.game_server._broadcast_game_state(game_session)

                # Check for game over
                if game_session.is_game_over():
                    await self.game_server._handle_game_over(game_session)

            logger.info(
                f"HTTP action executed: {action_type} by {player_id[:8]} "
                f"in game {game_id[:8]}"
            )

            return web.json_response(
                {
                    "success": True,
                    "message": message_text,
                    "data": result_data,
                }
            )

        except ValueError as e:
            logger.error(f"Validation error in HTTP action: {e}")
            error = ValidationError(
                "request", ErrorCode.INVALID_VALUE, {"details": str(e)}
            )
            return web.json_response(format_error_response(error, 400), status=400)
        except KeyError as e:
            logger.error(f"Missing field in HTTP action: {e}")
            error = ValidationError(
                "request", ErrorCode.MISSING_FIELD, {"field": str(e)}
            )
            return web.json_response(format_error_response(error, 400), status=400)
        except jwt.InvalidTokenError as e:
            if "exp" in str(e).lower():
                logger.warning(f"Token expired: {e}")
                error = ServerError(ErrorCode.TOKEN_EXPIRED, "Token expired")
                return web.json_response(format_error_response(error, 401), status=401)
            logger.warning(f"Invalid JWT token: {e}")
            error = ServerError(ErrorCode.TOKEN_INVALID, "Invalid token")
            return web.json_response(format_error_response(error, 401), status=401)
        except Exception as e:
            logger.error(f"Unexpected error in HTTP action: {e}", exc_info=True)
            return web.json_response({"error": "Internal server error"}, status=500)

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
