"""
Arcade sprite for game tokens.

This module creates GPU-accelerated sprites for rendering tokens with
hexagon shapes, health displays, and glow effects.
"""

import arcade
from PIL import Image, ImageDraw, ImageFont
import math

from game.token import Token
from shared.constants import CELL_SIZE, PLAYER_COLORS


class TokenSprite(arcade.Sprite):
    """
    Arcade sprite representing a game token.

    Renders as a glowing hexagon with the token's health value displayed.
    """

    def __init__(self, token: Token, player_color: tuple):
        """
        Initialize a token sprite.

        Args:
            token: The game token this sprite represents
            player_color: RGB color tuple for this player
        """
        super().__init__()

        self.token = token
        self.player_color = player_color
        self.token_radius = int(CELL_SIZE * 0.35)

        # Create texture
        self._create_texture()

        # Set sprite position (Arcade uses center coordinates)
        self.center_x = token.position[0] * CELL_SIZE + CELL_SIZE // 2
        self.center_y = token.position[1] * CELL_SIZE + CELL_SIZE // 2

    def _create_texture(self):
        """Create a texture for the token with hexagon shape and health number."""
        size = self.token_radius * 3  # Give extra space for glow

        # Create PIL image with transparency
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        center = size // 2

        # Draw hexagon with glow effect (multiple layers for glow)
        glow_layers = 5
        for i in range(glow_layers, 0, -1):
            alpha = int(100 / (i + 1))  # Fade out glow
            radius = self.token_radius + (i * 3)
            color = (*self.player_color, alpha)

            # Calculate hexagon points
            points = self._hexagon_points(center, center, radius)
            draw.polygon(points, fill=color, outline=color)

        # Draw main hexagon
        points = self._hexagon_points(center, center, self.token_radius)
        draw.polygon(points, fill=self.player_color, outline=self.player_color)

        # Draw health number
        try:
            # Try to use a nice font if available
            font_size = int(self.token_radius * 0.8)
            font = ImageFont.truetype("/usr/share/fonts/liberation/LiberationMono-Bold.ttf", font_size)
        except:
            # Fall back to default font
            font = ImageFont.load_default()

        health_text = str(self.token.health)

        # Get text bounding box for centering
        bbox = draw.textbbox((0, 0), health_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = center - text_width // 2
        text_y = center - text_height // 2

        # Draw text with dark outline for contrast
        outline_color = (0, 0, 0, 255)
        for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            draw.text((text_x + dx, text_y + dy), health_text, fill=outline_color, font=font)

        # Draw main text in white
        draw.text((text_x, text_y), health_text, fill=(255, 255, 255, 255), font=font)

        # Convert PIL image to Arcade texture
        self.texture = arcade.Texture(
            name=f"token_{self.token.id}",
            image=image
        )

    def _hexagon_points(self, cx: float, cy: float, radius: float) -> list:
        """
        Calculate hexagon vertices.

        Args:
            cx: Center x
            cy: Center y
            radius: Hexagon radius

        Returns:
            List of (x, y) tuples for hexagon points
        """
        points = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2  # Start from top
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append((x, y))
        return points

    def update_position(self, grid_x: int, grid_y: int):
        """
        Update sprite position to a new grid cell.

        Args:
            grid_x: Grid x coordinate
            grid_y: Grid y coordinate
        """
        self.center_x = grid_x * CELL_SIZE + CELL_SIZE // 2
        self.center_y = grid_y * CELL_SIZE + CELL_SIZE // 2

    def update_health(self):
        """Recreate texture when health changes."""
        self._create_texture()
