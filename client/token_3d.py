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

        # Animation state
        # Initialize render position based on token's current position
        self.render_x = self.token.position[0] * CELL_SIZE + CELL_SIZE / 2
        self.render_y = self.token.position[1] * CELL_SIZE + CELL_SIZE / 2
        self.target_x = self.render_x
        self.target_y = self.render_y
        self.is_moving = False

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
        # Create model matrix (translate to interpolated render position)
        world_x = self.render_x
        world_y = self.render_y
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

    def update_position(self, grid_x: int, grid_y: int, instant: bool = False):
        """
        Update token target position.

        Args:
            grid_x: New grid x coordinate
            grid_y: New grid y coordinate
            instant: Whether to move instantly or animate
        """
        self.target_x = grid_x * CELL_SIZE + CELL_SIZE / 2
        self.target_y = grid_y * CELL_SIZE + CELL_SIZE / 2

        if instant:
            self.render_x = self.target_x
            self.render_y = self.target_y
            self.is_moving = False
        else:
            self.is_moving = True

    def update(self, delta_time: float):
        """
        Update animation.

        Args:
            delta_time: Time since last update in seconds
        """
        if not self.is_moving:
            return

        # Move towards target
        dx = self.target_x - self.render_x
        dy = self.target_y - self.render_y

        dist = (dx * dx + dy * dy) ** 0.5

        # Speed matches 2D renderer speed
        speed = (CELL_SIZE * 5.0) * delta_time

        if dist <= speed:
            self.render_x = self.target_x
            self.render_y = self.target_y
            self.is_moving = False
        else:
            self.render_x += (dx / dist) * speed
            self.render_y += (dy / dist) * speed

    def cleanup(self):
        """Release OpenGL resources."""
        if self.vbo:
            self.vbo.release()
        if self.vao:
            self.vao.release()
