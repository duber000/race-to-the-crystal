"""
Arcade sprite for the game board.

This module creates the visual representation of the game board using
GPU-accelerated shapes.
"""

from arcade.shape_list import (
    ShapeElementList,
    create_line,
)
import math
from game.board import Board
from shared.constants import CELL_SIZE, BOARD_WIDTH, BOARD_HEIGHT
from shared.enums import CellType


def _draw_generator_to_crystal_lines(shape_list: ShapeElementList, generators, crystal_pos):
    """
    Draw animated flowing lines from each active generator to the crystal.
    
    Args:
        shape_list: ShapeElementList to add lines to
        generators: List of Generator objects
        crystal_pos: (x, y) position of the crystal
    """
    crystal_center_x = crystal_pos[0] * CELL_SIZE + CELL_SIZE / 2
    crystal_center_y = crystal_pos[1] * CELL_SIZE + CELL_SIZE / 2
    
    # Use global time for animation (frame counter would work too)
    # We'll use a simple time-based animation
    import time
    time_val = time.time()
    
    for gen in generators:
        # Skip disabled generators
        if gen.is_disabled:
            continue
            
        gen_x = gen.position[0] * CELL_SIZE + CELL_SIZE / 2
        gen_y = gen.position[1] * CELL_SIZE + CELL_SIZE / 2
        
        # Draw multiple flowing segments with pulsing glow
        segments = 12
        segment_length = 1.0 / segments
        
        # Animate flow by offsetting the segments
        flow_offset = (time_val * 2.0) % 1.0  # Flow speed
        
        for i in range(segments):
            # Calculate segment position
            t1 = (i / segments + flow_offset) % 1.0
            t2 = ((i + 1) / segments + flow_offset) % 1.0
            
            # Linear interpolation along the line
            x1 = gen_x + (crystal_center_x - gen_x) * t1
            y1 = gen_y + (crystal_center_y - gen_y) * t1
            x2 = gen_x + (crystal_center_x - gen_x) * t2
            y2 = gen_y + (crystal_center_y - gen_y) * t2
            
            # Calculate brightness based on position (flowing effect)
            brightness = abs(math.sin((t1 + flow_offset) * math.pi)) * 200 + 55
            alpha = int(brightness)
            
            # Draw glow layers for each segment
            for glow_offset in range(2, 0, -1):
                glow_alpha = int(alpha * (0.3 ** glow_offset))
                if glow_alpha > 10:
                    line = create_line(
                        x1, y1, x2, y2,
                        (255, 165, 0, glow_alpha),  # Orange glow
                        glow_offset + 1
                    )
                    shape_list.append(line)
            
            # Main bright segment
            if alpha > 20:
                line = create_line(
                    x1, y1, x2, y2,
                    (255, 200, 0, alpha),  # Bright orange
                    2
                )
                shape_list.append(line)


