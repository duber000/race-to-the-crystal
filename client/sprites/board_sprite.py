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
    Create a shape list for the game board with vector arcade aesthetics.

    Args:
        board: The game board to render

    Returns:
        ShapeElementList containing all board visual elements
    """
    shape_list = ShapeElementList()

    # Bright neon grid lines for vector arcade look
    grid_color = (0, 200, 200, 180)  # Brighter cyan with transparency

    # Draw vertical grid lines with glow
    for x in range(BOARD_WIDTH + 1):
        x_pos = x * CELL_SIZE
        # Glow effect - draw multiple overlapping lines
        for offset in range(3, 0, -1):
            alpha = int(100 / (offset + 1))
            glow_color = (0, 200, 200, alpha)
            line = create_line(
                x_pos, 0,
                x_pos, BOARD_HEIGHT * CELL_SIZE,
                glow_color, offset
            )
            shape_list.append(line)
        # Main bright line
        line = create_line(
            x_pos, 0,
            x_pos, BOARD_HEIGHT * CELL_SIZE,
            grid_color, 2
        )
        shape_list.append(line)

    # Draw horizontal grid lines with glow
    for y in range(BOARD_HEIGHT + 1):
        y_pos = y * CELL_SIZE
        # Glow effect
        for offset in range(3, 0, -1):
            alpha = int(100 / (offset + 1))
            glow_color = (0, 200, 200, alpha)
            line = create_line(
                0, y_pos,
                BOARD_WIDTH * CELL_SIZE, y_pos,
                glow_color, offset
            )
            shape_list.append(line)
        # Main bright line
        line = create_line(
            0, y_pos,
            BOARD_WIDTH * CELL_SIZE, y_pos,
            grid_color, 2
        )
        shape_list.append(line)

    # Draw special cells with wireframe vector graphics
    for y in range(BOARD_HEIGHT):
        for x in range(BOARD_WIDTH):
            cell = board.get_cell(x, y)
            if cell:
                cell_type = cell.cell_type
                center_x = x * CELL_SIZE + CELL_SIZE // 2
                center_y = y * CELL_SIZE + CELL_SIZE // 2

                if cell_type == CellType.GENERATOR:
                    # Draw generator as wireframe square with pulsing glow
                    size = CELL_SIZE * 0.6
                    half = size / 2

                    # Glow layers
                    for i in range(6, 0, -1):
                        alpha = int(120 / (i + 1))
                        glow_size = size + (i * 4)
                        glow_half = glow_size / 2
                        points = [
                            (center_x - glow_half, center_y - glow_half),
                            (center_x + glow_half, center_y - glow_half),
                            (center_x + glow_half, center_y + glow_half),
                            (center_x - glow_half, center_y + glow_half),
                            (center_x - glow_half, center_y - glow_half),
                        ]
                        for j in range(len(points) - 1):
                            line = create_line(
                                points[j][0], points[j][1],
                                points[j + 1][0], points[j + 1][1],
                                (255, 165, 0, alpha), max(1, 3 - i // 2)
                            )
                            shape_list.append(line)

                    # Bright main square
                    points = [
                        (center_x - half, center_y - half),
                        (center_x + half, center_y - half),
                        (center_x + half, center_y + half),
                        (center_x - half, center_y + half),
                        (center_x - half, center_y - half),
                    ]
                    for j in range(len(points) - 1):
                        line = create_line(
                            points[j][0], points[j][1],
                            points[j + 1][0], points[j + 1][1],
                            (255, 200, 0, 255), 3
                        )
                        shape_list.append(line)

                elif cell_type == CellType.CRYSTAL:
                    # Draw crystal as wireframe diamond with intense glow
                    size = CELL_SIZE * 0.5

                    # Multiple glow layers for intense effect
                    for i in range(8, 0, -1):
                        alpha = int(150 / (i + 1))
                        glow_size = size + (i * 3)
                        points = [
                            (center_x, center_y + glow_size),  # Top
                            (center_x + glow_size, center_y),  # Right
                            (center_x, center_y - glow_size),  # Bottom
                            (center_x - glow_size, center_y),  # Left
                            (center_x, center_y + glow_size),  # Close
                        ]
                        for j in range(len(points) - 1):
                            line = create_line(
                                points[j][0], points[j][1],
                                points[j + 1][0], points[j + 1][1],
                                (255, 0, 255, alpha), max(1, 4 - i // 2)
                            )
                            shape_list.append(line)

                    # Bright main diamond
                    points = [
                        (center_x, center_y + size),
                        (center_x + size, center_y),
                        (center_x, center_y - size),
                        (center_x - size, center_y),
                        (center_x, center_y + size),
                    ]
                    for j in range(len(points) - 1):
                        line = create_line(
                            points[j][0], points[j][1],
                            points[j + 1][0], points[j + 1][1],
                            (255, 100, 255, 255), 4
                        )
                        shape_list.append(line)

                    # Draw crossing lines inside for extra detail
                    line = create_line(
                        center_x - size, center_y,
                        center_x + size, center_y,
                        (255, 0, 255, 200), 2
                    )
                    shape_list.append(line)
                    line = create_line(
                        center_x, center_y - size,
                        center_x, center_y + size,
                        (255, 0, 255, 200), 2
                    )
                    shape_list.append(line)

                elif cell_type == CellType.MYSTERY:
                    # Draw mystery as wireframe circle with cyan glow
                    import math
                    radius = CELL_SIZE * 0.3
                    segments = 16  # Circle segments

                    # Glow layers
                    for i in range(5, 0, -1):
                        alpha = int(100 / (i + 1))
                        glow_radius = radius + (i * 3)
                        points = []
                        for seg in range(segments + 1):
                            angle = (seg / segments) * 2 * math.pi
                            px = center_x + glow_radius * math.cos(angle)
                            py = center_y + glow_radius * math.sin(angle)
                            points.append((px, py))

                        for j in range(len(points) - 1):
                            line = create_line(
                                points[j][0], points[j][1],
                                points[j + 1][0], points[j + 1][1],
                                (0, 255, 255, alpha), max(1, 3 - i // 2)
                            )
                            shape_list.append(line)

                    # Bright main circle
                    points = []
                    for seg in range(segments + 1):
                        angle = (seg / segments) * 2 * math.pi
                        px = center_x + radius * math.cos(angle)
                        py = center_y + radius * math.sin(angle)
                        points.append((px, py))

                    for j in range(len(points) - 1):
                        line = create_line(
                            points[j][0], points[j][1],
                            points[j + 1][0], points[j + 1][1],
                            (100, 255, 255, 255), 3
                        )
                        shape_list.append(line)

                    # Add question mark inside
                    line = create_line(
                        center_x, center_y - radius * 0.3,
                        center_x, center_y + radius * 0.3,
                        (0, 255, 255, 200), 2
                    )
                    shape_list.append(line)

    return shape_list
