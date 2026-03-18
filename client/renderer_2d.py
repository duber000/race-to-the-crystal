"""
2D renderer for Race to the Crystal.

This module handles all 2D rendering including board shapes, token sprites,
and selection visuals.
"""

import math
from collections.abc import Sequence

import arcade
from arcade import SpriteList
from arcade.shape_list import ShapeElementList

from client.sprites.board_sprite import create_board_shapes
from client.sprites.token_sprite import TokenSprite
from client.sprites.phantom_token_sprite import PhantomTokenSprite
from shared.constants import CELL_SIZE, CIRCLE_SEGMENTS, PLAYER_COLORS
from shared.logging_config import setup_logger
from shared.types import TokenID

logger = setup_logger(__name__)


def create_line(
    start_x: float, start_y: float, end_x: float, end_y: float, color, line_width: int
) -> arcade.shape_list.Shape:
    """
    Create a line shape for rendering.

    Args:
        start_x: Start x coordinate
        start_y: Start y coordinate
        end_x: End x coordinate
        end_y: End y coordinate
        color: RGBA color tuple
        line_width: Line width in pixels

    Returns:
        Line shape object
    """
    return arcade.shape_list.create_line(
        start_x, start_y, end_x, end_y, color, line_width
    )


class Renderer2D:
    """
    Manages all 2D rendering for the game.

    The Renderer2D handles:
    - Board shapes (grid, generators, crystal, mystery squares)
    - Token sprites (player tokens)
    - Selection visuals (highlights and valid move indicators)
    - 2D rendering updates and drawing
    """

    def __init__(self):
        """Initialize 2D renderer."""
        # Sprite lists
        self.board_shapes: ShapeElementList | None = None
        self.token_sprites: SpriteList = SpriteList()
        self.selection_shapes: ShapeElementList = ShapeElementList()
        self.phantom_token_sprites: SpriteList = SpriteList()

        # Store board data for recreating shapes (needed for animations)
        self.board = None
        self.generators = None
        self.crystal = None
        self.mystery_animations = None

    def create_board_sprites(
        self,
        board,
        generators: list,
        crystal,
        mystery_animations: dict[tuple[int, int], float],
    ) -> None:
        """
        Create shapes for the board (grid, generators, crystal, mystery squares).

        Args:
            board: Game board object
            generators: List of generator objects
            crystal: Crystal object
            mystery_animations: Dict mapping positions to animation progress (0.0-1.0)
        """
        # Store references for recreating shapes during updates (needed for animations)
        self.board = board

        # Network play currently sends generators/crystal as empty/None.
        # Fall back to board metadata so animations still run.
        if crystal is None and hasattr(board, "get_crystal_position"):

            class _DummyCrystal:
                def __init__(self, pos: tuple[int, int]):
                    self.position = pos

            self.crystal = _DummyCrystal(board.get_crystal_position())
        else:
            self.crystal = crystal

        if (not generators) and hasattr(board, "get_generator_positions"):

            class _DummyGenerator:
                def __init__(self, pos: tuple[int, int]):
                    self.position = pos
                    self.is_disabled = False

            self.generators = [
                _DummyGenerator(pos) for pos in board.get_generator_positions()
            ]
        else:
            self.generators = generators

        self.mystery_animations = mystery_animations

        crystal_pos = self.crystal.position if self.crystal else None

        self.board_shapes = create_board_shapes(
            board,
            generators=self.generators,
            crystal_pos=crystal_pos,
            mystery_animations=self.mystery_animations,
        )
        logger.debug("Created board shapes for 2D rendering")

    def create_token_sprites(
        self, game_state, viewing_player_id: str | None = None
    ) -> None:
        """
        Create sprites for all tokens, considering crystal effects.

        Args:
            game_state: Game state object
            viewing_player_id: Player ID viewing the board (for crystal effects)
        """
        self.token_sprites.clear()
        self.phantom_token_sprites.clear()

        if viewing_player_id is None:
            # No crystal effects - show all tokens
            for player in game_state.players.values():
                player_color = PLAYER_COLORS[player.color.value]

                for token_id in player.token_ids:
                    token = game_state.get_token(token_id)
                    if token and token.is_alive and token.is_deployed:
                        sprite = TokenSprite(token, player_color)
                        self.token_sprites.append(sprite)
        else:
            # Apply crystal effects - get visible tokens for this player
            visible_tokens, phantom_tokens = game_state.get_visible_tokens_for_player(
                viewing_player_id
            )

            # Create sprites for visible real tokens
            for token in visible_tokens:
                player = game_state.players[token.player_id]
                player_color = PLAYER_COLORS[player.color.value]
                sprite = TokenSprite(token, player_color)
                self.token_sprites.append(sprite)

            # Create sprites for phantom tokens
            for phantom in phantom_tokens:
                player_color = PLAYER_COLORS[
                    game_state.players[phantom.apparent_player_id].color.value
                ]
                sprite = PhantomTokenSprite(phantom, player_color)
                self.phantom_token_sprites.append(sprite)

        logger.debug(
            f"Created {len(self.token_sprites)} real token sprites and {len(self.phantom_token_sprites)} phantom token sprites for 2D rendering"
        )

    def sync_tokens(self, game_state, viewing_player_id: str | None = None) -> None:
        """
        Synchronize token sprites with game state, animating changes.

        Args:
            game_state: New game state object
            viewing_player_id: Player ID viewing the board (for crystal effects)
        """
        if viewing_player_id is None:
            # No crystal effects - use original logic
            # Create a map of existing sprites by token ID
            existing_sprites = {
                sprite.token.id: sprite
                for sprite in self.token_sprites
                if hasattr(sprite, "token")
            }

            # Track which token IDs we've processed
            processed_ids = set()

            for player in game_state.players.values():
                player_color = PLAYER_COLORS[player.color.value]

                for token_id in player.token_ids:
                    token = game_state.get_token(token_id)
                    if not token or not token.is_alive or not token.is_deployed:
                        continue

                    processed_ids.add(token_id)

                    if token_id in existing_sprites:
                        # Update existing sprite
                        sprite = existing_sprites[token_id]

                        # Update health if changed
                        if sprite.token.health != token.health:
                            sprite.token = token  # Update reference
                            sprite.update_health()

                        # Update position (with animation)
                        # Check if position actually changed
                        current_grid_x = int(sprite.target_x // CELL_SIZE)
                        current_grid_y = int(sprite.target_y // CELL_SIZE)

                        if (
                            current_grid_x != token.position[0]
                            or current_grid_y != token.position[1]
                        ):
                            logger.debug(
                                f"Animating token {token_id} from ({current_grid_x},{current_grid_y}) to ({token.position[0]},{token.position[1]})"
                            )
                            sprite.update_position(
                                token.position[0], token.position[1], instant=False
                            )
                        else:
                            logger.debug(
                                f"Token {token_id} already at target position ({token.position[0]},{token.position[1]})"
                            )
                    else:
                        # Create new sprite
                        sprite = TokenSprite(token, player_color)
                        self.token_sprites.append(sprite)

            # Remove sprites for tokens that are no longer present/alive/deployed
            sprites_to_remove = []
            for sprite in self.token_sprites:
                if hasattr(sprite, "token") and sprite.token.id not in processed_ids:
                    sprites_to_remove.append(sprite)

            for sprite in sprites_to_remove:
                self.token_sprites.remove(sprite)
        else:
            # Apply crystal effects - recreate all sprites
            # This is simpler than trying to sync individual phantom tokens
            self.create_token_sprites(game_state, viewing_player_id)

    def update_selection_visuals(
        self,
        selected_token_id: TokenID | None,
        valid_moves: set[tuple[int, int]],
        game_state,
    ) -> None:
        """
        Update visual feedback for selection and valid moves with vector glow.

        Args:
            selected_token_id: ID of currently selected token (None if no selection)
            valid_moves: Set of valid move positions (grid coordinates)
            game_state: Game state object
        """
        self.selection_shapes = ShapeElementList()

        if selected_token_id is not None:
            # Find selected token position
            selected_token = game_state.get_token(selected_token_id)
            if selected_token:
                # Draw pulsing selection highlight with glow
                x = selected_token.position[0] * CELL_SIZE + CELL_SIZE // 2
                y = selected_token.position[1] * CELL_SIZE + CELL_SIZE // 2
                size = CELL_SIZE * 0.8
                half = size / 2

                # Glow layers for selection
                self._draw_glow_box(x, y, size, 6, (255, 255, 0), 180, 4)

                # Bright main selection square
                points = [
                    (max(0, x - half), max(0, y - half)),
                    (max(0, x + half), max(0, y - half)),
                    (max(0, x + half), max(0, y + half)),
                    (max(0, x - half), max(0, y + half)),
                    (max(0, x - half), max(0, y - half)),
                ]
                self._draw_polygon_lines(points, (255, 255, 100, 255), 4)

        # Draw valid move indicators as glowing circles
        for move in valid_moves:
            x = move[0] * CELL_SIZE + CELL_SIZE // 2
            y = move[1] * CELL_SIZE + CELL_SIZE // 2
            radius = CELL_SIZE * 0.3

            # Glow layers
            self._draw_glow_circle(x, y, radius, 4, (0, 255, 0), 120, 3)

            # Bright main circle
            self._draw_circle_lines(x, y, radius, (100, 255, 100, 255), 3)

    def update(self, delta_time: float) -> None:
        """
        Update animations.

        Args:
            delta_time: Time since last update in seconds
        """
        self.token_sprites.update_animation(delta_time)
        for sprite in self.token_sprites:
            if hasattr(sprite, "update"):
                sprite.update(delta_time)

        # Recreate board shapes every frame to update animations (glowing lines, crystal pulse)
        if (
            self.board is not None
            and self.generators is not None
            and self.crystal is not None
            and self.mystery_animations is not None
        ):
            crystal_pos = self.crystal.position if self.crystal else None
            self.board_shapes = create_board_shapes(
                self.board,
                generators=self.generators,
                crystal_pos=crystal_pos,
                mystery_animations=self.mystery_animations,
            )

    def draw(self, camera_2d) -> None:
        """
        Draw all 2D rendering elements.

        Args:
            camera_2d: 2D camera object for world-space rendering
        """
        with camera_2d.activate():
            if self.board_shapes:
                self.board_shapes.draw()
            self.selection_shapes.draw()
            self.token_sprites.draw()
            # Draw phantom tokens on top of real tokens
            self.phantom_token_sprites.draw()

    def _draw_glow_box(
        self,
        center_x: float,
        center_y: float,
        size: float,
        layers: int,
        base_color: tuple[int, int, int],
        max_alpha: int,
        max_width: int,
    ) -> None:
        """
        Draw a glowing box with multiple layers.

        Args:
            center_x: Center X coordinate
            center_y: Center Y coordinate
            size: Base size of the box
            layers: Number of glow layers
            base_color: RGB color tuple
            max_alpha: Maximum alpha value for innermost layer
            max_width: Maximum line width for innermost layer
        """
        for i in range(layers, 0, -1):
            alpha = int(max_alpha / (i + 1))
            glow_size = size + (i * 4)
            glow_half = glow_size / 2
            points = [
                (max(0, center_x - glow_half), max(0, center_y - glow_half)),
                (max(0, center_x + glow_half), max(0, center_y - glow_half)),
                (max(0, center_x + glow_half), max(0, center_y + glow_half)),
                (max(0, center_x - glow_half), max(0, center_y + glow_half)),
                (max(0, center_x - glow_half), max(0, center_y - glow_half)),
            ]
            self._draw_polygon_lines(
                points, (*base_color, alpha), max(1, max_width - i // 2)
            )

    def _draw_polygon_lines(
        self,
        points: Sequence[tuple[float, float]],
        color: tuple[int, int, int, int],
        line_width: int,
    ) -> None:
        """
        Draw lines connecting a sequence of points.

        Args:
            points: List of (x, y) coordinate tuples
            color: RGBA color tuple
            line_width: Width of the lines
        """
        for j in range(len(points) - 1):
            line = create_line(
                points[j][0],
                points[j][1],
                points[j + 1][0],
                points[j + 1][1],
                color,
                line_width,
            )
            self.selection_shapes.append(line)

    def _draw_glow_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        layers: int,
        base_color: tuple[int, int, int],
        max_alpha: int,
        max_width: int,
        segments: int = CIRCLE_SEGMENTS,
    ) -> None:
        """
        Draw a glowing circle with multiple layers.

        Args:
            center_x: Center X coordinate
            center_y: Center Y coordinate
            radius: Base radius
            layers: Number of glow layers
            base_color: RGB color tuple
            max_alpha: Maximum alpha value for innermost layer
            max_width: Maximum line width for innermost layer
            segments: Number of line segments to use for the circle
        """
        for i in range(layers, 0, -1):
            alpha = int(max_alpha / (i + 1))
            glow_radius = radius + (i * 3)
            points = []
            for seg in range(segments + 1):
                angle = (seg / segments) * 2 * math.pi
                px = max(0, center_x + glow_radius * math.cos(angle))
                py = max(0, center_y + glow_radius * math.sin(angle))
                points.append((px, py))
            self._draw_polygon_lines(
                points, (*base_color, alpha), max(1, max_width - i // 2)
            )

    def _draw_circle_lines(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        color: tuple[int, int, int, int],
        line_width: int,
        segments: int = CIRCLE_SEGMENTS,
    ) -> None:
        """
        Draw a circle as a series of connected lines.

        Args:
            center_x: Center X coordinate
            center_y: Center Y coordinate
            radius: Circle radius
            color: RGBA color tuple
            line_width: Width of the lines
            segments: Number of line segments to use
        """
        points = []
        for seg in range(segments + 1):
            angle = (seg / segments) * 2 * math.pi
            px = max(0, center_x + radius * math.cos(angle))
            py = max(0, center_y + radius * math.sin(angle))
            points.append((px, py))
        self._draw_polygon_lines(points, color, line_width)

    def cleanup(self) -> None:
        """Clean up rendering resources."""
        self.board_shapes = None
        self.token_sprites.clear()
        self.selection_shapes = ShapeElementList()
        logger.debug("Cleaned up 2D renderer")
