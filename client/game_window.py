"""
Main Arcade-based game window for Race to the Crystal.

This module implements the primary game window using the Arcade framework,
replacing the Pygame-based implementation with GPU-accelerated rendering.
"""

from typing import Optional

import arcade

from client.audio_manager import AudioManager
from client.camera_controller import CameraController
from client.deployment_menu_controller import DeploymentMenuController
from client.game_action_handler import GameActionHandler
from client.input_handler import InputHandler
from client.renderer_2d import Renderer2D
from client.renderer_3d import Renderer3D
from client.ui.arcade_ui import UIManager
from client.ui.chat_widget import ChatWidget
from game.combat import CombatSystem
from game.game_state import GameState
from game.movement import MovementSystem
from shared.constants import (
    BACKGROUND_COLOR,
    CHAT_WIDGET_HEIGHT,
    CHAT_WIDGET_WIDTH,
    CHAT_WIDGET_X,
    CHAT_WIDGET_Y,
    MYSTERY_ANIMATION_DURATION,
    PLAYER_COLORS,
)
from shared.enums import TurnPhase
from shared.logging_config import setup_logger

# Set up logger for this module
logger = setup_logger(__name__)


class GameView(arcade.View):
    """
    Main game view for Race to the Crystal.

    Handles rendering, input, and game loop using Arcade's View architecture.
    This is designed to be shown within an existing window.
    """

    def __init__(
        self,
        game_state: GameState,
        start_in_3d: bool = False,
        is_network_game: bool = False,
        network_client: Optional["NetworkClient"] = None,
    ):
        """
        Initialize the game view.

        Args:
            game_state: The game state to render
            start_in_3d: Whether to start in 3D mode
            is_network_game: Whether this is a network game (enables chat)
            network_client: Network client for chat functionality (network games only)
        """
        super().__init__()

        # Game state
        self.game_state = game_state
        self.is_network_game = is_network_game
        self.network_client = network_client
        self.start_in_3d = start_in_3d

        # Systems
        self.movement_system = MovementSystem()
        self.combat_system = CombatSystem()

        # Camera controller (will be initialized in on_show_view)
        self.camera_controller = None

        # Renderer controllers
        self.renderer_2d = Renderer2D()
        self.renderer_3d = Renderer3D()

        # Visual elements
        self.ui_sprites = arcade.SpriteList()

        # Input handler (will be initialized in on_show_view)
        self.input_handler = None

        # HUD Text objects (for performance)
        self.player_text = arcade.Text(
            "",
            10,
            0,  # Y will be updated in _draw_hud
            (255, 255, 255),
            font_size=24,
            bold=True,
        )
        self.turn_text = arcade.Text("", 10, 0, (200, 200, 200), font_size=16)
        self.phase_text = arcade.Text("", 200, 0, (200, 200, 200), font_size=16)
        self.instruction_text = arcade.Text(
            "",
            0,
            0,  # X and Y will be updated in _draw_hud
            (150, 150, 150),
            font_size=14,
        )

        # UI Manager for panels and buttons (will be initialized in on_show_view)
        self.ui_manager = None

        # Deployment menu controller (will be initialized in on_show_view)
        self.deployment_controller = None

        # Chat widget for in-game communication
        self.chat_widget = None

        # Audio manager for background music and generator hums
        self.audio_manager = AudioManager()

        # Mystery square coin flip animations
        # Dict mapping (x, y) position to animation progress (0.0 to 1.0)
        self.mystery_animations = {}  # {(x, y): progress}
        self.mystery_animation_duration = (
            MYSTERY_ANIMATION_DURATION  # Duration in seconds
        )

        # Background color will be set in on_show_view()

    def on_show_view(self):
        """Called when this view is shown."""
        # Set background color
        arcade.set_background_color(BACKGROUND_COLOR)

        # Initialize components that need window dimensions
        self.camera_controller = CameraController(
            self.window.width, self.window.height, self.start_in_3d
        )
        self.ui_manager = UIManager(self.window.width, self.window.height)
        self.deployment_controller = DeploymentMenuController(
            self.window.width, self.window.height
        )

        # Initialize action handler (needs renderer and ui_manager references)
        self.action_handler = GameActionHandler(
            self.game_state,
            self.movement_system,
            self.renderer_2d,
            self.renderer_3d,
            self.ui_manager,
            self.audio_manager,
        )

        # Initialize input handler (coordinates all input events)
        self.input_handler = InputHandler(
            self.game_state,
            self.camera_controller,
            self.deployment_controller,
            self.ui_manager,
            self.action_handler,
            self.renderer_2d,
            self.renderer_3d,
            self.movement_system,
            self.audio_manager,
        )
        self.input_handler.set_mystery_animations(self.mystery_animations)

        # Initialize chat widget only for network games
        if self.is_network_game:
            chat_width = CHAT_WIDGET_WIDTH
            chat_height = CHAT_WIDGET_HEIGHT
            # Position on left side, avoiding corner deployment menus
            # Bottom-left deployment: y=60 (center), extends to ~y=140 (top)
            # Top-left deployment: y=560 (center), starts at ~y=500 (bottom)
            # Safe zone: y=200 to y=500
            chat_x = CHAT_WIDGET_X
            chat_y = CHAT_WIDGET_Y
            self.chat_widget = ChatWidget(
                network_client=self.network_client,
                x=chat_x,
                y=chat_y,
                width=chat_width,
                height=chat_height,
            )
        else:
            self.chat_widget = None

        # Set up the game
        self.setup()

        logger.info(f"Game view initialized: {self.window.width}x{self.window.height}")

    def on_hide_view(self):
        """Called when this view is hidden."""
        # Pause all audio
        self.audio_manager.pause_all()

        # Clean up OpenGL resources
        self.renderer_3d.cleanup()

    def setup(self):
        """Set up the window after initialization."""
        logger.debug(
            f"Setup called - Game state has {len(self.game_state.players)} players, {len(self.game_state.tokens)} tokens"
        )

        # Create 2D rendering elements
        self.renderer_2d.create_board_sprites(
            self.game_state.board,
            self.game_state.generators,
            self.game_state.crystal,
            self.mystery_animations,
        )
        self.renderer_2d.create_token_sprites(self.game_state)
        logger.debug(f"Created {len(self.renderer_2d.token_sprites)} token sprites")

        self._create_ui_sprites()
        self.renderer_3d.create(
            self.game_state, self.window.ctx, self.mystery_animations
        )

        # Set up camera to fit entire board in view
        self.camera_controller.setup_initial_view(self.window.width, self.window.height)

        # Load and play background music (only if not already loaded)
        if not self.audio_manager.background_music:
            self.audio_manager.load_background_music()

        # Build initial UI
        self.ui_manager.rebuild_visuals(self.game_state)

        logger.info("Window setup complete")

    def _create_ui_sprites(self):
        """Create UI sprites (HUD, buttons, etc.)."""
        # Corner indicator is drawn directly in _draw_hud() in screen space
        pass

    def _draw_hud(self):
        """Draw the heads-up display with game information."""
        # Get current player
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        # HUD background
        arcade.draw_lrbt_rectangle_filled(
            0,
            self.window.width,
            self.window.height - 80,
            self.window.height,
            (20, 20, 30, 200),  # Semi-transparent dark background
        )

        # Current player info
        player_color = PLAYER_COLORS[current_player.color.value]
        self.player_text.text = f"{current_player.name}'s Turn"
        self.player_text.color = player_color
        self.player_text.y = self.window.height - 30
        self.player_text.draw()

        # Turn number
        self.turn_text.text = f"Turn {self.game_state.turn_number}"
        self.turn_text.y = self.window.height - 60
        self.turn_text.draw()

        # Turn phase (check if input_handler exists)
        if self.input_handler:
            self.phase_text.text = f"Phase: {self.input_handler.turn_phase.name}"
        else:
            self.phase_text.text = "Phase: MOVEMENT"
        self.phase_text.y = self.window.height - 60
        self.phase_text.draw()

        # Instructions (check if input_handler exists)
        if self.input_handler:
            if self.deployment_controller.selected_deploy_health:
                instruction = f"Selected {self.deployment_controller.selected_deploy_health}hp token - click a corner position to deploy (ESC to cancel)"
            elif self.input_handler.turn_phase == TurnPhase.MOVEMENT:
                if self.camera_controller.camera_mode == "3D":
                    instruction = "Click a token to select, then move OR attack (not both) | Right-click + drag to look around"
                else:
                    instruction = (
                        "Click a token to select, then move OR attack (not both)"
                    )
            elif self.input_handler.turn_phase == TurnPhase.ACTION:
                instruction = (
                    "Click an adjacent enemy to attack, or press SPACE to end turn"
                )
            else:
                instruction = "Press SPACE to end turn"
        else:
            instruction = ""

        self.instruction_text.text = instruction
        self.instruction_text.x = self.window.width - 700
        self.instruction_text.y = self.window.height - 60
        self.instruction_text.draw()

        # Draw corner indicator for deployment area
        current_player = self.game_state.get_current_player()
        if current_player:
            self.deployment_controller.draw_indicator(current_player)

    def on_draw(self):
        """
        Render the screen.

        Called automatically by Arcade on each frame.
        """
        # Ensure proper OpenGL state for 2D rendering
        self.window.ctx.disable(self.window.ctx.DEPTH_TEST)
        self.window.ctx.enable(self.window.ctx.BLEND)

        # Clear the window (color buffer and depth buffer)
        self.clear()

        if self.camera_controller.camera_mode == "2D":
            # 2D top-down rendering
            self.renderer_2d.draw(self.camera_controller.camera_2d)
        else:
            # 3D first-person rendering - enable depth test and blending
            self.window.ctx.enable(self.window.ctx.DEPTH_TEST)
            self.window.ctx.enable(self.window.ctx.BLEND)
            self.window.ctx.disable(self.window.ctx.CULL_FACE)

            if self.renderer_3d.is_available():
                # Update camera to follow controlled token
                self.camera_controller.update_3d_camera(self.game_state)

                # Draw 3D rendering
                self.renderer_3d.draw(self.camera_controller.camera_3d)

            # Reset state for UI
            self.window.ctx.disable(self.window.ctx.DEPTH_TEST)

        # Draw UI (no camera transform) - always in 2D
        with self.camera_controller.ui_camera.activate():
            self.ui_sprites.draw()
            self._draw_hud()
            self.ui_manager.draw()

        # Draw chat widget (in UI space)
        if self.chat_widget:
            with self.camera_controller.ui_camera.activate():
                self.chat_widget.draw()

        # Draw corner menu if open (in UI space around R hexagon)
        # Works in both 2D and 3D modes
        # Draw deployment menu if open
        if self.deployment_controller.menu_open:
            with self.camera_controller.ui_camera.activate():
                current_player = self.game_state.get_current_player()
                if current_player:
                    reserve_counts = self.game_state.get_reserve_token_counts(
                        current_player.id
                    )
                    self.deployment_controller.draw_menu(current_player, reserve_counts)

    def on_update(self, delta_time: float):
        """
        Update game state and animations.

        Args:
            delta_time: Time since last update in seconds
        """
        # Update animations
        self.renderer_2d.update(delta_time)
        self.renderer_3d.update(delta_time)
        self.ui_sprites.update()

        # Update chat widget
        if self.chat_widget:
            self.chat_widget.update(delta_time)

        # Update mystery square coin flip animations
        positions_to_remove = []
        for position, progress in self.mystery_animations.items():
            # Advance animation
            new_progress = progress + (delta_time / self.mystery_animation_duration)
            if new_progress >= 1.0:
                # Animation complete
                positions_to_remove.append(position)
            else:
                self.mystery_animations[position] = new_progress

        # Remove completed animations
        for position in positions_to_remove:
            del self.mystery_animations[position]

        # Update 3D mystery animations if there are any active
        self.renderer_3d.update_mystery_animations(self.mystery_animations)

        # Rebuild board shapes every frame to animate generator lines and mystery squares
        if self.camera_controller.camera_mode == "2D":
            self.renderer_2d.create_board_sprites(
                self.game_state.board,
                self.game_state.generators,
                self.game_state.crystal,
                self.mystery_animations,
            )

    def on_resize(self, width: int, height: int):
        """
        Handle window resize events.

        Args:
            width: New window width
            height: New window height
        """
        # Call parent resize handler
        super().on_resize(width, height)

        # Check if initialization is complete (ui_manager exists)
        if hasattr(self, "ui_manager") and self.ui_manager:
            # Update camera system
            if hasattr(self, "camera_controller") and self.camera_controller:
                self.camera_controller.resize(width, height)

            # Update UI manager layout
            self.ui_manager.update_layout(width, height)
            self.ui_manager.rebuild_visuals(self.game_state)

            # Update deployment controller
            if hasattr(self, "deployment_controller") and self.deployment_controller:
                self.deployment_controller.resize(width, height)

            logger.debug(f"Game view resized to {width}x{height}")

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        """
        Handle mouse motion for UI hover effects and mouse-look in 3D mode.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            dx: Change in x
            dy: Change in y
        """
        # Check if initialization is complete
        if not self.input_handler:
            return

        self.input_handler.handle_mouse_motion(x, y, dx, dy, self.window)

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        """
        Handle mouse press events with support for 2D and 3D picking.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            button: Which button was pressed
            modifiers: Key modifiers (Shift, Ctrl, etc.)
        """
        # Check if initialization is complete
        if not self.input_handler:
            return

        self.input_handler.handle_mouse_press(x, y, button, modifiers, self.window)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int):
        """
        Handle mouse release events.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            button: Which button was released
            modifiers: Key modifiers (Shift, Ctrl, etc.)
        """
        # Check if initialization is complete
        if not self.input_handler:
            return

        self.input_handler.handle_mouse_release(x, y, button, modifiers, self.window)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float):
        """
        Handle mouse scroll events (for zooming).

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            scroll_x: Horizontal scroll amount
            scroll_y: Vertical scroll amount
        """
        if not self.input_handler:
            return

        self.input_handler.handle_mouse_scroll(scroll_y)

    def on_key_press(self, symbol: int, modifiers: int):
        """
        Handle key press events.

        Args:
            symbol: Key that was pressed
            modifiers: Key modifiers (Shift, Ctrl, etc.)
        """
        if not self.input_handler:
            return

        self.input_handler.handle_key_press(
            symbol, modifiers, self.chat_widget, self.window
        )

    def on_text(self, text: str):
        """
        Handle text input events.

        Args:
            text: Character(s) to add
        """
        if not self.input_handler:
            return

        self.input_handler.handle_text(text, self.chat_widget)