def create_board_shapes(board: Board, generators=None, crystal_pos=None) -> ShapeElementList:
    """
    Create a shape list for the game board with vector arcade aesthetics.

    Args:
        board: The game board to render
        generators: Optional list of Generator objects for drawing connection lines
        crystal_pos: Optional (x, y) position of crystal for drawing connection lines

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
                x_pos, 0, x_pos, BOARD_HEIGHT * CELL_SIZE, glow_color, offset
            )
            shape_list.append(line)
        # Main bright line
        line = create_line(x_pos, 0, x_pos, BOARD_HEIGHT * CELL_SIZE, grid_color, 2)
        shape_list.append(line)

    # Draw horizontal grid lines with glow
    for y in range(BOARD_HEIGHT + 1):
        y_pos = y * CELL_SIZE
        # Glow effect
        for offset in range(3, 0, -1):
            alpha = int(100 / (offset + 1))
            glow_color = (0, 200, 200, alpha)
            line = create_line(
                0, y_pos, BOARD_WIDTH * CELL_SIZE, y_pos, glow_color, offset
            )
            shape_list.append(line)
        # Main bright line
        line = create_line(0, y_pos, BOARD_WIDTH * CELL_SIZE, y_pos, grid_color, 2)
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
                    # Draw generator as wireframe square with enhanced pulsing glow
                    size = CELL_SIZE * 0.6
                    half = size / 2

                    # Enhanced glow layers (increased from 6 to 10 layers)
                    for i in range(10, 0, -1):
                        alpha = int(150 / (i + 0.5))  # Increased base alpha
                        glow_size = size + (i * 5)  # Larger glow spread
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
                                points[j][0],
                                points[j][1],
                                points[j + 1][0],
                                points[j + 1][1],
                                (255, 165, 0, alpha),
                                max(1, 4 - i // 3),  # Thicker outer glow
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
                            points[j][0],
                            points[j][1],
                            points[j + 1][0],
                            points[j + 1][1],
                            (255, 220, 0, 255),  # Brighter main line
                            4,  # Thicker main line
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
                                points[j][0],
                                points[j][1],
                                points[j + 1][0],
                                points[j + 1][1],
                                (255, 0, 255, alpha),
                                max(1, 4 - i // 2),
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
                            points[j][0],
                            points[j][1],
                            points[j + 1][0],
                            points[j + 1][1],
                            (255, 100, 255, 255),
                            4,
                        )
                        shape_list.append(line)

                    # Draw crossing lines inside for extra detail
                    line = create_line(
                        center_x - size,
                        center_y,
                        center_x + size,
                        center_y,
                        (255, 0, 255, 200),
                        2,
                    )
                    shape_list.append(line)
                    line = create_line(
                        center_x,
                        center_y - size,
                        center_x,
                        center_y + size,
                        (255, 0, 255, 200),
                        2,
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
                                points[j][0],
                                points[j][1],
                                points[j + 1][0],
                                points[j + 1][1],
                                (0, 255, 255, alpha),
                                max(1, 3 - i // 2),
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
                            points[j][0],
                            points[j][1],
                            points[j + 1][0],
                            points[j + 1][1],
                            (100, 255, 255, 255),
                            3,
                        )
                        shape_list.append(line)

                    # Add question mark inside
                    line = create_line(
                        center_x,
                        center_y - radius * 0.3,
                        center_x,
                        center_y + radius * 0.3,
                        (0, 255, 255, 200),
                        2,
                    )
                    shape_list.append(line)

    # Draw flowing lines from active generators to crystal
    if generators and crystal_pos:
        _draw_generator_to_crystal_lines(shape_list, generators, crystal_pos)

    # Draw deployment zone indicators (3x3 corners)
    deployment_zones = [
        (0, 0, 3, 3),      # Top-left (0,0) to (2,2)
        (21, 0, 3, 3),     # Top-right (21,0) to (23,2)
        (0, 21, 3, 3),     # Bottom-left (0,21) to (2,23)
        (21, 21, 3, 3),    # Bottom-right (21,21) to (23,23)
    ]

    for zone_x, zone_y, zone_w, zone_h in deployment_zones:
        # Calculate pixel positions
        x1 = zone_x * CELL_SIZE
        y1 = zone_y * CELL_SIZE
        x2 = (zone_x + zone_w) * CELL_SIZE
        y2 = (zone_y + zone_h) * CELL_SIZE

        # Corner bracket length
        bracket_len = CELL_SIZE * 0.8

        # Deployment zone color: subtle yellow/white glow
        zone_color = (255, 255, 150, 120)  # Semi-transparent yellow
        glow_color = (255, 255, 150, 40)   # Very faint glow

        # Draw glow layers first
        for offset in range(3, 0, -1):
            alpha = int(40 / (offset + 1))
            glow = (255, 255, 150, alpha)

            # Top-left corner brackets
            line = create_line(x1, y1 + bracket_len, x1, y1, glow, offset + 1)
            shape_list.append(line)
            line = create_line(x1, y1, x1 + bracket_len, y1, glow, offset + 1)
            shape_list.append(line)

            # Top-right corner brackets
            line = create_line(x2 - bracket_len, y1, x2, y1, glow, offset + 1)
            shape_list.append(line)
            line = create_line(x2, y1, x2, y1 + bracket_len, glow, offset + 1)
            shape_list.append(line)

            # Bottom-left corner brackets
            line = create_line(x1, y2 - bracket_len, x1, y2, glow, offset + 1)
            shape_list.append(line)
            line = create_line(x1, y2, x1 + bracket_len, y2, glow, offset + 1)
            shape_list.append(line)

            # Bottom-right corner brackets
            line = create_line(x2 - bracket_len, y2, x2, y2, glow, offset + 1)
            shape_list.append(line)
            line = create_line(x2, y2 - bracket_len, x2, y2, glow, offset + 1)
            shape_list.append(line)

        # Draw main bracket lines
        # Top-left corner
        line = create_line(x1, y1 + bracket_len, x1, y1, zone_color, 2)
        shape_list.append(line)
        line = create_line(x1, y1, x1 + bracket_len, y1, zone_color, 2)
        shape_list.append(line)

        # Top-right corner
        line = create_line(x2 - bracket_len, y1, x2, y1, zone_color, 2)
        shape_list.append(line)
        line = create_line(x2, y1, x2, y1 + bracket_len, zone_color, 2)
        shape_list.append(line)

        # Bottom-left corner
        line = create_line(x1, y2 - bracket_len, x1, y2, zone_color, 2)
        shape_list.append(line)
        line = create_line(x1, y2, x1 + bracket_len, y2, zone_color, 2)
        shape_list.append(line)

        # Bottom-right corner
        line = create_line(x2 - bracket_len, y2, x2, y2, zone_color, 2)
        shape_list.append(line)
        line = create_line(x2, y2 - bracket_len, x2, y2, zone_color, 2)
        shape_list.append(line)

    return shape_list
