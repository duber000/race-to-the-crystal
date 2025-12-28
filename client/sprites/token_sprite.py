"""
Arcade sprite for game tokens.

This module creates GPU-accelerated sprites for rendering tokens with
hexagon shapes, health displays, and glow effects.
"""

import arcade
from PIL import Image, ImageDraw, ImageFont
import math

from game.token import Token
from shared.constants import CELL_SIZE


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
        self.token_radius = int(CELL_SIZE * 0.45)  # Larger for better visibility

        # Create texture
        self._create_texture()

        # Set sprite position (Arcade uses center coordinates)
        self.center_x = token.position[0] * CELL_SIZE + CELL_SIZE // 2
        self.center_y = token.position[1] * CELL_SIZE + CELL_SIZE // 2

    def _create_texture(self):
        """Create a vector wireframe texture with glow effect for arcade aesthetic."""
        size = self.token_radius * 4  # Extra space for glow

        # Create PIL image with transparency on pure black
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        center = size // 2

        # Draw glowing hexagon wireframe (multiple passes for glow)
        # Outer glow layers
        for i in range(8, 0, -1):
            alpha = int(180 / (i + 1))  # Brighter glow
            radius = self.token_radius + (i * 2)
            width = max(1, 4 - i // 2)
            color = (*self.player_color, alpha)

            points = self._hexagon_points(center, center, radius)
            # Draw as outline only for wireframe effect
            draw.line(points + [points[0]], fill=color, width=width)

        # Main bright hexagon outline
        points = self._hexagon_points(center, center, self.token_radius)
        bright_color = tuple(min(255, c + 100) for c in self.player_color) + (255,)
        draw.line(points + [points[0]], fill=bright_color, width=3)

        # Draw health number with vector-style font
        try:
            # Try multiple font paths for cross-platform compatibility
            font_size = int(self.token_radius * 1.0)
            font_paths = [
                "/usr/share/fonts/liberation/LiberationMono-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
                "C:\\Windows\\Fonts\\arialbd.ttf",
            ]
            font = None
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except (IOError, OSError):
                    continue
            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        health_text = str(self.token.health)
        bbox = draw.textbbox((0, 0), health_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = center - text_width // 2
        text_y = center - text_height // 2

        # Draw glowing text
        # Glow layers
        for offset in range(4, 0, -1):
            alpha = int(150 / (offset + 1))
            glow_color = (*self.player_color, alpha)
            for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset)]:
                draw.text(
                    (text_x + dx, text_y + dy), health_text, fill=glow_color, font=font
                )

        # Bright main text
        draw.text((text_x, text_y), health_text, fill=bright_color, font=font)

        # Convert PIL image to Arcade texture
        self.texture = arcade.Texture(name=f"token_{self.token.id}", image=image)

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
