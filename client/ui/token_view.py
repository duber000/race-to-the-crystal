"""Token rendering for the game."""

import pygame
from typing import Optional, List, Dict, Tuple
import math

from game.token import Token
from game.player import Player
from shared.constants import (
    CELL_SIZE,
    PLAYER_COLORS,
    GLOW_INTENSITY,
    MOVEMENT_ANIMATION_DURATION,
)
from client.ui.camera import Camera
from client.ui.vector_graphics import (
    draw_hexagon,
    draw_text_with_glow,
    COLORS,
)


class TokenAnimation:
    """Represents an animation for a token."""

    def __init__(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float], duration: float):
        """
        Initialize token animation.

        Args:
            start_pos: Starting (x, y) world position
            end_pos: Ending (x, y) world position
            duration: Animation duration in seconds
        """
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.duration = duration
        self.elapsed = 0.0
        self.finished = False

    def update(self, dt: float) -> Tuple[float, float]:
        """
        Update animation and get current position.

        Args:
            dt: Delta time in seconds

        Returns:
            Current (x, y) world position
        """
        self.elapsed += dt

        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.finished = True

        # Linear interpolation (can use easing functions for smoother animation)
        t = self.elapsed / self.duration
        x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * t
        y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * t

        return (x, y)


class TokenView:
    """Handles rendering of game tokens."""

    def __init__(self, cell_size: int = CELL_SIZE):
        """
        Initialize the token view.

        Args:
            cell_size: Size of each board cell in pixels
        """
        self.cell_size = cell_size
        self.token_radius = int(cell_size * 0.35)  # 35% of cell size

        # Font for rendering health numbers
        pygame.font.init()
        self.health_font = pygame.font.Font(None, int(cell_size * 0.5))

        # Animation tracking
        self.animations: Dict[int, TokenAnimation] = {}  # token_id -> animation

        # Selection state
        self.selected_token_id: Optional[int] = None

    def render(self, surface: pygame.Surface, tokens: List[Token], players: List[Player], camera: Camera, dt: float = 0.0):
        """
        Render all tokens to the surface.

        Args:
            surface: Surface to draw on
            tokens: List of tokens to render
            players: List of players (for color mapping)
            camera: Camera for coordinate transformation
            dt: Delta time for animations
        """
        for token in tokens:
            if not token.is_alive:
                continue

            self._render_token(surface, token, players, camera, dt)

    def _render_token(self, surface: pygame.Surface, token: Token, players: List[Player], camera: Camera, dt: float):
        """
        Render a single token.

        Args:
            surface: Surface to draw on
            token: Token to render
            players: List of players
            camera: Camera for coordinate transformation
            dt: Delta time for animations
        """
        # Get token color based on player
        player = next((p for p in players if p.id == token.player_id), None)
        if not player:
            return

        player_index = players.index(player)
        color = PLAYER_COLORS[player_index % len(PLAYER_COLORS)]

        # Get token position (animated or static)
        if token.id in self.animations:
            animation = self.animations[token.id]
            world_pos = animation.update(dt)

            if animation.finished:
                del self.animations[token.id]
        else:
            # Static position (cell center)
            world_pos = (
                (token.position[0] + 0.5) * self.cell_size,
                (token.position[1] + 0.5) * self.cell_size,
            )

        # Convert to screen coordinates
        screen_pos = camera.world_to_screen(*world_pos)

        # Calculate radius based on zoom
        radius = int(self.token_radius * camera.zoom)

        # Draw selection indicator if selected
        if token.id == self.selected_token_id:
            selection_radius = int(radius * 1.3)
            from client.ui.vector_graphics import draw_glow_circle
            draw_glow_circle(surface, COLORS['white'], screen_pos, selection_radius, glow_size=GLOW_INTENSITY + 1)

        # Draw hexagon token
        draw_hexagon(surface, color, screen_pos, radius, filled=True, glow=True)

        # Draw health number
        health_text = str(token.health)
        text_color = COLORS['white'] if token.health > token.max_health // 2 else COLORS['yellow']

        # Calculate text position (centered)
        text_surface = self.health_font.render(health_text, True, text_color)
        text_rect = text_surface.get_rect(center=screen_pos)

        # Draw text with glow
        draw_text_with_glow(surface, health_text, self.health_font, text_color, text_rect.topleft, glow_size=2)

    def start_move_animation(self, token: Token, start_cell: Tuple[int, int], end_cell: Tuple[int, int]):
        """
        Start a movement animation for a token.

        Args:
            token: Token to animate
            start_cell: Starting cell coordinates
            end_cell: Ending cell coordinates
        """
        start_world = (
            (start_cell[0] + 0.5) * self.cell_size,
            (start_cell[1] + 0.5) * self.cell_size,
        )
        end_world = (
            (end_cell[0] + 0.5) * self.cell_size,
            (end_cell[1] + 0.5) * self.cell_size,
        )

        self.animations[token.id] = TokenAnimation(start_world, end_world, MOVEMENT_ANIMATION_DURATION)

    def set_selected_token(self, token_id: Optional[int]):
        """
        Set the currently selected token.

        Args:
            token_id: ID of the token to select, or None to deselect
        """
        self.selected_token_id = token_id

    def get_token_at_screen_pos(self, screen_pos: Tuple[int, int], tokens: List[Token], camera: Camera) -> Optional[Token]:
        """
        Get the token at a screen position (if any).

        Args:
            screen_pos: (x, y) position on screen
            tokens: List of tokens to check
            camera: Camera for coordinate transformation

        Returns:
            Token at the position, or None
        """
        world_pos = camera.screen_to_world(*screen_pos)

        # Check each token
        for token in tokens:
            if not token.is_alive:
                continue

            # Get token world position
            token_world_pos = (
                (token.position[0] + 0.5) * self.cell_size,
                (token.position[1] + 0.5) * self.cell_size,
            )

            # Check distance
            dx = world_pos[0] - token_world_pos[0]
            dy = world_pos[1] - token_world_pos[1]
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= self.token_radius:
                return token

        return None

    def render_movement_range(self, surface: pygame.Surface, valid_moves: List[Tuple[int, int]], camera: Camera):
        """
        Render valid movement positions for a selected token.

        Args:
            surface: Surface to draw on
            valid_moves: List of (x, y) cell coordinates
            camera: Camera for coordinate transformation
        """
        from client.ui.vector_graphics import draw_glow_circle

        for cell_x, cell_y in valid_moves:
            # Get cell center in world coordinates
            world_x = (cell_x + 0.5) * self.cell_size
            world_y = (cell_y + 0.5) * self.cell_size
            screen_pos = camera.world_to_screen(world_x, world_y)

            # Draw indicator
            radius = int(self.token_radius * 0.3 * camera.zoom)
            draw_glow_circle(surface, COLORS['white'], screen_pos, radius, glow_size=2)

    def render_attack_range(self, surface: pygame.Surface, valid_targets: List[Tuple[int, int]], camera: Camera):
        """
        Render valid attack positions for a selected token.

        Args:
            surface: Surface to draw on
            valid_targets: List of (x, y) cell coordinates
            camera: Camera for coordinate transformation
        """
        from client.ui.vector_graphics import draw_glow_circle

        for cell_x, cell_y in valid_targets:
            # Get cell center in world coordinates
            world_x = (cell_x + 0.5) * self.cell_size
            world_y = (cell_y + 0.5) * self.cell_size
            screen_pos = camera.world_to_screen(world_x, world_y)

            # Draw red indicator for attack
            radius = int(self.token_radius * 0.4 * camera.zoom)
            draw_glow_circle(surface, (255, 0, 0), screen_pos, radius, glow_size=2)
