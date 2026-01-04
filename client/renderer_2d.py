"""
2D renderer for Race to the Crystal.

This module handles all 2D rendering including board shapes, token sprites,
and selection visuals.
"""

import math
from typing import Dict, List, Optional, Set, Tuple

import arcade
from arcade import SpriteList
from arcade.shape_list import ShapeElementList

from client.sprites.board_sprite import create_board_shapes
from client.sprites.token_sprite import TokenSprite
from shared.constants import CELL_SIZE, CIRCLE_SEGMENTS, PLAYER_COLORS
from shared.logging_config import setup_logger

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
        self.board_shapes: Optional[ShapeElementList] = None
        self.token_sprites: SpriteList = SpriteList()
        self.selection_shapes: ShapeElementList = ShapeElementList()

        # Store board data for recreating shapes (needed for animations)
        self.board = None
        self.generators = None
        self.crystal = None
        self.mystery_animations = None

    def create_board_sprites(
        self,
        board,
        generators: List,
        crystal,
        mystery_animations: Dict[Tuple[int, int], float],
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
        self.generators = generators
        self.crystal = crystal
        self.mystery_animations = mystery_animations

        crystal_pos = crystal.position if crystal else None

        self.board_shapes = create_board_shapes(
            board,
            generators=generators,
            crystal_pos=crystal_pos,
            mystery_animations=mystery_animations,
        )
        logger.debug("Created board shapes for 2D rendering")

    def create_token_sprites(self, game_state) -> None:
        """
        Create sprites for all tokens.

        Args:
            game_state: Game state object
        """
        self.token_sprites.clear()

        for player in game_state.players.values():
            player_color = PLAYER_COLORS[player.color.value]

            for token_id in player.token_ids:
                token = game_state.get_token(token_id)
                if token and token.is_alive and token.is_deployed:
                    sprite = TokenSprite(token, player_color)
                    self.token_sprites.append(sprite)

        logger.debug(
            f"Created {len(self.token_sprites)} token sprites for 2D rendering"
        )

    def sync_tokens(self, game_state) -> None:
        """
        Synchronize token sprites with game state, animating changes.

        Args:
            game_state: New game state object
        """
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
                        logger.debug(f"Animating token {token_id} from ({current_grid_x},{current_grid_y}) to ({token.position[0]},{token.position[1]})")
                        sprite.update_position(
                            token.position[0], token.position[1], instant=False
                        )
                    else:
                        logger.debug(f"Token {token_id} already at target position ({token.position[0]},{token.position[1]})")
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

    def update_selection_visuals(
        self,
        selected_token_id: Optional[int],
        valid_moves: Set[Tuple[int, int]],
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

        if selected_token_id:
            # Find selected token position
            selected_token = game_state.get_token(selected_token_id)
            if selected_token:
                # Draw pulsing selection highlight with glow
                x = selected_token.position[0] * CELL_SIZE + CELL_SIZE // 2
                y = selected_token.position[1] * CELL_SIZE + CELL_SIZE // 2
                size = CELL_SIZE * 0.8
                half = size / 2

                # Glow layers for selection
                for i in range(6, 0, -1):
                    alpha = int(180 / (i + 1))
                    glow_size = size + (i * 4)
                    glow_half = glow_size / 2
                    # Clamp coordinates to prevent negative values (fixes clipping at board edges)
                    points = [
                        (max(0, x - glow_half), max(0, y - glow_half)),
                        (max(0, x + glow_half), max(0, y - glow_half)),
                        (max(0, x + glow_half), max(0, y + glow_half)),
                        (max(0, x - glow_half), max(0, y + glow_half)),
                        (max(0, x - glow_half), max(0, y - glow_half)),
                    ]
                    for j in range(len(points) - 1):
                        line = create_line(
                            points[j][0],
                            points[j][1],
                            points[j + 1][0],
                            points[j + 1][1],
                            (255, 255, 0, alpha),
                            max(1, 4 - i // 2),
                        )
                        self.selection_shapes.append(line)

                # Bright main selection square (clamp coordinates)
                points = [
                    (max(0, x - half), max(0, y - half)),
                    (max(0, x + half), max(0, y - half)),
                    (max(0, x + half), max(0, y + half)),
                    (max(0, x - half), max(0, y + half)),
                    (max(0, x - half), max(0, y - half)),
                ]
                for j in range(len(points) - 1):
                    line = create_line(
                        points[j][0],
                        points[j][1],
                        points[j + 1][0],
                        points[j + 1][1],
                        (255, 255, 100, 255),
                        4,
                    )
                    self.selection_shapes.append(line)

        # Draw valid move indicators as glowing circles
        for move in valid_moves:
            x = move[0] * CELL_SIZE + CELL_SIZE // 2
            y = move[1] * CELL_SIZE + CELL_SIZE // 2
            radius = CELL_SIZE * 0.3
            segments = CIRCLE_SEGMENTS

            # Glow layers (clamp coordinates to prevent negative values)
            for i in range(4, 0, -1):
                alpha = int(120 / (i + 1))
                glow_radius = radius + (i * 3)
                points = []
                for seg in range(segments + 1):
                    angle = (seg / segments) * 2 * math.pi
                    px = max(0, x + glow_radius * math.cos(angle))
                    py = max(0, y + glow_radius * math.sin(angle))
                    points.append((px, py))

                for j in range(len(points) - 1):
                    line = create_line(
                        points[j][0],
                        points[j][1],
                        points[j + 1][0],
                        points[j + 1][1],
                        (0, 255, 0, alpha),
                        max(1, 3 - i // 2),
                    )
                    self.selection_shapes.append(line)

            # Bright main circle (clamp coordinates)
            points = []
            for seg in range(segments + 1):
                angle = (seg / segments) * 2 * math.pi
                px = max(0, x + radius * math.cos(angle))
                py = max(0, y + radius * math.sin(angle))
                points.append((px, py))

            for j in range(len(points) - 1):
                line = create_line(
                    points[j][0],
                    points[j][1],
                    points[j + 1][0],
                    points[j + 1][1],
                    (100, 255, 100, 255),
                    3,
                )
                self.selection_shapes.append(line)

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

    def cleanup(self) -> None:
        """Clean up rendering resources."""
        self.board_shapes = None
        self.token_sprites.clear()
        self.selection_shapes = ShapeElementList()
        logger.debug("Cleaned up 2D renderer")
