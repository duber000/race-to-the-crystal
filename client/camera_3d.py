"""
First-person 3D perspective camera for Race to the Crystal.

This module implements a 3D camera system that follows tokens from a first-person
perspective, with support for ray casting (mouse picking) in 3D space.
"""

import numpy as np
from typing import Tuple
from shared.constants import (
    CELL_SIZE,
    CAMERA_FOV,
    CAMERA_NEAR_PLANE,
    CAMERA_FAR_PLANE,
    CAMERA_HEIGHT_ABOVE_TOKEN,
    CAMERA_FORWARD_OFFSET,
)


class FirstPersonCamera3D:
    """
    First-person perspective camera for 3D board viewing.
    Follows a selected token's position and orientation.
    """

    def __init__(self, window_width: int, window_height: int):
        """
        Initialize the 3D camera.

        Args:
            window_width: Window width in pixels
            window_height: Window height in pixels
        """
        # Perspective projection parameters
        self.fov = CAMERA_FOV  # Field of view in degrees
        self.near = CAMERA_NEAR_PLANE  # Near clipping plane
        self.far = CAMERA_FAR_PLANE  # Far clipping plane
        self.aspect_ratio = window_width / window_height

        # Camera position (world coordinates, in pixels)
        # Start above board center for initial overview
        self.position = np.array(
            [12 * CELL_SIZE, 12 * CELL_SIZE, 150.0], dtype=np.float32
        )

        # Camera orientation (Euler angles in degrees)
        self.yaw = 0.0  # Rotation around Z axis (left/right look)
        self.pitch = -60.0  # Rotation around X axis (up/down look, negative = down, steep for overview)
        self.roll = 0.0  # Rotation around Y axis (tilt)

        # Movement parameters
        self.height_above_token = CAMERA_HEIGHT_ABOVE_TOKEN
        self.forward_offset = CAMERA_FORWARD_OFFSET

        # Following state
        self.following_token_id = None

    def update_aspect_ratio(self, width: int, height: int):
        """
        Update aspect ratio when window is resized.

        Args:
            width: New window width
            height: New window height
        """
        self.aspect_ratio = width / height

    def get_projection_matrix(self) -> np.ndarray:
        """
        Compute perspective projection matrix.

        Returns:
            4x4 projection matrix as numpy array
        """
        fov_rad = np.radians(self.fov)
        f = 1.0 / np.tan(fov_rad / 2.0)

        # Standard perspective projection matrix
        projection = np.array(
            [
                [f / self.aspect_ratio, 0, 0, 0],
                [0, f, 0, 0],
                [0, 0, (self.far + self.near) / (self.near - self.far), -1],
                [0, 0, (2 * self.far * self.near) / (self.near - self.far), 0],
            ],
            dtype=np.float32,
        )

        return projection

    def get_view_matrix(self) -> np.ndarray:
        """
        Compute view matrix from camera position and orientation.

        Returns:
            4x4 view matrix for transforming world to camera space
        """
        # Convert angles to radians
        yaw_rad = np.radians(self.yaw)
        pitch_rad = np.radians(self.pitch)
        roll_rad = np.radians(self.roll)

        # Calculate forward, right, and up vectors
        forward = np.array(
            [
                np.cos(pitch_rad) * np.cos(yaw_rad),
                np.cos(pitch_rad) * np.sin(yaw_rad),
                np.sin(pitch_rad),
            ],
            dtype=np.float32,
        )

        # World up vector
        world_up = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        # Right vector (cross product of forward and world_up)
        right = np.cross(forward, world_up)
        right = right / np.linalg.norm(right)

        # Recalculate up vector
        up = np.cross(right, forward)

        # Apply roll rotation
        if abs(self.roll) > 0.001:
            cos_roll = np.cos(roll_rad)
            sin_roll = np.sin(roll_rad)
            right_rolled = right * cos_roll + up * sin_roll
            up = -right * sin_roll + up * cos_roll
            right = right_rolled

        # Create view matrix (look-at matrix)
        view = np.eye(4, dtype=np.float32)

        # Rotation part
        view[0, :3] = right
        view[1, :3] = up
        view[2, :3] = -forward  # Negative because we look down -Z in OpenGL

        # Translation part
        view[0, 3] = -np.dot(right, self.position)
        view[1, 3] = -np.dot(up, self.position)
        view[2, 3] = np.dot(forward, self.position)

        return view

    def follow_token(
        self, token_position: Tuple[int, int], token_rotation: float = 0.0
    ):
        """
        Position camera to follow a token in first-person view.

        Args:
            token_position: Grid position (x, y) of token
            token_rotation: Direction token is facing (degrees), 0 = right, 90 = up
        """
        # Convert grid position to world coordinates (center of cell)
        world_x = token_position[0] * CELL_SIZE + CELL_SIZE / 2
        world_y = token_position[1] * CELL_SIZE + CELL_SIZE / 2

        # Calculate camera position relative to token
        # Eye is behind and above token
        self.yaw = token_rotation

        # Calculate offset in the direction opposite to where token faces
        offset_angle = np.radians(token_rotation + 180)  # Behind the token
        offset_x = self.forward_offset * np.cos(offset_angle)
        offset_y = self.forward_offset * np.sin(offset_angle)

        self.position[0] = world_x + offset_x
        self.position[1] = world_y + offset_y
        self.position[2] = self.height_above_token

    def rotate(
        self, yaw_delta: float = 0.0, pitch_delta: float = 0.0, roll_delta: float = 0.0
    ):
        """
        Rotate the camera by given deltas.

        Args:
            yaw_delta: Change in yaw (degrees)
            pitch_delta: Change in pitch (degrees)
            roll_delta: Change in roll (degrees)
        """
        self.yaw += yaw_delta
        self.pitch += pitch_delta
        self.roll += roll_delta

        # Clamp pitch to avoid gimbal lock
        self.pitch = max(-89.0, min(89.0, self.pitch))

        # Keep yaw in [0, 360)
        self.yaw = self.yaw % 360.0

    def screen_to_ray(
        self, screen_x: int, screen_y: int, window_width: int, window_height: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert screen coordinates to 3D ray in world space for mouse picking.

        Args:
            screen_x: Mouse x position on screen
            screen_y: Mouse y position on screen
            window_width: Window width in pixels
            window_height: Window height in pixels

        Returns:
            Tuple of (ray_origin, ray_direction) as 3D numpy arrays
        """
        # Normalize device coordinates (-1 to 1)
        ndc_x = (2.0 * screen_x) / window_width - 1.0
        ndc_y = 1.0 - (2.0 * screen_y) / window_height  # Flip Y

        # Clip space coordinates (homogeneous)
        clip_coords = np.array([ndc_x, ndc_y, -1.0, 1.0], dtype=np.float32)

        # Eye/camera space
        inv_projection = np.linalg.inv(self.get_projection_matrix())
        eye_coords = inv_projection @ clip_coords
        eye_coords = np.array(
            [eye_coords[0], eye_coords[1], -1.0, 0.0], dtype=np.float32
        )

        # World space
        inv_view = np.linalg.inv(self.get_view_matrix())
        world_coords = inv_view @ eye_coords

        # Normalize ray direction
        ray_direction = world_coords[:3]
        ray_direction = ray_direction / np.linalg.norm(ray_direction)

        ray_origin = self.position.copy()

        return ray_origin, ray_direction

    def ray_intersect_plane(
        self, ray_origin: np.ndarray, ray_direction: np.ndarray, plane_z: float = 0.0
    ) -> Tuple[float, float]:
        """
        Find intersection of ray with horizontal plane (board surface).

        Args:
            ray_origin: 3D ray origin point
            ray_direction: 3D ray direction vector (normalized)
            plane_z: Z-coordinate of the plane (default: 0 for board surface)

        Returns:
            Tuple of (x, y) world coordinates of intersection, or None if no intersection
        """
        # Plane equation: z = plane_z (horizontal board at z=0)
        # Ray equation: P = origin + t * direction
        # Solve for t where ray.z = plane_z

        # Check if ray is parallel to plane (direction.z ≈ 0)
        if abs(ray_direction[2]) < 0.0001:
            return None  # Ray is parallel, no intersection

        # Calculate parameter t
        t = (plane_z - ray_origin[2]) / ray_direction[2]

        # Check if intersection is behind the ray origin
        if t < 0:
            return None  # Intersection is behind camera

        # Calculate intersection point
        intersect_x = ray_origin[0] + t * ray_direction[0]
        intersect_y = ray_origin[1] + t * ray_direction[1]

        return intersect_x, intersect_y

    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """
        Convert world coordinates to grid coordinates.

        Args:
            world_x: World X coordinate
            world_y: World Y coordinate

        Returns:
            Tuple of (grid_x, grid_y)
        """
        grid_x = int(world_x // CELL_SIZE)
        grid_y = int(world_y // CELL_SIZE)
        return grid_x, grid_y
