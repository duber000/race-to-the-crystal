"""Vector graphics utilities with glow effects for Tron-style aesthetics."""

import pygame
import math
from typing import List, Tuple


# Tron-inspired color palette
COLORS = {
    'background': (10, 10, 15),  # Dark background #0a0a0f
    'cyan': (0, 255, 255),
    'magenta': (255, 0, 255),
    'yellow': (255, 255, 0),
    'green': (0, 255, 0),
    'white': (255, 255, 255),
    'gray': (128, 128, 128),
    'dark_gray': (64, 64, 64),
}

# Player colors (neon glow)
PLAYER_COLORS = [
    COLORS['cyan'],      # Player 1
    COLORS['magenta'],   # Player 2
    COLORS['yellow'],    # Player 3
    COLORS['green'],     # Player 4
]


def draw_glow_circle(surface: pygame.Surface, color: Tuple[int, int, int], center: Tuple[int, int], radius: int, glow_size: int = 3):
    """
    Draw a circle with a glow effect.

    Args:
        surface: Surface to draw on
        color: RGB color tuple
        center: (x, y) center position
        radius: Radius of the circle
        glow_size: Number of glow layers (more = stronger glow)
    """
    # Draw glow layers from outer to inner
    for i in range(glow_size, 0, -1):
        # Calculate alpha and size for this layer
        alpha = int(255 * (glow_size - i + 1) / (glow_size * 2))
        glow_radius = radius + i * 2

        # Create temporary surface for this glow layer
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        glow_color = (*color, alpha)
        pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)

        # Blit to main surface
        surface.blit(glow_surface, (center[0] - glow_radius, center[1] - glow_radius))

    # Draw the solid center
    pygame.draw.circle(surface, color, center, radius)


def draw_glow_line(surface: pygame.Surface, color: Tuple[int, int, int], start: Tuple[int, int], end: Tuple[int, int], width: int = 2, glow_size: int = 3):
    """
    Draw a line with a glow effect.

    Args:
        surface: Surface to draw on
        color: RGB color tuple
        start: (x, y) start position
        end: (x, y) end position
        width: Line width
        glow_size: Number of glow layers
    """
    # Draw glow layers
    for i in range(glow_size, 0, -1):
        alpha = int(255 * (glow_size - i + 1) / (glow_size * 2))
        glow_width = width + i * 2

        # Create a temporary surface for the glow
        max_x = max(start[0], end[0]) + glow_width + 10
        max_y = max(start[1], end[1]) + glow_width + 10
        min_x = min(start[0], end[0]) - glow_width - 10
        min_y = min(start[1], end[1]) - glow_width - 10

        if max_x <= min_x or max_y <= min_y:
            continue

        glow_surface = pygame.Surface((max_x - min_x, max_y - min_y), pygame.SRCALPHA)
        glow_color = (*color, alpha)

        # Adjust coordinates for the temporary surface
        adj_start = (start[0] - min_x, start[1] - min_y)
        adj_end = (end[0] - min_x, end[1] - min_y)

        pygame.draw.line(glow_surface, glow_color, adj_start, adj_end, glow_width)
        surface.blit(glow_surface, (min_x, min_y))

    # Draw solid line on top
    pygame.draw.line(surface, color, start, end, width)


def draw_glow_rect(surface: pygame.Surface, color: Tuple[int, int, int], rect: pygame.Rect, width: int = 2, glow_size: int = 3):
    """
    Draw a rectangle outline with a glow effect.

    Args:
        surface: Surface to draw on
        color: RGB color tuple
        rect: Rectangle to draw
        width: Line width
        glow_size: Number of glow layers
    """
    # Draw glow layers
    for i in range(glow_size, 0, -1):
        alpha = int(255 * (glow_size - i + 1) / (glow_size * 2))
        glow_width = width + i * 2

        # Expand rect for glow
        glow_rect = rect.inflate(i * 4, i * 4)

        # Create temporary surface
        glow_surface = pygame.Surface((glow_rect.width + 20, glow_rect.height + 20), pygame.SRCALPHA)
        glow_color = (*color, alpha)

        # Draw on temporary surface
        temp_rect = pygame.Rect(10, 10, glow_rect.width, glow_rect.height)
        pygame.draw.rect(glow_surface, glow_color, temp_rect, glow_width)

        # Blit to main surface
        surface.blit(glow_surface, (glow_rect.x - 10, glow_rect.y - 10))

    # Draw solid rectangle on top
    pygame.draw.rect(surface, color, rect, width)


