"""Board rendering for the game."""

import pygame
from typing import Optional

from game.board import Board
from shared.enums import CellType
from shared.constants import (
    CELL_SIZE,
    BACKGROUND_COLOR,
    GRID_LINE_COLOR,
    GENERATOR_COLOR,
    CRYSTAL_COLOR,
    MYSTERY_COLOR,
    START_COLOR,
    GLOW_INTENSITY,
)
from client.ui.camera import Camera
from client.ui.vector_graphics import (
    draw_glow_rect,
    draw_glow_circle,
    COLORS,
)


class BoardView:
    """Handles rendering of the game board."""

    def __init__(self, board: Board):
        """
        Initialize the board view.

        Args:
            board: The game board to render
        """
        self.board = board
        self.cell_size = CELL_SIZE

    def render(self, surface: pygame.Surface, camera: Camera):
        """
        Render the board to the surface.

        Args:
            surface: Surface to draw on
            camera: Camera for coordinate transformation
        """
        # Render grid
        self._render_grid(surface, camera)

        # Render special cells
        self._render_special_cells(surface, camera)

    def _render_grid(self, surface: pygame.Surface, camera: Camera):
        """
        Render the board grid lines.

        Args:
            surface: Surface to draw on
            camera: Camera for coordinate transformation
        """
        # Get visible area to avoid rendering off-screen lines
        visible_left, visible_top, visible_width, visible_height = camera.get_visible_rect()

        # Calculate which grid cells are visible
        start_x = max(0, int(visible_left / self.cell_size) - 1)
        start_y = max(0, int(visible_top / self.cell_size) - 1)
        end_x = min(self.board.width, int((visible_left + visible_width) / self.cell_size) + 2)
        end_y = min(self.board.height, int((visible_top + visible_height) / self.cell_size) + 2)

        # Render vertical lines
        for x in range(start_x, end_x + 1):
            world_x = x * self.cell_size
            start_world = (world_x, 0)
            end_world = (world_x, self.board.height * self.cell_size)

            start_screen = camera.world_to_screen(*start_world)
            end_screen = camera.world_to_screen(*end_world)

            pygame.draw.line(surface, GRID_LINE_COLOR, start_screen, end_screen, 1)

        # Render horizontal lines
        for y in range(start_y, end_y + 1):
            world_y = y * self.cell_size
            start_world = (0, world_y)
            end_world = (self.board.width * self.cell_size, world_y)

            start_screen = camera.world_to_screen(*start_world)
            end_screen = camera.world_to_screen(*end_world)

            pygame.draw.line(surface, GRID_LINE_COLOR, start_screen, end_screen, 1)

    def _render_special_cells(self, surface: pygame.Surface, camera: Camera):
        """
        Render special cells (generators, crystal, mystery squares, start positions).

        Args:
            surface: Surface to draw on
            camera: Camera for coordinate transformation
        """
        for y in range(self.board.height):
            for x in range(self.board.width):
                cell = self.board.get_cell(x, y)

                if cell.cell_type == CellType.NORMAL:
                    continue

                # Calculate cell center in world coordinates
                world_x = (x + 0.5) * self.cell_size
                world_y = (y + 0.5) * self.cell_size
                screen_pos = camera.world_to_screen(world_x, world_y)

                # Calculate cell rectangle in screen coordinates
                top_left_world = (x * self.cell_size, y * self.cell_size)
                bottom_right_world = ((x + 1) * self.cell_size, (y + 1) * self.cell_size)
                top_left_screen = camera.world_to_screen(*top_left_world)
                bottom_right_screen = camera.world_to_screen(*bottom_right_world)

                cell_rect = pygame.Rect(
                    top_left_screen[0],
                    top_left_screen[1],
                    bottom_right_screen[0] - top_left_screen[0],
                    bottom_right_screen[1] - top_left_screen[1],
                )

                # Render based on cell type
                if cell.cell_type == CellType.GENERATOR:
                    self._render_generator(surface, cell_rect, screen_pos)
                elif cell.cell_type == CellType.CRYSTAL:
                    self._render_crystal(surface, cell_rect, screen_pos)
                elif cell.cell_type == CellType.MYSTERY:
                    self._render_mystery(surface, cell_rect, screen_pos)
                elif cell.cell_type == CellType.START:
                    self._render_start(surface, cell_rect, screen_pos)

    def _render_generator(self, surface: pygame.Surface, rect: pygame.Rect, center: tuple):
        """
        Render a generator cell.

        Args:
            surface: Surface to draw on
            rect: Rectangle of the cell in screen coordinates
            center: Center position in screen coordinates
        """
        # Draw glowing square
        inner_rect = rect.inflate(-rect.width // 3, -rect.height // 3)
        draw_glow_rect(surface, GENERATOR_COLOR, inner_rect, width=2, glow_size=GLOW_INTENSITY)

    def _render_crystal(self, surface: pygame.Surface, rect: pygame.Rect, center: tuple):
        """
        Render the crystal cell.

        Args:
            surface: Surface to draw on
            rect: Rectangle of the cell in screen coordinates
            center: Center position in screen coordinates
        """
        # Draw glowing diamond (rotated square)
        size = min(rect.width, rect.height) // 3
        points = [
            (center[0], center[1] - size),      # Top
            (center[0] + size, center[1]),      # Right
            (center[0], center[1] + size),      # Bottom
            (center[0] - size, center[1]),      # Left
        ]

        # Use vector graphics for glow effect
        from client.ui.vector_graphics import draw_glow_polygon
        draw_glow_polygon(surface, CRYSTAL_COLOR, points, width=0, glow_size=GLOW_INTENSITY + 2)

    def _render_mystery(self, surface: pygame.Surface, rect: pygame.Rect, center: tuple):
        """
        Render a mystery square.

        Args:
            surface: Surface to draw on
            rect: Rectangle of the cell in screen coordinates
            center: Center position in screen coordinates
        """
        # Draw glowing question mark as a circle
        radius = min(rect.width, rect.height) // 4
        draw_glow_circle(surface, MYSTERY_COLOR, center, radius, glow_size=GLOW_INTENSITY)

    def _render_start(self, surface: pygame.Surface, rect: pygame.Rect, center: tuple):
        """
        Render a starting position cell.

        Args:
            surface: Surface to draw on
            rect: Rectangle of the cell in screen coordinates
            center: Center position in screen coordinates
        """
        # Draw subtle square outline
        inner_rect = rect.inflate(-rect.width // 4, -rect.height // 4)
        pygame.draw.rect(surface, START_COLOR, inner_rect, 1)

    def get_cell_at_screen_pos(self, screen_pos: tuple, camera: Camera) -> Optional[tuple]:
        """
        Get the board cell coordinates at a screen position.

        Args:
            screen_pos: (x, y) position on screen
            camera: Camera for coordinate transformation

        Returns:
            (x, y) cell coordinates, or None if outside board
        """
        world_pos = camera.screen_to_world(*screen_pos)
        cell_x = int(world_pos[0] / self.cell_size)
        cell_y = int(world_pos[1] / self.cell_size)

        if 0 <= cell_x < self.board.width and 0 <= cell_y < self.board.height:
            return (cell_x, cell_y)

        return None

    def get_cell_center_world(self, cell_x: int, cell_y: int) -> tuple:
        """
        Get the world coordinates of a cell's center.

        Args:
            cell_x: Cell X coordinate
            cell_y: Cell Y coordinate

        Returns:
            (world_x, world_y) coordinates of cell center
        """
        world_x = (cell_x + 0.5) * self.cell_size
        world_y = (cell_y + 0.5) * self.cell_size
        return (world_x, world_y)
