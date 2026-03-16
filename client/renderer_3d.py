"""
3D renderer for Race to the Crystal.

This module handles all 3D rendering including board, tokens, and shaders.
"""

from client.board_3d import Board3D
from client.token_3d import Token3D
from client.phantom_token_3d import PhantomToken3D
from game.ai_observation import AIObserver
from shared.enums import TurnPhase, CrystalEffect
from shared.constants import (
    PLAYER_COLORS,
    CELL_SIZE,
    WALL_HEIGHT,
    TOKEN_HEIGHT_3D,
)
from shared.logging_config import setup_logger
from shared.types import TokenID

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
        self.board_3d: Board3D | None = None
        self.tokens_3d: list[Token3D] = []
        self.phantom_tokens_3d: list[PhantomToken3D] = []
        self.shader_3d = None  # Shared OpenGL shader program

        # OpenGL context (set by GameView during initialization)
        self.ctx = None

        # Selection state for highlighting selected token
        self.selected_token_id: TokenID | None = None

    def create(
        self,
        game_state,
        ctx,
        mystery_animations: dict[tuple[int, int], float],
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

            # Get crystal position (fallback for network games that omit it)
            crystal = game_state.crystal
            if crystal:
                crystal_pos = crystal.position
            elif hasattr(game_state.board, "get_crystal_position"):
                crystal_pos = game_state.board.get_crystal_position()
            else:
                crystal_pos = None

            # Get generator list (fallback to board positions when missing)
            generators = game_state.generators
            if (not generators) and hasattr(
                game_state.board, "get_generator_positions"
            ):
                from types import SimpleNamespace

                generators = [
                    SimpleNamespace(position=pos, is_disabled=False)
                    for pos in game_state.board.get_generator_positions()
                ]

            # Create 3D board with generators, crystal position, and mystery animations
            self.board_3d = Board3D(
                game_state.board,
                ctx,
                generators=generators,
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

        except RuntimeError as e:
            logger.error(f"OpenGL context error initializing 3D: {e}")
            self.board_3d = None
            self.shader_3d = None
            return False
        except ValueError as e:
            logger.error(f"Invalid 3D configuration: {e}")
            self.board_3d = None
            self.shader_3d = None
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error initializing 3D rendering: {e}", exc_info=True
            )
            self.board_3d = None
            self.shader_3d = None
            return False

        # Create 3D tokens
        self.create_tokens_with_effects(game_state, ctx, viewing_player_id=None)
        return True

    def create_tokens_with_effects(
        self, game_state, ctx, viewing_player_id: str | None = None
    ) -> None:
        """
        Create 3D tokens considering crystal effects.

        Args:
            game_state: Game state object
            ctx: OpenGL context
            viewing_player_id: Player ID viewing the board (for crystal effects)
        """
        self.tokens_3d.clear()
        self.phantom_tokens_3d.clear()

        if viewing_player_id is None:
            # No crystal effects - show all tokens
            for player in game_state.players.values():
                player_color = PLAYER_COLORS[player.color.value]

                for token_id in player.token_ids:
                    token = game_state.get_token(token_id)
                    if token and token.is_alive and token.is_deployed:
                        try:
                            token_3d = Token3D(
                                token, player_color, ctx, self.shader_3d, height=TOKEN_HEIGHT_3D
                            )
                            self.tokens_3d.append(token_3d)
                        except ValueError as e:
                            logger.error(f"Invalid token data for 3D: {token_id}: {e}")
                        except RuntimeError as e:
                            logger.error(
                                f"OpenGL error creating 3D token {token_id}: {e}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Unexpected error creating 3D token: {e}",
                                exc_info=True,
                            )
        else:
            # Apply crystal effects - get visible tokens for this player
            visible_tokens, phantom_tokens = game_state.get_visible_tokens_for_player(
                viewing_player_id
            )

            # Create 3D tokens for visible real tokens
            for token in visible_tokens:
                player = game_state.players[token.player_id]
                player_color = PLAYER_COLORS[player.color.value]
                try:
                    token_3d = Token3D(
                        token, player_color, ctx, self.shader_3d, height=TOKEN_HEIGHT_3D
                    )
                    self.tokens_3d.append(token_3d)
                except ValueError as e:
                    logger.error(f"Invalid token data for 3D: {token.id}: {e}")
                except RuntimeError as e:
                    logger.error(f"OpenGL error creating 3D token {token.id}: {e}")
                except Exception as e:
                    logger.error(
                        f"Unexpected error creating 3D token: {e}", exc_info=True
                    )

            # Create 3D phantom tokens
            for phantom in phantom_tokens:
                player_color = PLAYER_COLORS[
                    game_state.players[phantom.apparent_player_id].color.value
                ]
                try:
                    phantom_3d = PhantomToken3D(phantom, player_color, ctx, self.shader_3d)
                    self.phantom_tokens_3d.append(phantom_3d)
                except Exception as e:
                    logger.error(
                        f"Failed to create 3D phantom token {phantom.phantom_id}: {e}"
                    )

        logger.debug(
            f"Created {len(self.tokens_3d)} real 3D tokens and {len(self.phantom_tokens_3d)} phantom 3D tokens"
        )

    def add_token(self, token, player_color: tuple[int, int, int], ctx) -> None:
        """
        Add a single 3D token (used when deploying new tokens).

        Args:
            token: Token object to render
            player_color: RGB color tuple
            ctx: OpenGL context from Arcade window
        """
        try:
            token_3d = Token3D(token, player_color, ctx, self.shader_3d, height=TOKEN_HEIGHT_3D)
            self.tokens_3d.append(token_3d)
            logger.debug(f"Added 3D token {token.id}")
        except ValueError as e:
            logger.error(f"Invalid token data for 3D: {token.id}: {e}")
        except RuntimeError as e:
            logger.error(f"OpenGL error creating 3D token {token.id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating 3D token: {e}", exc_info=True)

    def sync_tokens(
        self, game_state, ctx, viewing_player_id: str | None = None
    ) -> None:
        """
        Synchronize 3D tokens with game state, animating changes.

        Args:
            game_state: New game state object
            ctx: OpenGL context
            viewing_player_id: Player ID viewing the board (for crystal effects)
        """
        if viewing_player_id is None:
            # No crystal effects - use original logic
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
                        # Just update target, Token3D handles interpolation
                        token_3d.update_position(
                            token.position[0], token.position[1], instant=False
                        )
                    else:
                        # Create new token
                        try:
                            self.add_token(token, player_color, ctx)
                        except ValueError as e:
                            logger.error(f"Invalid token data for 3D: {token_id}: {e}")
                        except RuntimeError as e:
                            logger.error(
                                f"OpenGL error creating 3D token {token_id}: {e}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Unexpected error creating 3D token: {e}",
                                exc_info=True,
                            )

            # Remove dead/undeployed tokens
            tokens_to_remove = []
            for token_3d in self.tokens_3d:
                if token_3d.token.id not in processed_ids:
                    tokens_to_remove.append(token_3d)

            for token_3d in tokens_to_remove:
                token_3d.cleanup()
                self.tokens_3d.remove(token_3d)
        else:
            # Apply crystal effects - recreate all tokens
            # This is simpler than trying to sync individual phantom tokens
            self.create_tokens_with_effects(game_state, ctx, viewing_player_id)

    def update(self, delta_time: float) -> None:
        """
        Update 3D animations.

        Args:
            delta_time: Time since last update
        """
        for token_3d in self.tokens_3d:
            if hasattr(token_3d, "update"):
                token_3d.update(delta_time)

    def remove_token(self, token_id: TokenID) -> None:
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
        self, mystery_animations: dict[tuple[int, int], float]
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

    def update_selection_visuals(
        self, selected_token_id: TokenID | None, valid_moves: set
    ) -> None:
        """
        Update selection and valid move indicators in 3D mode.

        Args:
            selected_token_id: ID of selected token (None if no selection)
            valid_moves: Set of (x, y) grid coordinates where token can move
        """
        self.selected_token_id = selected_token_id
        if self.board_3d:
            self.board_3d.update_valid_moves(valid_moves)

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
                    is_selected = token_3d.token.id == self.selected_token_id
                    token_3d.draw(camera_3d, self.shader_3d, is_selected=is_selected)

            # Draw phantom tokens (always on top)
            for phantom_3d in self.phantom_tokens_3d:
                phantom_3d.draw(camera_3d, self.shader_3d, is_selected=False)

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
