"""Camera and viewport management for the game."""

import pygame
from typing import Tuple


class Camera:
    """
    Manages the viewport for rendering the game board.

    Handles:
    - World-to-screen coordinate transformations
    - Zoom in/out functionality
    - Panning/scrolling the view
    - Centering on specific positions
    """

    def __init__(self, screen_width: int, screen_height: int, world_width: int, world_height: int):
        """
        Initialize the camera.

        Args:
            screen_width: Width of the game window in pixels
            screen_height: Height of the game window in pixels
            world_width: Width of the game world in world units
            world_height: Height of the game world in world units
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.world_width = world_width
        self.world_height = world_height

        # Camera position (center of view in world coordinates)
        self.x = world_width / 2
        self.y = world_height / 2

        # Zoom level (1.0 = normal, >1.0 = zoomed in, <1.0 = zoomed out)
        self.zoom = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 3.0

        # Pan velocity for smooth scrolling
        self.pan_speed = 10.0

    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """
        Convert world coordinates to screen coordinates.

        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space

        Returns:
            Tuple of (screen_x, screen_y) in pixels
        """
        # Calculate offset from camera center
        offset_x = (world_x - self.x) * self.zoom
        offset_y = (world_y - self.y) * self.zoom

        # Convert to screen coordinates (centered on screen)
        screen_x = int(self.screen_width / 2 + offset_x)
        screen_y = int(self.screen_height / 2 + offset_y)

        return screen_x, screen_y

    def screen_to_world(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """
        Convert screen coordinates to world coordinates.

        Args:
            screen_x: X coordinate on screen in pixels
            screen_y: Y coordinate on screen in pixels

        Returns:
            Tuple of (world_x, world_y)
        """
        # Calculate offset from screen center
        offset_x = screen_x - self.screen_width / 2
        offset_y = screen_y - self.screen_height / 2

        # Convert to world coordinates
        world_x = self.x + offset_x / self.zoom
        world_y = self.y + offset_y / self.zoom

        return world_x, world_y

    def set_zoom(self, zoom: float):
        """
        Set the zoom level, clamped to min/max bounds.

        Args:
            zoom: New zoom level
        """
        self.zoom = max(self.min_zoom, min(self.max_zoom, zoom))

    def zoom_in(self, factor: float = 1.1):
        """Zoom in by a given factor."""
        self.set_zoom(self.zoom * factor)

    def zoom_out(self, factor: float = 1.1):
        """Zoom out by a given factor."""
        self.set_zoom(self.zoom / factor)

    def pan(self, dx: float, dy: float):
        """
        Pan the camera by a given offset.

        Args:
            dx: Change in X position (world units)
            dy: Change in Y position (world units)
        """
        self.x += dx
        self.y += dy

        # Optional: Clamp to world bounds
        # self.x = max(0, min(self.world_width, self.x))
        # self.y = max(0, min(self.world_height, self.y))

    def center_on(self, world_x: float, world_y: float):
        """
        Center the camera on a specific world position.

        Args:
            world_x: X coordinate to center on
            world_y: Y coordinate to center on
        """
        self.x = world_x
        self.y = world_y

    def update(self, dt: float):
        """
        Update camera state (for animations, smooth movements, etc.).

        Args:
            dt: Delta time since last update in seconds
        """
        # Can add smooth camera movements, easing, etc. here
        pass

    def get_visible_rect(self) -> Tuple[float, float, float, float]:
        """
        Get the rectangle of world space currently visible on screen.

        Returns:
            Tuple of (left, top, width, height) in world coordinates
        """
        # Get the world coordinates of screen corners
        left, top = self.screen_to_world(0, 0)
        right, bottom = self.screen_to_world(self.screen_width, self.screen_height)

        width = right - left
        height = bottom - top

        return left, top, width, height
