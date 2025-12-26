"""
3D Wireframe Board Renderer for Race to the Crystal.

This module renders the game board as vertical wireframe walls in 3D space
with Tron/Battlezone aesthetic and transparent glowing lines.
"""

import arcade
from arcade.gl import BufferDescription
import numpy as np
import math
from pathlib import Path

from game.board import Board
from shared.enums import CellType
from shared.constants import (
    CELL_SIZE,
    BOARD_WIDTH,
    BOARD_HEIGHT,
    WALL_HEIGHT,
)


class Board3D:
    """
    Renders game board as vertical wireframe walls in 3D space.
    Tron/Battlezone aesthetic with transparent glowing lines.
    """

    def __init__(self, board: Board, ctx: arcade.ArcadeContext):
        """
        Initialize the 3D board renderer.

        Args:
            board: Game board instance
            ctx: Arcade OpenGL context
        """
        self.board = board
        self.ctx = ctx

        # Vertex buffers
        self.grid_vbo = None
        self.grid_vao = None
        self.special_cells_vbo = None
        self.special_cells_vao = None

        # Shader program
        self.shader_program = None

        # Grid and wall parameters
        self.wall_height = WALL_HEIGHT
        self.grid_color = np.array(
            [0.0, 0.78, 0.78, 0.7], dtype=np.float32
        )  # Cyan glow

        # Initialize geometry and shaders
        self._create_shader()
        self._create_grid_geometry()
        self._create_special_cells_geometry()

    def _create_shader(self):
        """Create GLSL shader program for glow wireframe effect."""
        shader_path = Path(__file__).parent / "shaders"

        # Load shader source files
        with open(shader_path / "glow_vertex.glsl", "r") as f:
            vertex_shader = f.read()

        with open(shader_path / "glow_fragment.glsl", "r") as f:
            fragment_shader = f.read()

        # Compile shader program with error handling
        try:
            self.shader_program = self.ctx.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )
        except Exception as e:
            print(f"ERROR: Failed to compile 3D shaders: {e}")
            self.shader_program = None

    def _create_grid_geometry(self):
        """
        Generate vertex data for 3D wireframe grid.
        Creates vertical lines at grid intersections and horizontal connectors.
        """
        vertices = []

        # Create vertical lines at each grid intersection
        for x in range(BOARD_WIDTH + 1):
            for y in range(BOARD_HEIGHT + 1):
                world_x = x * CELL_SIZE
                world_y = y * CELL_SIZE

                # Bottom vertex
                vertices.extend([world_x, world_y, 0.0])
                # Top vertex
                vertices.extend([world_x, world_y, self.wall_height])

        # Create horizontal lines at top of walls (connecting vertical lines)
        # Horizontal lines parallel to X axis
        for y in range(BOARD_HEIGHT + 1):
            for x in range(BOARD_WIDTH):
                world_y = y * CELL_SIZE
                x1 = x * CELL_SIZE
                x2 = (x + 1) * CELL_SIZE

                # Line from (x, y, height) to (x+1, y, height)
                vertices.extend([x1, world_y, self.wall_height])
                vertices.extend([x2, world_y, self.wall_height])

        # Horizontal lines parallel to Y axis
        for x in range(BOARD_WIDTH + 1):
            for y in range(BOARD_HEIGHT):
                world_x = x * CELL_SIZE
                y1 = y * CELL_SIZE
                y2 = (y + 1) * CELL_SIZE

                # Line from (x, y, height) to (x, y+1, height)
                vertices.extend([world_x, y1, self.wall_height])
                vertices.extend([world_x, y2, self.wall_height])

        # Convert to numpy array
        vertices_array = np.array(vertices, dtype=np.float32)

        # Create VBO (Vertex Buffer Object)
        self.grid_vbo = self.ctx.buffer(data=vertices_array.tobytes())

        # Create VAO (Vertex Array Object) with position attribute
        self.grid_vao = self.ctx.geometry(
            [
                BufferDescription(
                    self.grid_vbo,
                    "3f",  # 3 floats per vertex (x, y, z)
                    ["in_position"],
                )
            ]
        )

    def _create_special_cells_geometry(self):
        """
        Generate geometry for special cells (generators, crystal, mystery squares).
        Each rendered as 3D wireframe with distinct shape and color.
        """
        vertices = []

        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                cell = self.board.get_cell(x, y)
                if (
                    cell
                    and cell.cell_type != CellType.NORMAL
                    and cell.cell_type != CellType.START
                ):
                    center_x = x * CELL_SIZE + CELL_SIZE / 2
                    center_y = y * CELL_SIZE + CELL_SIZE / 2

                    if cell.cell_type == CellType.GENERATOR:
                        # Generator as wireframe cube
                        vertices.extend(
                            self._create_cube_wireframe(
                                center_x, center_y, CELL_SIZE * 0.6
                            )
                        )

                    elif cell.cell_type == CellType.CRYSTAL:
                        # Crystal as wireframe diamond (pyramid)
                        vertices.extend(
                            self._create_diamond_wireframe(
                                center_x, center_y, CELL_SIZE * 0.5
                            )
                        )

                    elif cell.cell_type == CellType.MYSTERY:
                        # Mystery as wireframe cylinder/circle
                        vertices.extend(
                            self._create_cylinder_wireframe(
                                center_x, center_y, CELL_SIZE * 0.3
                            )
                        )

        if len(vertices) > 0:
            vertices_array = np.array(vertices, dtype=np.float32)
            self.special_cells_vbo = self.ctx.buffer(data=vertices_array.tobytes())
            self.special_cells_vao = self.ctx.geometry(
                [BufferDescription(self.special_cells_vbo, "3f", ["in_position"])]
            )

    def _create_cube_wireframe(
        self, center_x: float, center_y: float, size: float
    ) -> list:
        """Create wireframe cube vertices."""
        half = size / 2
        height = self.wall_height * 0.6  # Cube height

        # 8 vertices of cube
        vertices = [
            (center_x - half, center_y - half, 0.0),  # 0: bottom-front-left
            (center_x + half, center_y - half, 0.0),  # 1: bottom-front-right
            (center_x + half, center_y + half, 0.0),  # 2: bottom-back-right
            (center_x - half, center_y + half, 0.0),  # 3: bottom-back-left
            (center_x - half, center_y - half, height),  # 4: top-front-left
            (center_x + half, center_y - half, height),  # 5: top-front-right
            (center_x + half, center_y + half, height),  # 6: top-back-right
            (center_x - half, center_y + half, height),  # 7: top-back-left
        ]

        # 12 edges of cube (each edge is 2 vertices)
        edges = [
            # Bottom square
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            # Top square
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            # Vertical edges
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]

        # Convert edges to vertex list
        result = []
        for start, end in edges:
            result.extend(vertices[start])
            result.extend(vertices[end])

        return result

    def _create_diamond_wireframe(
        self, center_x: float, center_y: float, size: float
    ) -> list:
        """Create wireframe diamond/pyramid vertices."""
        height = self.wall_height * 0.8

        # 5 vertices: 4 base corners + 1 apex
        vertices = [
            (center_x, center_y, height),  # 0: apex
            (center_x + size, center_y, 0.0),  # 1: base-right
            (center_x, center_y + size, 0.0),  # 2: base-back
            (center_x - size, center_y, 0.0),  # 3: base-left
            (center_x, center_y - size, 0.0),  # 4: base-front
        ]

        # Edges: 4 base edges + 4 edges to apex
        edges = [
            # Base square
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 1),
            # Edges to apex
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
        ]

        result = []
        for start, end in edges:
            result.extend(vertices[start])
            result.extend(vertices[end])

        return result

    def _create_cylinder_wireframe(
        self, center_x: float, center_y: float, radius: float
    ) -> list:
        """Create wireframe cylinder vertices (circle at bottom and top)."""
        segments = 16
        height = self.wall_height * 0.5

        vertices = []

        # Bottom circle
        for i in range(segments):
            angle1 = (i / segments) * 2 * math.pi
            angle2 = ((i + 1) / segments) * 2 * math.pi

            x1 = center_x + radius * math.cos(angle1)
            y1 = center_y + radius * math.sin(angle1)
            x2 = center_x + radius * math.cos(angle2)
            y2 = center_y + radius * math.sin(angle2)

            # Bottom circle edge
            vertices.extend([x1, y1, 0.0])
            vertices.extend([x2, y2, 0.0])

            # Top circle edge
            vertices.extend([x1, y1, height])
            vertices.extend([x2, y2, height])

            # Vertical edge
            vertices.extend([x1, y1, 0.0])
            vertices.extend([x1, y1, height])

        return vertices

    def draw(self, camera_3d):
        """
        Render the 3D wireframe grid and special cells.

        Args:
            camera_3d: FirstPersonCamera3D instance with view/projection matrices
        """
        if self.shader_program is None:
            print("ERROR: 3D shader not compiled, skipping rendering")
            return

        # Note: OpenGL state (blending, depth test) is managed by GameWindow.on_draw

        # Identity model matrix (board is at world origin)
        model_matrix = np.eye(4, dtype=np.float32)

        # Set shader uniforms
        self.shader_program["projection"] = camera_3d.get_projection_matrix().flatten()
        self.shader_program["view"] = camera_3d.get_view_matrix().flatten()
        self.shader_program["model"] = model_matrix.flatten()
        self.shader_program["base_color"] = self.grid_color
        self.shader_program["glow_intensity"] = 1.5

        # Draw grid lines
        self.grid_vao.render(self.shader_program, mode=self.ctx.LINES)

        # Draw special cells if they exist
        if self.special_cells_vao:
            # Generators: orange
            self.shader_program["base_color"] = np.array(
                [1.0, 0.65, 0.0, 0.8], dtype=np.float32
            )
            self.shader_program["glow_intensity"] = 2.0
            # TODO: Separate VAOs for different cell types for different colors
            # For now, draw all special cells with same shader
            self.special_cells_vao.render(self.shader_program, mode=self.ctx.LINES)
