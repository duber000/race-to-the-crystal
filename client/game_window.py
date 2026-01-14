"""
Main Arcade-based game window for Race to the Crystal.

This module implements the primary game window using the Arcade framework,
replacing the Pygame-based implementation with GPU-accelerated rendering.
"""

from typing import Optional

import arcade

from client.audio_manager import AudioManager
from client.camera_controller import CameraController
from client.crystal_effect_animator import CrystalEffectAnimator
from client.deployment_menu_controller import DeploymentMenuController
from client.game_action_handler import GameActionHandler
from client.input_handler import InputHandler
from client.renderer_2d import Renderer2D
from client.renderer_3d import Renderer3D
from client.sprites.board_sprite import create_board_shapes
from client.ui.arcade_ui import UIManager
from client.ui.chat_widget import ChatWidget
from client.ui.victory_view import VictoryViewSimple
from client.network_client import NetworkClient
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
from shared.enums import TurnPhase, GamePhase, CrystalEffect
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
        is_network_game: bool = False,
        network_client: Optional["NetworkClient"] = None,
        local_player_id: Optional[str] = None,
        music_enabled: bool = True,
    ):
        """
        Initialize the game view.

        Args:
            game_state: The game state to render
            is_network_game: Whether this is a network game (enables chat)
            network_client: Network client for chat functionality (network games only)
            local_player_id: Game player ID for local player (e.g., "player_0")
            music_enabled: Whether background music/hums should start enabled
        """
        super().__init__()

        # Game state
        self.game_state = game_state
        self.is_network_game = is_network_game
        self.network_client = network_client
        self.local_player_id = local_player_id
        self.window.ctx  # Ensure context is available
        self.music_enabled = music_enabled

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

        # Crystal effect animator for visual effects
        self.crystal_effect_animator = CrystalEffectAnimator()

        # Mystery square coin flip animations
        # Dict mapping (x, y) position to animation progress (0.0 to 1.0)
        self.mystery_animations = {}  # {(x, y): progress}
        self.mystery_animation_duration = (
            MYSTERY_ANIMATION_DURATION  # Duration in seconds
        )

        # Victory screen tracking
        self.victory_shown = False
        self.victory_delay = (
            0.0  # Delay before showing victory screen to let final effects play
        )
        self.victory_delay_duration = (
            2.0  # Wait 2 seconds for sounds/animations to finish
        )

        # Background color will be set in on_show_view()

    def on_show_view(self):
        """Called when this view is shown."""
        # Set background color
        arcade.set_background_color(BACKGROUND_COLOR)

        # Initialize components that need window dimensions
        # Use local_player_id from init (for network games), otherwise None (for single player)
        logger.info(
            f"GameView.on_show_view: is_network_game={self.is_network_game}, local_player_id={self.local_player_id}"
        )
        self.camera_controller = CameraController(
            self.window.width, self.window.height, False, self.local_player_id
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
            chat_x = CHAT_WIDGET_X
            chat_y = CHAT_WIDGET_Y
            # Assert network_client is not None since we are in a network game
            assert self.network_client is not None
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
        current_player = self.game_state.get_current_player()
        viewing_player_id = current_player.id if current_player else None
        self.renderer_2d.create_token_sprites(self.game_state, viewing_player_id)
        logger.debug(f"Created {len(self.renderer_2d.token_sprites)} token sprites")

        self._create_ui_sprites()
        current_player = self.game_state.get_current_player()
        viewing_player_id = current_player.id if current_player else None
        self.renderer_3d.create(
            self.game_state, self.window.ctx, self.mystery_animations
        )
        # Update 3D tokens with crystal effects after creation
        if viewing_player_id:
            self.renderer_3d._create_tokens_with_effects(self.game_state, self.window.ctx, viewing_player_id)

        # Set up camera to fit entire board in view
        self.camera_controller.setup_initial_view(self.window.width, self.window.height)  # type: ignore

        # Load and play background music (only if enabled and not already loaded)
        self.audio_manager.music_playing = self.music_enabled
        if self.music_enabled and not self.audio_manager.background_music:
            self.audio_manager.load_background_music()

        # Build initial UI
        self.ui_manager.rebuild_visuals(self.game_state)  # type: ignore

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
            if self.deployment_controller.selected_deploy_health:  # type: ignore
                instruction = f"Selected {self.deployment_controller.selected_deploy_health}hp token - click a corner position to deploy (ESC to cancel)"  # type: ignore
            elif self.input_handler.turn_phase == TurnPhase.MOVEMENT:
                if self.camera_controller.camera_mode == "3D":  # type: ignore
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
            self.deployment_controller.draw_indicator(current_player)  # type: ignore

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

        if self.camera_controller.camera_mode == "2D":  # type: ignore
            # 2D top-down rendering
            self.renderer_2d.draw(self.camera_controller.camera_2d)  # type: ignore
        else:
            # 3D first-person rendering - enable depth test and blending
            self.window.ctx.enable(self.window.ctx.DEPTH_TEST)
            self.window.ctx.enable(self.window.ctx.BLEND)
            self.window.ctx.disable(self.window.ctx.CULL_FACE)

            if self.renderer_3d.is_available():
                # Update camera to follow controlled token
                self.camera_controller.update_3d_camera(self.game_state)  # type: ignore

                # Update hover and valid move indicators for 3D
                if self.renderer_3d.board_3d:
                    self.renderer_3d.board_3d.update_hover_indicator(
                        self.input_handler.hovered_grid_pos
                    )
                    self.renderer_3d.board_3d.update_valid_moves(
                        self.input_handler.valid_moves
                    )

                # Draw 3D rendering
                self.renderer_3d.draw(self.camera_controller.camera_3d)  # type: ignore

            # Reset state for UI
            self.window.ctx.disable(self.window.ctx.DEPTH_TEST)

        # Draw crystal effect animations (on top of game, below UI)
        if self.crystal_effect_animator.is_animating() and self.game_state.crystal:
            # Convert crystal grid position to screen position
            crystal_pos = self.game_state.crystal.position
            if self.camera_controller.camera_mode == "2D":  # type: ignore
                # Use camera transform for 2D mode
                with self.camera_controller.camera_2d.activate():  # type: ignore
                    from shared.constants import CELL_SIZE
                    screen_x = crystal_pos[0] * CELL_SIZE + CELL_SIZE / 2
                    screen_y = crystal_pos[1] * CELL_SIZE + CELL_SIZE / 2
                    self.crystal_effect_animator.draw(screen_x, screen_y)
            else:
                # For 3D mode, draw in screen space
                # Project 3D crystal position to screen coordinates
                # For now, use a fixed center position
                with self.camera_controller.ui_camera.activate():  # type: ignore
                    screen_x = self.window.width / 2
                    screen_y = self.window.height / 2
                    self.crystal_effect_animator.draw(screen_x, screen_y)

        # Draw UI (no camera transform) - always in 2D
        with self.camera_controller.ui_camera.activate():  # type: ignore
            self.ui_sprites.draw()
            self._draw_hud()
            self.ui_manager.draw()  # type: ignore

        # Draw chat widget (in UI space)
        if self.chat_widget:
            with self.camera_controller.ui_camera.activate():
                self.chat_widget.draw()

        # Draw corner menu if open (in UI space around R hexagon)
        # Works in both 2D and 3D modes
        # Draw deployment menu if open
        if self.deployment_controller.menu_open:  # type: ignore
            with self.camera_controller.ui_camera.activate():  # type: ignore
                current_player = self.game_state.get_current_player()
                if current_player:
                    reserve_counts = self.game_state.get_reserve_token_counts(
                        current_player.id
                    )
                    self.deployment_controller.draw_menu(current_player, reserve_counts)  # type: ignore

    def on_update(self, delta_time: float):
        """
        Update game state and animations.

        Args:
            delta_time: Time since last update in seconds
        """
        # Check if game has ended
        if not self.victory_shown and self.game_state.phase == GamePhase.ENDED:
            # Start countdown to victory screen (let final effects play first)
            self.victory_delay += delta_time

            if self.victory_delay >= self.victory_delay_duration:
                self.victory_shown = True
                winner = self.game_state.get_winner()
                if winner:
                    winner_name = winner.name
                    # Create and show victory view
                    victory_view = VictoryViewSimple(winner_name)
                    victory_view.on_return_to_menu = self._on_victory_return_to_menu
                    self.window.show_view(victory_view)
                    return

        # Update animations
        self.renderer_2d.update(delta_time)
        self.renderer_3d.update(delta_time)
        self.ui_sprites.update()

        # Update chat widget
        if self.chat_widget:
            self.chat_widget.update(delta_time)

        # Process pending mystery animations (start when token arrives)
        self.action_handler.process_pending_mystery_animations(self.mystery_animations)

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

        # Check for newly triggered crystal effects
        if self.game_state.last_triggered_crystal_effect:
            player_id, effect_type = self.game_state.last_triggered_crystal_effect

            # Get crystal position
            if self.game_state.crystal:
                crystal_pos = self.game_state.crystal.position

                # Get affected tokens for lightning effect
                affected_tokens = []
                if effect_type == CrystalEffect.DAMAGE_BOOST:
                    affected_tokens = [
                        t for t in self.game_state.tokens.values()
                        if t.player_id == player_id and t.is_deployed and t.is_alive
                    ]

                # Start animation
                self.crystal_effect_animator.start_effect_animation(
                    effect_type, crystal_pos, affected_tokens
                )

                # Play sound effect
                if effect_type == CrystalEffect.FOG_OF_WAR:
                    self.audio_manager.play_fog_horn_sound()
                elif effect_type == CrystalEffect.PHANTOM_ENEMIES:
                    self.audio_manager.play_ghost_sound()
                elif effect_type == CrystalEffect.DAMAGE_BOOST:
                    self.audio_manager.play_lightning_sound()
                elif effect_type == CrystalEffect.SPEED_BOOST:
                    self.audio_manager.play_whoosh_sound()

            # Clear the trigger
            self.game_state.last_triggered_crystal_effect = None

        # Update crystal effect animator
        self.crystal_effect_animator.update(delta_time)

        # Update 3D mystery animations if there are any active
        self.renderer_3d.update_mystery_animations(self.mystery_animations)

        # Recreate board shapes every frame to update animations (glowing lines, crystal pulse)
        # Check if board data is valid before animating
        renderer_board = getattr(self.renderer_2d, "board", None)
        renderer_generators = getattr(self.renderer_2d, "generators", None)
        renderer_crystal = getattr(self.renderer_2d, "crystal", None)
        renderer_mystery = getattr(self.renderer_2d, "mystery_animations", None)

        if (
            renderer_board is not None
            and renderer_generators is not None
            and renderer_crystal is not None
            and renderer_mystery is not None
        ):
            # Board data is valid, animate
            crystal_pos = (
                self.renderer_2d.crystal.position if self.renderer_2d.crystal else None
            )
            self.renderer_2d.board_shapes = create_board_shapes(
                self.renderer_2d.board,  # type: ignore
                generators=self.renderer_2d.generators,  # type: ignore
                crystal_pos=crystal_pos,
                mystery_animations=self.mystery_animations,
            )
        else:
            # Board data missing, animation loop skipped
            pass

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

    def _on_victory_return_to_menu(self):
        """Handle returning to main menu from victory screen."""
        # Close the current view and return to main menu
        from client.menu_main import MainMenu

        main_menu = MainMenu()
        self.window.show_view(main_menu)
