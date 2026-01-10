"""
FastAPI web server for Race to the Crystal.

Provides REST API and WebSocket endpoints for game state management
and serves the Babylon.js 3D frontend with Mercure real-time updates.
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from game.game_state import GameState
from game.ai_actions import (
    AIActionExecutor,
    MoveAction,
    AttackAction,
    DeployAction,
    EndTurnAction,
)
from shared.enums import PlayerColor, GamePhase
from shared.logging_config import setup_logger
from web_server.mercure_publisher import MercureConfig, MercurePublisher

logger = setup_logger(__name__)


class GameManager:
    """Manages game state, WebSocket connections, and Mercure publishing."""

    def __init__(self):
        self.game_state: GameState | None = None
        self.websocket_clients: list[WebSocket] = []
        self.action_executor = AIActionExecutor()

        # Initialize Mercure publisher
        mercure_config = MercureConfig.from_env()
        self.mercure = MercurePublisher(mercure_config)
        self.game_id = "default_game"  # For single-game mode

    def create_new_game(self, num_players: int = 2) -> GameState:
        """Create a new game with specified number of players."""
        from game.generator import Generator
        from game.crystal import Crystal

        self.game_state = GameState()
        num_players = max(2, min(4, num_players))

        # Add players
        colors = [
            PlayerColor.CYAN,
            PlayerColor.MAGENTA,
            PlayerColor.YELLOW,
            PlayerColor.GREEN,
        ]
        for i in range(num_players):
            player_id = f"player_{i}"
            self.game_state.add_player(player_id, f"Player {i + 1}", colors[i])

        # Start the game (creates tokens and auto-deploys starting tokens)
        self.game_state.start_game()

        # Initialize generators
        generator_positions = self.game_state.board.get_generator_positions()
        for i, pos in enumerate(generator_positions):
            generator = Generator(id=i, position=pos)
            self.game_state.generators.append(generator)

        # Initialize crystal
        crystal_pos = self.game_state.board.get_crystal_position()
        self.game_state.crystal = Crystal(position=crystal_pos)

        # Set game to playing
        self.game_state.phase = GamePhase.PLAYING
        self.game_state.current_turn_player_id = "player_0"

        logger.info(f"Created new game with {num_players} players")
        return self.game_state

    async def broadcast_state(self, action_type: str | None = None):
        """
        Broadcast game state to all connected clients via WebSocket and Mercure.

        Args:
            action_type: Optional action type that triggered this update
        """
        if not self.game_state:
            return

        state_dict = self.game_state.to_dict()
        state_json = self.game_state.to_json()

        # Broadcast via WebSocket (fallback for non-Mercure clients)
        disconnected = []
        for client in self.websocket_clients:
            try:
                await client.send_text(state_json)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(client)

        # Remove disconnected clients
        for client in disconnected:
            self.websocket_clients.remove(client)

        # Publish via Mercure for real-time updates
        if self.mercure.enabled:
            update_data = {"state": state_dict, "type": "state_update"}
            if action_type:
                update_data["last_action"] = action_type

            await self.mercure.publish_game_state(self.game_id, update_data)

    def execute_action(
        self, action_data: dict[str, Any]
    ) -> tuple[bool, str, dict | None]:
        """Execute a game action and return result."""
        if not self.game_state:
            return False, "No active game", None

        action_type = action_data.get("type")
        player_id = action_data.get("player_id")

        # Create action based on type
        action = None
        if action_type == "move":
            action = MoveAction(
                token_id=action_data["token_id"],
                destination=tuple(action_data["destination"]),
            )
        elif action_type == "attack":
            action = AttackAction(
                attacker_id=action_data["attacker_id"],
                target_id=action_data["target_id"],
            )
        elif action_type == "deploy":
            action = DeployAction(
                token_id=action_data["token_id"],
                position=tuple(action_data["position"]),
            )
        elif action_type == "end_turn":
            action = EndTurnAction()
        else:
            return False, f"Unknown action type: {action_type}", None

        # Execute action
        result = self.action_executor.execute_action(action, self.game_state, player_id)
        return result.success, result.message, result.data


# Global game manager instance
game_manager = GameManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI application."""
    # Startup: Create initial game
    game_manager.create_new_game(num_players=2)
    logger.info("FastAPI server started")
    yield
    # Shutdown
    await game_manager.mercure.close()
    logger.info("FastAPI server shutting down")


