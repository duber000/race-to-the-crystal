"""
Arcade sprite for the game board.

This module creates the visual representation of the game board using
GPU-accelerated shapes.
"""

import arcade
from arcade.shape_list import (
    ShapeElementList,
    create_line,
    create_rectangle_filled,
    create_polygon,
    create_ellipse_filled
)
from game.board import Board
from shared.constants import CELL_SIZE, BOARD_WIDTH, BOARD_HEIGHT
from shared.enums import CellType


def create_board_shapes(board: Board) -> ShapeElementList:
    """
    Create a shape list for the game board.

    Args:
        board: The game board to render

    Returns:
        ShapeElementList containing all board visual elements
    """
    shape_list = ShapeElementList()

    # Grid lines color (dim cyan)
    grid_color = (0, 100, 100, 100)

    # Draw vertical grid lines
    for x in range(BOARD_WIDTH + 1):
        x_pos = x * CELL_SIZE
        line = create_line(
            x_pos, 0,
            x_pos, BOARD_HEIGHT * CELL_SIZE,
            grid_color, 1
        )
        shape_list.append(line)

    # Draw horizontal grid lines
    for y in range(BOARD_HEIGHT + 1):
        y_pos = y * CELL_SIZE
        line = create_line(
            0, y_pos,
            BOARD_WIDTH * CELL_SIZE, y_pos,
            grid_color, 1
        )
        shape_list.append(line)

    # Draw special cells
    for y in range(BOARD_HEIGHT):
        for x in range(BOARD_WIDTH):
            cell = board.get_cell(x, y)
            if cell:
                cell_type = cell.cell_type
                center_x = x * CELL_SIZE + CELL_SIZE // 2
                center_y = y * CELL_SIZE + CELL_SIZE // 2

                if cell_type == CellType.GENERATOR:
                    # Draw generator as glowing square
                    color = (255, 165, 0, 150)  # Orange glow
                    rect = create_rectangle_filled(
                        center_x, center_y,
                        CELL_SIZE * 0.6, CELL_SIZE * 0.6,
                        color
                    )
                    shape_list.append(rect)

                elif cell_type == CellType.CRYSTAL:
                    # Draw crystal as glowing diamond
                    color = (255, 0, 255, 200)  # Magenta glow
                    points = [
                        (center_x, center_y + CELL_SIZE * 0.4),  # Top
                        (center_x + CELL_SIZE * 0.4, center_y),  # Right
                        (center_x, center_y - CELL_SIZE * 0.4),  # Bottom
                        (center_x - CELL_SIZE * 0.4, center_y),  # Left
                    ]
                    diamond = create_polygon(points, color)
                    shape_list.append(diamond)

                elif cell_type == CellType.MYSTERY:
                    # Draw mystery square as glowing circle
                    color = (0, 255, 255, 100)  # Cyan glow
                    circle = create_ellipse_filled(
                        center_x, center_y,
                        CELL_SIZE * 0.3, CELL_SIZE * 0.3,
                        color
                    )
                    shape_list.append(circle)

    return shape_list
