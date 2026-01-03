"""
Camera controller for Race to the Crystal.

This module handles all camera management including 2D and 3D camera systems,
camera mode switching, panning, zooming, and token following.
"""

from typing import Optional, Tuple

import arcade

from client.camera_3d import FirstPersonCamera3D
from shared.constants import (
    BOARD_HEIGHT,
    BOARD_WIDTH,
    CAMERA_INITIAL_ZOOM,
    CAMERA_PAN_SPEED,
    CAMERA_ROTATION_INCREMENT,
    CELL_SIZE,
    HUD_HEIGHT,
    MOUSE_LOOK_SENSITIVITY,
)
from shared.logging_config import setup_logger

logger = setup_logger(__name__)


class CameraController:
    """
    Manages all camera systems for the game.

    The CameraController handles:
    - 2D camera (orthographic top-down view)
    - 3D camera (first-person perspective view)
    - Camera mode switching between 2D and 3D
    - Panning and zooming in 2D
    - Token following in 3D mode
    - Mouse-look rotation in 3D mode
    - Camera rotation controls (Q/E keys)
    """

    def __init__(self, window_width: int, window_height: int, start_in_3d: bool = False):
        """
        Initialize camera controller.

        Args:
            window_width: Window width in pixels
            window_height: Window height in pixels
            start_in_3d: Whether to start in 3D mode
        """
        # 2D Camera system
        self.camera_2d = arcade.camera.Camera2D()
        self.ui_camera = arcade.camera.Camera2D()
        self.zoom_level = CAMERA_INITIAL_ZOOM
        self.camera_speed = CAMERA_PAN_SPEED

        # 3D Camera system
        self.camera_3d = FirstPersonCamera3D(window_width, window_height)
        self.controlled_token_id: Optional[int] = None  # Token camera follows in 3D
        self.token_rotation = 0.0  # Camera rotation around token

        # Camera mode
        self.camera_mode = "3D" if start_in_3d else "2D"

        # Mouse-look state for 3D mode
        self.mouse_look_active = False
        self.mouse_look_sensitivity = MOUSE_LOOK_SENSITIVITY
        self.last_mouse_position = (0, 0)

    def setup_initial_view(self, window_width: int, window_height: int) -> None:
        """
        Set up camera to show the entire board, accounting for HUD at top.

        Args:
            window_width: Window width in pixels
            window_height: Window height in pixels
        """
        # Calculate board dimensions in pixels
        board_pixel_width = BOARD_WIDTH * CELL_SIZE
        board_pixel_height = BOARD_HEIGHT * CELL_SIZE

        # Calculate playable area (subtract HUD height from top)
        playable_height = window_height - HUD_HEIGHT

        # Calculate zoom to fit board in playable area
        zoom_x = window_width / board_pixel_width
        zoom_y = playable_height / board_pixel_height

        # Use the smaller zoom to ensure entire board is visible
        optimal_zoom = min(zoom_x, zoom_y)

        # Apply zoom
        self.zoom_level = optimal_zoom
        self.camera_2d.zoom = self.zoom_level

        # Center camera on board center, shifted down to account for HUD
        board_center_x = (BOARD_WIDTH * CELL_SIZE) / 2
        board_center_y = (BOARD_HEIGHT * CELL_SIZE) / 2
        # Offset camera downward by half the HUD height (in world coordinates)
        hud_offset_world = (HUD_HEIGHT / 2) / self.zoom_level

        self.camera_2d.position = (board_center_x, board_center_y)

        logger.debug(
            f"Camera setup: zoom={self.zoom_level:.2f}, "
            f"position=({board_center_x:.1f}, {board_center_y:.1f}), "
            f"HUD offset={hud_offset_world:.1f}"
        )

    def pan(self, dx: float, dy: float) -> None:
        """
        Pan the 2D camera by the given amount.

        Args:
            dx: Change in x
            dy: Change in y
        """
        self.camera_2d.position = (
            self.camera_2d.position[0] + dx,
            self.camera_2d.position[1] + dy,
        )

    def zoom_in(self) -> None:
        """Zoom in the 2D camera."""
        self.zoom_level = min(2.0, self.zoom_level * 1.1)
        self.camera_2d.zoom = self.zoom_level

    def zoom_out(self) -> None:
        """Zoom out the 2D camera."""
        self.zoom_level = max(0.5, self.zoom_level / 1.1)
        self.camera_2d.zoom = self.zoom_level

    def toggle_mode(self, board_3d_available: bool) -> str:
        """
        Toggle between 2D and 3D camera modes.

        Args:
            board_3d_available: Whether 3D rendering is available

        Returns:
            New camera mode ("2D" or "3D")
        """
        if self.camera_mode == "2D":
            # Trying to enter 3D mode
            if not board_3d_available:
                logger.error("3D rendering failed to initialize. Cannot switch to 3D mode.")
                return "2D"
            self.camera_mode = "3D"
            logger.debug(f"Camera mode: {self.camera_mode}")
            logger.info("Press TAB to cycle through and follow your tokens")
        else:
            # Exiting 3D mode back to 2D
            self.camera_mode = "2D"
            logger.debug(f"Camera mode: {self.camera_mode}")

        return self.camera_mode

    def cycle_controlled_token(self, game_state) -> Optional[int]:
        """
        Cycle to next token in 3D mode.

        Args:
            game_state: Game state object

        Returns:
            New controlled token ID or None
        """
        current_player = game_state.get_current_player()
        if not current_player:
            return None

        # Get all alive deployed tokens for current player
        alive_tokens = [
            token.id
            for token in game_state.get_player_tokens(current_player.id)
            if token.is_alive and token.is_deployed
        ]

        if not alive_tokens:
            logger.debug("No alive tokens to control")
            return None

        # Find next token
        next_index = 0
        if alive_tokens:
            if self.controlled_token_id is not None:
                current_index = alive_tokens.index(self.controlled_token_id)
                next_index = (current_index + 1) % len(alive_tokens)
            else:
                next_index = 0

        self.controlled_token_id = alive_tokens[next_index]
        token = game_state.get_token(self.controlled_token_id)
        if token:
            logger.debug(f"Switched to token {self.controlled_token_id} at {token.position}")
        else:
            logger.debug(f"Switched to token {self.controlled_token_id} (token not found)")

        return self.controlled_token_id

    def rotate_camera_left(self, game_state) -> None:
        """
        Rotate camera left (Q key) in 3D mode.

        Args:
            game_state: Game state object
        """
        if self.camera_mode != "3D":
            return

        self.token_rotation -= CAMERA_ROTATION_INCREMENT
        # Update camera position immediately
        if self.controlled_token_id:
            token = game_state.get_token(self.controlled_token_id)
            if token and token.is_alive:
                self.camera_3d.follow_token(token.position, self.token_rotation)
                logger.debug(
                    f"Camera rotation: {self.token_rotation}, "
                    f"following token {token.id} at {token.position}"
                )
            else:
                logger.debug(
                    f"Camera rotation: {self.token_rotation}, "
                    "but no valid token to follow"
                )
        else:
            logger.debug(
                f"Camera rotation: {self.token_rotation}, "
                "but no controlled token selected"
            )

    def rotate_camera_right(self, game_state) -> None:
        """
        Rotate camera right (E key) in 3D mode.

        Args:
            game_state: Game state object
        """
        if self.camera_mode != "3D":
            return

        self.token_rotation += CAMERA_ROTATION_INCREMENT
        # Update camera position immediately
        if self.controlled_token_id:
            token = game_state.get_token(self.controlled_token_id)
            if token and token.is_alive:
                self.camera_3d.follow_token(token.position, self.token_rotation)
                logger.debug(
                    f"Camera rotation: {self.token_rotation}, "
                    f"following token {token.id} at {token.position}"
                )
            else:
                logger.debug(
                    f"Camera rotation: {self.token_rotation}, "
                    "but no valid token to follow"
                )
        else:
            logger.debug(
                f"Camera rotation: {self.token_rotation}, "
                "but no controlled token selected"
            )

    def update_3d_camera(self, game_state) -> None:
        """
        Update 3D camera to follow controlled token.

        Args:
            game_state: Game state object
        """
        if self.camera_mode != "3D":
            return

        if self.controlled_token_id:
            token = game_state.get_token(self.controlled_token_id)
            if token and token.is_alive:
                self.camera_3d.follow_token(token.position, self.token_rotation)

    def handle_mouse_motion(
        self, x: int, y: int, dx: int, dy: int, window
    ) -> bool:
        """
        Handle mouse motion for mouse-look in 3D mode.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            dx: Mouse x delta
            dy: Mouse y delta
            window: Window reference for cursor visibility

        Returns:
            True if mouse motion was handled (mouse-look active)
        """
        if self.camera_mode == "3D" and self.mouse_look_active:
            # Apply mouse movement to camera rotation
            yaw_delta = -dx * self.mouse_look_sensitivity
            pitch_delta = -dy * self.mouse_look_sensitivity

            # Update camera rotation
            self.camera_3d.rotate(yaw_delta=yaw_delta, pitch_delta=pitch_delta)

            # If following a token, update the token rotation to match camera yaw
            if self.controlled_token_id:
                self.token_rotation = self.camera_3d.yaw

            return True
        return False

    def activate_mouse_look(self, x: int, y: int, window) -> None:
        """
        Activate mouse-look mode in 3D.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            window: Window reference for cursor visibility
        """
        if self.camera_mode == "3D":
            self.mouse_look_active = True
            self.last_mouse_position = (x, y)
            window.set_mouse_visible(False)
            logger.debug("Mouse-look activated")

    def deactivate_mouse_look(self, window) -> None:
        """
        Deactivate mouse-look mode.

        Args:
            window: Window reference for cursor visibility
        """
        if self.camera_mode == "3D":
            self.mouse_look_active = False
            window.set_mouse_visible(True)
            logger.debug("Mouse-look deactivated")

    def screen_to_world_2d(self, screen_x: int, screen_y: int) -> Tuple[float, float]:
        """
        Convert screen coordinates to world coordinates in 2D mode.

        Args:
            screen_x: Screen x coordinate
            screen_y: Screen y coordinate

        Returns:
            World coordinates (x, y)
        """
        return self.camera_2d.unproject((screen_x, screen_y))

    def screen_to_grid_3d(
        self, screen_x: int, screen_y: int, window_width: int, window_height: int
    ) -> Optional[Tuple[int, int]]:
        """
        Convert screen coordinates to grid coordinates in 3D mode using ray casting.

        Args:
            screen_x: Screen x coordinate
            screen_y: Screen y coordinate
            window_width: Window width
            window_height: Window height

        Returns:
            Grid coordinates (x, y) or None if no intersection
        """
        # 3D ray casting
        ray_origin, ray_direction = self.camera_3d.screen_to_ray(
            screen_x, screen_y, window_width, window_height
        )

        # Intersect with board plane (z=0)
        intersection = self.camera_3d.ray_intersect_plane(
            ray_origin, ray_direction, plane_z=0.0
        )

        if intersection:
            world_x, world_y, _ = intersection
            grid_x, grid_y = self.camera_3d.world_to_grid(world_x, world_y)
            return (grid_x, grid_y)

        return None

    def resize(self, width: int, height: int) -> None:
        """
        Handle window resize.

        Args:
            width: New window width
            height: New window height
        """
        # Update 2D camera viewports
        self.camera_2d.viewport = arcade.types.LBWH(0, 0, width, height)
        self.ui_camera.viewport = arcade.types.LBWH(0, 0, width, height)

        # Update camera setup to refit board
        self.setup_initial_view(width, height)

        # Update 3D camera aspect ratio (without resetting position)
        self.camera_3d.update_aspect_ratio(width, height)