# Create FastAPI app
app = FastAPI(
    title="Race to the Crystal Web API",
    description="REST API and WebSocket server for Race to the Crystal game",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main game page."""
    html_file = Path(__file__).parent / "templates" / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse(
        content="<h1>Race to the Crystal</h1><p>3D view coming soon!</p>"
    )


@app.get("/api/config")
async def get_config():
    """Get client configuration including Mercure hub URL."""
    return {
        "mercure_hub_url": game_manager.mercure.config.hub_url,
        "mercure_topic": f"{game_manager.mercure.config.topic_prefix}/{game_manager.game_id}",
        "mercure_enabled": game_manager.mercure.enabled,
        "api_version": "1.0.0",
        "features": ["mercure", "websocket_fallback", "babylon3d"],
    }


@app.get("/api/game/state")
async def get_game_state():
    """Get current game state as JSON."""
    if not game_manager.game_state:
        raise HTTPException(status_code=404, detail="No active game")
    return game_manager.game_state.to_dict()


@app.post("/api/game/new")
async def create_new_game(num_players: int = 2):
    """Create a new game."""
    if num_players < 2 or num_players > 4:
        raise HTTPException(
            status_code=400, detail="Number of players must be between 2 and 4"
        )

    game_state = game_manager.create_new_game(num_players)
    await game_manager.broadcast_state()
    return {"message": "Game created", "state": game_state.to_dict()}


@app.post("/api/game/action")
async def execute_action(action: dict[str, Any]):
    """Execute a game action and broadcast via Mercure."""
    success, message, data = game_manager.execute_action(action)

    if success:
        # Broadcast updated state to all clients with action type
        action_type = action.get("type", "unknown")
        await game_manager.broadcast_state(action_type=action_type)

    return {"success": success, "message": message, "data": data}


@app.post("/api/game/apply-effect")
async def apply_crystal_effect(
    player_id: str, effect_type: str, duration: int | None = None
):
    """
    Apply a crystal effect to a player (for testing).

    Args:
        player_id: Player to affect (e.g., 'player_0')
        effect_type: Effect type ('fog_of_war' or 'phantom_enemies')
        duration: Optional duration in turns (defaults to 4)
    """
    if not game_manager.game_state:
        raise HTTPException(status_code=404, detail="No active game")

    from shared.enums import CrystalEffect

    # Parse effect type
    effect_map = {
        "fog_of_war": CrystalEffect.FOG_OF_WAR,
        "phantom_enemies": CrystalEffect.PHANTOM_ENEMIES,
    }

    effect = effect_map.get(effect_type.lower())
    if not effect:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid effect type. Must be one of: {list(effect_map.keys())}",
        )

    # Validate player exists
    if player_id not in game_manager.game_state.players:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

    # Apply effect
    game_manager.game_state.apply_crystal_effect(player_id, effect, duration)

    # Broadcast updated state
    await game_manager.broadcast_state(action_type="crystal_effect_applied")

    return {
        "success": True,
        "message": f"Applied {effect_type} to {player_id}",
        "duration": duration or 4,
    }


@app.websocket("/ws/game")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time game state updates."""
    await websocket.accept()
    game_manager.websocket_clients.append(websocket)
    logger.info("WebSocket client connected")

    try:
        # Send initial game state
        if game_manager.game_state:
            await websocket.send_text(game_manager.game_state.to_json())

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message: {data}")

            # Handle action requests via WebSocket
            try:
                action_data = json.loads(data)
                success, message, result_data = game_manager.execute_action(action_data)

                # Send response
                await websocket.send_json(
                    {
                        "type": "action_result",
                        "success": success,
                        "message": message,
                        "data": result_data,
                    }
                )

                if success:
                    # Broadcast updated state with action type
                    action_type = action_data.get("type", "unknown")
                    await game_manager.broadcast_state(action_type=action_type)

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        game_manager.websocket_clients.remove(websocket)


def run_server():
    """Run the FastAPI server with uvicorn."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    run_server()
