"""
Arcade sprite for phantom game tokens.

This module creates GPU-accelerated sprites for rendering phantom tokens with
a ghostly, translucent appearance to distinguish them from real tokens.
"""

import arcade
from PIL import Image, ImageDraw, ImageFont
import math

from game.crystal_effects import PhantomToken
from shared.constants import CELL_SIZE, MOVEMENT_ANIMATION_DURATION


class PhantomTokenSprite(arcade.Sprite):
    """
    Arcade sprite representing a phantom/illusion token.

    Renders as a translucent, ghostly hexagon with the token's apparent health value displayed.
    """

    def __init__(self, phantom_token: PhantomToken, player_color: tuple):
        """
        Initialize a phantom token sprite.

        Args:
            phantom_token: The phantom token this sprite represents
            player_color: RGB color tuple for the apparent player
        """
        super().__init__()

        self.phantom_token = phantom_token
        self.player_color = player_color
        self.token_radius = int(CELL_SIZE * 0.45)  # Same size as real tokens

        # Create texture with ghostly appearance
        self._create_texture()

        # Set sprite position (Arcade uses center coordinates)
        self.target_x = phantom_token.position[0] * CELL_SIZE + CELL_SIZE // 2
        self.target_y = phantom_token.position[1] * CELL_SIZE + CELL_SIZE // 2
        self.center_x = self.target_x
        self.center_y = self.target_y

        self.is_moving = False
        self.move_speed = 10.0  # Pixels per frame approximation, will use delta_time

    def _create_texture(self):
        """Create a ghostly, translucent texture for phantom tokens."""
        size = self.token_radius * 4  # Extra space for glow

        # Create PIL image with transparency
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        center = size // 2

        # Draw ghostly hexagon wireframe (semi-transparent)
        # Use player color with transparency to show phantom nature
        base_color = self.player_color

        # Multiple layers for ghostly glow effect
        for i in range(4, 0, -1):
            alpha = int(120 / (i + 1))  # More transparent glow
            radius = self.token_radius + (i * 2)
            width = max(1, 3 - i // 2)
            color = (*base_color, alpha)

            points = self._hexagon_points(center, center, radius)
            # Draw as outline only for wireframe effect
            draw.line(points + [points[0]], fill=color, width=width)

        # Main ghostly hexagon outline
        points = self._hexagon_points(center, center, self.token_radius)
        main_color = (*base_color, 200)  # Slightly more opaque
        draw.line(points + [points[0]], fill=main_color, width=2)

        # Draw apparent health number with ghostly appearance
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
                except IOError, OSError:
                    continue
            if font is None:
                font = ImageFont.load_default()
        except OSError as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Font file not found, using default: {e}")
            font = ImageFont.load_default()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Unexpected font error, using default: {e}")
            font = ImageFont.load_default()

        health_text = str(self.phantom_token.apparent_health)
        bbox = draw.textbbox((0, 0), health_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = center - text_width // 2
        text_y = center - text_height // 2

        # Draw ghostly text with transparency using player color
        # Lighten the player color for better visibility on dark background
        lightened_color = tuple(min(255, int(c * 1.3)) for c in base_color)
        text_color = (*lightened_color, 220)  # Semi-transparent

        # Glow layers
        for offset in range(3, 0, -1):
            alpha = int(100 / (offset + 1))
            glow_color = (*lightened_color, alpha)
            for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset)]:
                draw.text(
                    (text_x + dx, text_y + dy), health_text, fill=glow_color, font=font
                )

        # Main ghostly text
        draw.text((text_x, text_y), health_text, fill=text_color, font=font)

        # Convert PIL image to Arcade texture
        self.texture = arcade.Texture(
            name=f"phantom_{self.phantom_token.phantom_id}", image=image
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

    def update_position(self, grid_x: int, grid_y: int, instant: bool = True):
        """
        Update sprite position to a new grid cell.

        Args:
            grid_x: Grid x coordinate
            grid_y: Grid y coordinate
            instant: Whether to move instantly or animate
        """
        target_x = grid_x * CELL_SIZE + CELL_SIZE // 2
        target_y = grid_y * CELL_SIZE + CELL_SIZE // 2

        self.target_x = target_x
        self.target_y = target_y

        if instant:
            self.center_x = target_x
            self.center_y = target_y
            self.is_moving = False
        else:
            self.is_moving = True

    def update(self, delta_time: float = 1 / 60):
        """
        Update sprite animation.

        Args:
            delta_time: Time since last update in seconds
        """
        if not self.is_moving:
            return

        # Move towards target
        dx = self.target_x - self.center_x
        dy = self.target_y - self.center_y

        dist = (dx * dx + dy * dy) ** 0.5

        # Calculate speed based on movement duration
        speed = (CELL_SIZE / MOVEMENT_ANIMATION_DURATION) * delta_time

        # Increase speed if distance is large (to catch up)
        if dist > CELL_SIZE * 2:
            speed *= 2.0

        if dist <= speed:
            self.center_x = self.target_x
            self.center_y = self.target_y
            self.is_moving = False
        else:
            # Normalize and scale
            self.center_x += (dx / dist) * speed
            self.center_y += (dy / dist) * speed

    def update_health(self):
        """Recreate texture when apparent health changes."""
        self._create_texture()