def draw_glow_polygon(surface: pygame.Surface, color: Tuple[int, int, int], points: List[Tuple[int, int]], width: int = 2, glow_size: int = 3):
    """
    Draw a polygon with a glow effect.

    Args:
        surface: Surface to draw on
        color: RGB color tuple
        points: List of (x, y) points
        width: Line width (0 for filled polygon)
        glow_size: Number of glow layers
    """
    if len(points) < 3:
        return

    # Calculate bounding box
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Draw glow layers
    for i in range(glow_size, 0, -1):
        alpha = int(255 * (glow_size - i + 1) / (glow_size * 2))
        glow_width = width + i * 2 if width > 0 else 0

        # Create temporary surface
        surf_width = max_x - min_x + glow_size * 4 + 20
        surf_height = max_y - min_y + glow_size * 4 + 20
        glow_surface = pygame.Surface((surf_width, surf_height), pygame.SRCALPHA)
        glow_color = (*color, alpha)

        # Adjust points for temporary surface
        offset_x = min_x - glow_size * 2 - 10
        offset_y = min_y - glow_size * 2 - 10
        adj_points = [(p[0] - offset_x, p[1] - offset_y) for p in points]

        # Draw on temporary surface
        if width == 0:
            pygame.draw.polygon(glow_surface, glow_color, adj_points)
        else:
            pygame.draw.polygon(glow_surface, glow_color, adj_points, glow_width)

        # Blit to main surface
        surface.blit(glow_surface, (offset_x, offset_y))

    # Draw solid polygon on top
    if width == 0:
        pygame.draw.polygon(surface, color, points)
    else:
        pygame.draw.polygon(surface, color, points, width)


def draw_hexagon(surface: pygame.Surface, color: Tuple[int, int, int], center: Tuple[int, int], radius: int, filled: bool = True, glow: bool = True):
    """
    Draw a hexagon (for tokens).

    Args:
        surface: Surface to draw on
        color: RGB color tuple
        center: (x, y) center position
        radius: Radius from center to vertex
        filled: Whether to fill the hexagon
        glow: Whether to apply glow effect
    """
    # Calculate hexagon vertices
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)  # Start from top
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append((int(x), int(y)))

    # Draw with or without glow
    if glow:
        draw_glow_polygon(surface, color, points, width=0 if filled else 2)
    else:
        if filled:
            pygame.draw.polygon(surface, color, points)
        else:
            pygame.draw.polygon(surface, color, points, 2)


def draw_text_with_glow(surface: pygame.Surface, text: str, font: pygame.font.Font, color: Tuple[int, int, int], position: Tuple[int, int], glow_size: int = 2):
    """
    Draw text with a glow effect.

    Args:
        surface: Surface to draw on
        text: Text to draw
        font: Font to use
        color: RGB color tuple
        position: (x, y) position (top-left)
        glow_size: Number of glow layers
    """
    # Render glow layers
    for i in range(glow_size, 0, -1):
        alpha = int(255 * (glow_size - i + 1) / (glow_size * 2))
        glow_color = (*color, alpha)

        # Render glow text on transparent surface
        text_surface = font.render(text, True, glow_color)
        text_surface.set_alpha(alpha)

        # Blit with offset for glow effect
        for dx in range(-i, i + 1):
            for dy in range(-i, i + 1):
                if dx == 0 and dy == 0:
                    continue
                surface.blit(text_surface, (position[0] + dx, position[1] + dy))

    # Draw solid text on top
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, position)


def create_particle(pos: Tuple[float, float], velocity: Tuple[float, float], color: Tuple[int, int, int], lifetime: float) -> dict:
    """
    Create a particle for effects (explosions, sparks, etc.).

    Args:
        pos: (x, y) starting position
        velocity: (vx, vy) velocity vector
        color: RGB color tuple
        lifetime: How long the particle lives (seconds)

    Returns:
        Dictionary representing the particle
    """
    return {
        'pos': list(pos),
        'velocity': list(velocity),
        'color': color,
        'lifetime': lifetime,
        'max_lifetime': lifetime,
    }


def update_particle(particle: dict, dt: float) -> bool:
    """
    Update a particle's state.

    Args:
        particle: Particle dictionary
        dt: Delta time in seconds

    Returns:
        True if particle is still alive, False if it should be removed
    """
    particle['pos'][0] += particle['velocity'][0] * dt
    particle['pos'][1] += particle['velocity'][1] * dt
    particle['lifetime'] -= dt

    # Apply gravity or other forces if needed
    # particle['velocity'][1] += 100 * dt  # gravity

    return particle['lifetime'] > 0


def draw_particle(surface: pygame.Surface, particle: dict):
    """
    Draw a particle.

    Args:
        surface: Surface to draw on
        particle: Particle dictionary
    """
    # Calculate alpha based on remaining lifetime
    alpha_factor = particle['lifetime'] / particle['max_lifetime']
    alpha = int(255 * alpha_factor)

    if alpha <= 0:
        return

    # Draw as a small glowing circle
    pos = (int(particle['pos'][0]), int(particle['pos'][1]))
    color_with_alpha = (*particle['color'], alpha)

    # Create small surface for particle
    particle_surface = pygame.Surface((10, 10), pygame.SRCALPHA)
    pygame.draw.circle(particle_surface, color_with_alpha, (5, 5), 3)

    surface.blit(particle_surface, (pos[0] - 5, pos[1] - 5))
