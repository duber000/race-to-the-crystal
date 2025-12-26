"""
3D Token Renderer for Race to the Crystal.

This module renders game tokens as 3D hexagonal prism wireframes
with player colors and glow effects.
"""

import arcade
from arcade.gl import BufferDescription
import numpy as np
import math

from game.token import Token
from shared.constants import CELL_SIZE, TOKEN_HEIGHT_3D


class Token3D:
    """
    3D representation of a game token.
    Rendered as 3D hexagonal prism wireframe with glow.
    """

    def __init__(self, token: Token, player_color: tuple, ctx: arcade.ArcadeContext):
        """
        Initialize 3D token renderer.

        Args:
            token: Game token instance
            player_color: RGB color tuple for player
            ctx: Arcade OpenGL context
        """
        self.token = token
        self.color = np.array(
            [
                player_color[0] / 255.0,
                player_color[1] / 255.0,
                player_color[2] / 255.0,
                0.9,  # Alpha
            ],
            dtype=np.float32,
        )
        self.ctx = ctx

        # 3D geometry parameters
        self.radius = CELL_SIZE * 0.45
        self.height = TOKEN_HEIGHT_3D

        # Buffers
        self.vbo = None
        self.vao = None

        self._create_hexagon_prism()

    def _create_hexagon_prism(self):
        """
        Create 3D hexagonal prism wireframe.
        12 vertical edges (6 per hexagon) + 12 horizontal edges (6 bottom + 6 top).
        """
        vertices = []

        # Generate hexagon points (6 vertices for bottom, 6 for top)
        bottom_hexagon = []
        top_hexagon = []

        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2  # Start from top
            x = self.radius * math.cos(angle)
            y = self.radius * math.sin(angle)

            bottom_hexagon.append((x, y, 0.0))
            top_hexagon.append((x, y, self.height))

        # Bottom hexagon edges (6 edges)
        for i in range(6):
            next_i = (i + 1) % 6
            vertices.extend(bottom_hexagon[i])
            vertices.extend(bottom_hexagon[next_i])

        # Top hexagon edges (6 edges)
        for i in range(6):
            next_i = (i + 1) % 6
            vertices.extend(top_hexagon[i])
            vertices.extend(top_hexagon[next_i])

        # Vertical edges connecting bottom to top (6 edges)
        for i in range(6):
            vertices.extend(bottom_hexagon[i])
            vertices.extend(top_hexagon[i])

        # Convert to numpy array
        vertices_array = np.array(vertices, dtype=np.float32)

        # Create VBO
        self.vbo = self.ctx.buffer(data=vertices_array.tobytes())

        # Create VAO with position attribute
        self.vao = self.ctx.geometry(
            [
                BufferDescription(
                    self.vbo,
                    "3f",  # 3 floats per vertex (x, y, z)
                    ["in_position"],
                )
            ]
        )

    def draw(self, camera_3d, shader_program):
        """
        Draw token at its world position.

        Args:
            camera_3d: FirstPersonCamera3D instance
            shader_program: Compiled shader program
        """
        # Create model matrix (translate to token position)
        world_x = self.token.position[0] * CELL_SIZE + CELL_SIZE / 2
        world_y = self.token.position[1] * CELL_SIZE + CELL_SIZE / 2
        world_z = 0.0  # Tokens sit on the board surface

        # Translation matrix
        model_matrix = np.eye(4, dtype=np.float32)
        model_matrix[0, 3] = world_x
        model_matrix[1, 3] = world_y
        model_matrix[2, 3] = world_z

        # Set shader uniforms (transpose for OpenGL column-major format)
        shader_program["projection"] = camera_3d.get_projection_matrix().T.flatten()
        shader_program["view"] = camera_3d.get_view_matrix().T.flatten()
        shader_program["model"] = model_matrix.T.flatten()
        shader_program["base_color"] = self.color
        shader_program["glow_intensity"] = 2.5  # Brighter glow for tokens

        # Render as lines
        self.vao.render(shader_program, mode=self.ctx.LINES)

    def update_position(self, new_position: tuple):
        """
        Update token position (no need to recreate geometry).

        Args:
            new_position: New (x, y) grid position
        """
        # Position is read from self.token.position during draw()
        # So just update the token's position
        pass  # No action needed, position is read dynamically

    def cleanup(self):
        """Release OpenGL resources."""
        if self.vbo:
            self.vbo.release()
        if self.vao:
            self.vao.release()
