"""
3D renderer for Race to the Crystal.

This module handles all 3D rendering including board, tokens, and shaders.
"""

from typing import Dict, List, Optional, Tuple

from client.board_3d import Board3D
from client.token_3d import Token3D
from shared.constants import PLAYER_COLORS
from shared.logging_config import setup_logger

logger = setup_logger(__name__)


class Renderer3D:
    """
    Manages all 3D rendering for the game.

    The Renderer3D handles:
    - 3D board (wireframe grid, generators, crystal, mystery squares)
    - 3D token models (hexagonal prisms)
    - Shader management (OpenGL shader programs)
    - 3D rendering updates and drawing
    """

    def __init__(self):
        """Initialize 3D renderer."""
        # 3D rendering components
        self.board_3d: Optional[Board3D] = None
        self.tokens_3d: List[Token3D] = []
        self.shader_3d = None  # Shared OpenGL shader program

        # OpenGL context (set by GameView during initialization)
        self.ctx = None

    def create(
        self,
        game_state,
        ctx,
        mystery_animations: Dict[Tuple[int, int], float],
    ) -> bool:
        """
        Initialize 3D rendering components.

        Args:
            game_state: Game state object
            ctx: OpenGL context from Arcade window
            mystery_animations: Dict mapping positions to animation progress (0.0-1.0)

        Returns:
            True if 3D rendering was successfully initialized, False otherwise
        """
        try:
            # Store OpenGL context
            self.ctx = ctx

            # Clean up old 3D board if it exists
            if self.board_3d is not None:
                self.board_3d.cleanup()
                self.board_3d = None

            # Clean up old 3D tokens
            for token_3d in self.tokens_3d:
                token_3d.cleanup()
            self.tokens_3d.clear()

            # Get crystal position
            crystal = game_state.crystal
            crystal_pos = crystal.position if crystal else None

            # Create 3D board with generators, crystal position, and mystery animations
            self.board_3d = Board3D(
                game_state.board,
                ctx,
                generators=game_state.generators,
                crystal_pos=crystal_pos,
                mystery_animations=mystery_animations,
            )

            if self.board_3d.shader_program is None:
                logger.warning(
                    "3D shader compilation failed, 3D mode will not be available"
                )
                self.shader_3d = None
                return False
            else:
                self.shader_3d = self.board_3d.shader_program  # Reuse shader
                logger.info("3D rendering initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize 3D rendering: {e}")
            self.board_3d = None
            self.shader_3d = None
            return False

        # Create 3D tokens
        for player in game_state.players.values():
            player_color = PLAYER_COLORS[player.color.value]

            for token_id in player.token_ids:
                token = game_state.get_token(token_id)
                if token and token.is_alive and token.is_deployed:
                    try:
                        token_3d = Token3D(token, player_color, ctx)
                        self.tokens_3d.append(token_3d)
                    except Exception as e:
                        logger.error(f"Failed to create 3D token {token_id}: {e}")

        logger.debug(f"Created {len(self.tokens_3d)} 3D tokens")
        return True

    def add_token(self, token, player_color: Tuple[int, int, int], ctx) -> None:
        """
        Add a single 3D token (used when deploying new tokens).

        Args:
            token: Token object to render
            player_color: RGB color tuple
            ctx: OpenGL context from Arcade window
        """
        try:
            token_3d = Token3D(token, player_color, ctx)
            self.tokens_3d.append(token_3d)
            logger.debug(f"Added 3D token {token.id}")
        except Exception as e:
            logger.error(f"Failed to create 3D token {token.id}: {e}")

    def sync_tokens(self, game_state, ctx) -> None:
        """
        Synchronize 3D tokens with game state, animating changes.

        Args:
            game_state: New game state object
            ctx: OpenGL context
        """
        # Create a map of existing tokens by token ID
        existing_tokens = {t.token.id: t for t in self.tokens_3d}

        # Track processed IDs
        processed_ids = set()

        for player in game_state.players.values():
            player_color = PLAYER_COLORS[player.color.value]

            for token_id in player.token_ids:
                token = game_state.get_token(token_id)
                if not token or not token.is_alive or not token.is_deployed:
                    continue

                processed_ids.add(token_id)

                if token_id in existing_tokens:
                    # Update existing token
                    token_3d = existing_tokens[token_id]

                    # Update reference
                    token_3d.token = token

                    # Update position target (non-instant)
                    # Note: We check against render target, not current position, to avoid interrupting animation
                    current_grid_x = int(
                        token_3d.target_x // 32
                    )  # Using 32 as approximate CELL_SIZE if imported locally
                    current_grid_y = int(token_3d.target_y // 32)

                    # Just update target, Token3D handles interpolation
                    token_3d.update_position(
                        token.position[0], token.position[1], instant=False
                    )
                else:
                    # Create new token
                    try:
                        self.add_token(token, player_color, ctx)
                    except Exception as e:
                        logger.error(f"Failed to create new 3D token {token_id}: {e}")

        # Remove dead/undeployed tokens
        tokens_to_remove = []
        for token_3d in self.tokens_3d:
            if token_3d.token.id not in processed_ids:
                tokens_to_remove.append(token_3d)

        for token_3d in tokens_to_remove:
            token_3d.cleanup()
            self.tokens_3d.remove(token_3d)

    def update(self, delta_time: float) -> None:
        """
        Update 3D animations.

        Args:
            delta_time: Time since last update
        """
        for token_3d in self.tokens_3d:
            if hasattr(token_3d, "update"):
                token_3d.update(delta_time)

    def remove_token(self, token_id: int) -> None:
        """
        Remove a 3D token by ID (used when tokens are destroyed).

        Args:
            token_id: ID of token to remove
        """
        for token_3d in self.tokens_3d:
            if token_3d.token.id == token_id:
                token_3d.cleanup()
                self.tokens_3d.remove(token_3d)
                logger.debug(f"Removed 3D token {token_id}")
                break

    def update_mystery_animations(
        self, mystery_animations: Dict[Tuple[int, int], float]
    ) -> None:
        """
        Update mystery square animations.

        Args:
            mystery_animations: Dict mapping positions to animation progress (0.0-1.0)
        """
        if self.board_3d and len(mystery_animations) > 0:
            self.board_3d.update_mystery_animations(mystery_animations)

    def update_generator_lines(self) -> None:
        """Update generator connection lines (called after turn ends)."""
        if self.board_3d:
            self.board_3d.update_generator_lines()

    def draw(self, camera_3d) -> None:
        """
        Draw all 3D rendering elements.

        Args:
            camera_3d: 3D camera object for rendering
        """
        if self.board_3d and self.shader_3d:
            # Draw 3D board
            self.board_3d.draw(camera_3d)

            # Draw 3D tokens
            for token_3d in self.tokens_3d:
                if token_3d.token.is_alive:
                    token_3d.draw(camera_3d, self.shader_3d)

    def is_available(self) -> bool:
        """
        Check if 3D rendering is available.

        Returns:
            True if 3D board and shader are ready, False otherwise
        """
        return self.board_3d is not None and self.shader_3d is not None

    def cleanup(self) -> None:
        """Clean up 3D rendering resources."""
        if self.board_3d is not None:
            self.board_3d.cleanup()
            self.board_3d = None

        for token_3d in self.tokens_3d:
            token_3d.cleanup()
        self.tokens_3d.clear()

        self.shader_3d = None
        logger.debug("Cleaned up 3D renderer")
