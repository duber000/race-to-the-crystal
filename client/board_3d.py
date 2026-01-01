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

    def __init__(self, board: Board, ctx: arcade.ArcadeContext, generators=None, crystal_pos=None):
        """
        Initialize the 3D board renderer.

        Args:
            board: Game board instance
            ctx: Arcade OpenGL context
            generators: Optional list of Generator objects for connection lines
            crystal_pos: Optional (x, y) position of crystal
        """
        self.board = board
        self.ctx = ctx
        self.generators = generators
        self.crystal_pos = crystal_pos

        # Vertex buffers
        self.grid_vbo = None
        self.grid_vao = None
        
        # Special cell VAOs (separate for each type with different colors)
        self.generators_vao = None
        self.generators_vbo = None
        self.crystal_vao = None
        self.crystal_vbo = None
        self.mystery_vao = None
        self.mystery_vbo = None
        
        # Generator to crystal lines VAO
        self.gen_crystal_lines_vao = None
        self.gen_crystal_lines_vbo = None

        # Deployment zones VAO (3x3 corner areas)
        self.deployment_zones_vao = None
        self.deployment_zones_vbo = None

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
        self._create_generator_crystal_lines_geometry()
        self._create_deployment_zones_geometry()

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

    def _create_generator_crystal_lines_geometry(self):
        """
        Generate geometry for flowing lines from generators to crystal.
        These lines are animated and only drawn for active (non-disabled) generators.
        """
        # Release old buffers if they exist to prevent memory leaks and buffer copy warnings
        # Note: Arcade handles cleanup via garbage collection when references are cleared
        self.gen_crystal_lines_vbo = None
        self.gen_crystal_lines_vao = None

        if not self.generators or not self.crystal_pos:
            return

        vertices = []

        # Get crystal position in world coordinates
        crystal_center_x = self.crystal_pos[0] * CELL_SIZE + CELL_SIZE / 2
        crystal_center_y = self.crystal_pos[1] * CELL_SIZE + CELL_SIZE / 2
        crystal_height = self.wall_height * 0.8

        for gen in self.generators:
            # Skip disabled generators
            if gen.is_disabled:
                continue

            # Get generator position
            gen_x = gen.position[0] * CELL_SIZE + CELL_SIZE / 2
            gen_y = gen.position[1] * CELL_SIZE + CELL_SIZE / 2
            gen_height = self.wall_height * 0.6

            # Create line segments from generator to crystal
            segments = 20
            for i in range(segments):
                t1 = i / segments
                t2 = (i + 1) / segments

                # Linear interpolation
                x1 = gen_x + (crystal_center_x - gen_x) * t1
                y1 = gen_y + (crystal_center_y - gen_y) * t1
                z1 = gen_height + (crystal_height - gen_height) * t1

                x2 = gen_x + (crystal_center_x - gen_x) * t2
                y2 = gen_y + (crystal_center_y - gen_y) * t2
                z2 = gen_height + (crystal_height - gen_height) * t2

                # Add vertices for line segment
                vertices.extend([x1, y1, z1])
                vertices.extend([x2, y2, z2])

        if len(vertices) > 0:
            vertices_array = np.array(vertices, dtype=np.float32)
            self.gen_crystal_lines_vbo = self.ctx.buffer(data=vertices_array.tobytes())
            self.gen_crystal_lines_vao = self.ctx.geometry(
                [BufferDescription(self.gen_crystal_lines_vbo, "3f", ["in_position"])]
            )

    def update_generator_lines(self):
        """
        Update generator-to-crystal connection lines.
        Call this when generator status changes (e.g., when disabled).
        """
        self._create_generator_crystal_lines_geometry()

    def _create_special_cells_geometry(self):
        """
        Generate geometry for special cells (generators, crystal, mystery squares).
        Each rendered as 3D wireframe with distinct shape and color.
        Creates separate VAOs for each type to allow different colors.
        """
        # Collect vertices by cell type
        generator_vertices = []
        crystal_vertices = []
        mystery_vertices = []

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
                        # Generator as wireframe cube (orange)
                        generator_vertices.extend(
                            self._create_cube_wireframe(
                                center_x, center_y, CELL_SIZE * 0.6
                            )
                        )

                    elif cell.cell_type == CellType.CRYSTAL:
                        # Crystal as wireframe diamond (magenta)
                        crystal_vertices.extend(
                            self._create_diamond_wireframe(
                                center_x, center_y, CELL_SIZE * 0.5
                            )
                        )

                    elif cell.cell_type == CellType.MYSTERY:
                        # Mystery as wireframe cylinder (cyan)
                        mystery_vertices.extend(
                            self._create_cylinder_wireframe(
                                center_x, center_y, CELL_SIZE * 0.3
                            )
                        )

        # Create separate VAOs for each type
        if len(generator_vertices) > 0:
            vertices_array = np.array(generator_vertices, dtype=np.float32)
            self.generators_vbo = self.ctx.buffer(data=vertices_array.tobytes())
            self.generators_vao = self.ctx.geometry(
                [BufferDescription(self.generators_vbo, "3f", ["in_position"])]
            )

        if len(crystal_vertices) > 0:
            vertices_array = np.array(crystal_vertices, dtype=np.float32)
            self.crystal_vbo = self.ctx.buffer(data=vertices_array.tobytes())
            self.crystal_vao = self.ctx.geometry(
                [BufferDescription(self.crystal_vbo, "3f", ["in_position"])]
            )

        if len(mystery_vertices) > 0:
            vertices_array = np.array(mystery_vertices, dtype=np.float32)
            self.mystery_vbo = self.ctx.buffer(data=vertices_array.tobytes())
            self.mystery_vao = self.ctx.geometry(
                [BufferDescription(self.mystery_vbo, "3f", ["in_position"])]
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

    def _create_deployment_zones_geometry(self):
        """
        Generate geometry for deployment zone indicators (3x3 corner areas).
        Creates corner bracket wireframes to mark where tokens can be deployed.
        """
        vertices = []

        # Define 3x3 deployment zones for each corner
        deployment_zones = [
            (0, 0, 3, 3),      # Top-left (0,0) to (2,2)
            (21, 0, 3, 3),     # Top-right (21,0) to (23,2)
            (0, 21, 3, 3),     # Bottom-left (0,21) to (2,23)
            (21, 21, 3, 3),    # Bottom-right (21,21) to (23,23)
        ]

        bracket_height = self.wall_height * 0.3  # Bracket height in 3D
        bracket_len_cells = 0.8  # Length in cells

        for zone_x, zone_y, zone_w, zone_h in deployment_zones:
            # Calculate pixel positions for the zone boundaries
            x1 = zone_x * CELL_SIZE
            y1 = zone_y * CELL_SIZE
            x2 = (zone_x + zone_w) * CELL_SIZE
            y2 = (zone_y + zone_h) * CELL_SIZE

            bracket_len = CELL_SIZE * bracket_len_cells

            # Create 3D corner brackets at each corner of the deployment zone
            # Each bracket is an L-shape in 3D space

            # Top-left corner bracket
            # Vertical line
            vertices.extend([x1, y1, 0.0])
            vertices.extend([x1, y1, bracket_height])
            vertices.extend([x1, y1, bracket_height])
            vertices.extend([x1, y1 + bracket_len, bracket_height])
            # Horizontal line
            vertices.extend([x1, y1, bracket_height])
            vertices.extend([x1 + bracket_len, y1, bracket_height])

            # Top-right corner bracket
            # Vertical line
            vertices.extend([x2, y1, 0.0])
            vertices.extend([x2, y1, bracket_height])
            vertices.extend([x2, y1, bracket_height])
            vertices.extend([x2, y1 + bracket_len, bracket_height])
            # Horizontal line
            vertices.extend([x2, y1, bracket_height])
            vertices.extend([x2 - bracket_len, y1, bracket_height])

            # Bottom-left corner bracket
            # Vertical line
            vertices.extend([x1, y2, 0.0])
            vertices.extend([x1, y2, bracket_height])
            vertices.extend([x1, y2, bracket_height])
            vertices.extend([x1, y2 - bracket_len, bracket_height])
            # Horizontal line
            vertices.extend([x1, y2, bracket_height])
            vertices.extend([x1 + bracket_len, y2, bracket_height])

            # Bottom-right corner bracket
            # Vertical line
            vertices.extend([x2, y2, 0.0])
            vertices.extend([x2, y2, bracket_height])
            vertices.extend([x2, y2, bracket_height])
            vertices.extend([x2, y2 - bracket_len, bracket_height])
            # Horizontal line
            vertices.extend([x2, y2, bracket_height])
            vertices.extend([x2 - bracket_len, y2, bracket_height])

        if len(vertices) > 0:
            vertices_array = np.array(vertices, dtype=np.float32)
            self.deployment_zones_vbo = self.ctx.buffer(data=vertices_array.tobytes())
            self.deployment_zones_vao = self.ctx.geometry(
                [BufferDescription(self.deployment_zones_vbo, "3f", ["in_position"])]
            )

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

        # Set common shader uniforms (transpose for OpenGL column-major format)
        self.shader_program["projection"] = camera_3d.get_projection_matrix().T.flatten()
        self.shader_program["view"] = camera_3d.get_view_matrix().T.flatten()
        self.shader_program["model"] = model_matrix.T.flatten()

        # Draw grid lines (cyan)
        self.shader_program["base_color"] = self.grid_color
        self.shader_program["glow_intensity"] = 1.5
        self.grid_vao.render(self.shader_program, mode=self.ctx.LINES)

        # Draw generators (orange cubes)
        if self.generators_vao:
            self.shader_program["base_color"] = np.array(
                [1.0, 0.65, 0.0, 0.8], dtype=np.float32
            )
            self.shader_program["glow_intensity"] = 2.0
            self.generators_vao.render(self.shader_program, mode=self.ctx.LINES)

        # Draw crystal (magenta diamond)
        if self.crystal_vao:
            self.shader_program["base_color"] = np.array(
                [1.0, 0.0, 1.0, 0.9], dtype=np.float32
            )
            self.shader_program["glow_intensity"] = 2.5
            self.crystal_vao.render(self.shader_program, mode=self.ctx.LINES)

        # Draw mystery squares (cyan cylinders)
        if self.mystery_vao:
            self.shader_program["base_color"] = np.array(
                [0.0, 1.0, 1.0, 0.7], dtype=np.float32
            )
            self.shader_program["glow_intensity"] = 1.8
            self.mystery_vao.render(self.shader_program, mode=self.ctx.LINES)
        
        # Draw generator to crystal connection lines (orange with glow)
        if self.gen_crystal_lines_vao:
            self.shader_program["base_color"] = np.array(
                [1.0, 0.65, 0.0, 0.9], dtype=np.float32
            )
            self.shader_program["glow_intensity"] = 2.2
            self.gen_crystal_lines_vao.render(self.shader_program, mode=self.ctx.LINES)

        # Draw deployment zone indicators (yellow/white brackets)
        if self.deployment_zones_vao:
            self.shader_program["base_color"] = np.array(
                [1.0, 1.0, 0.6, 0.5], dtype=np.float32  # Subtle yellow/white
            )
            self.shader_program["glow_intensity"] = 1.2
            self.deployment_zones_vao.render(self.shader_program, mode=self.ctx.LINES)

    def cleanup(self):
        """Release all OpenGL resources to prevent memory leaks."""
        # Clear all buffer references - Arcade handles cleanup via garbage collection
        self.grid_vbo = None
        self.grid_vao = None
        self.generators_vbo = None
        self.generators_vao = None
        self.crystal_vbo = None
        self.crystal_vao = None
        self.mystery_vbo = None
        self.mystery_vao = None
        self.gen_crystal_lines_vbo = None
        self.gen_crystal_lines_vao = None
        self.deployment_zones_vbo = None
        self.deployment_zones_vao = None
