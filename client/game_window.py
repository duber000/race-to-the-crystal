"""
Main Arcade-based game window for Race to the Crystal.

This module implements the primary game window using the Arcade framework,
replacing the Pygame-based implementation with GPU-accelerated rendering.
"""

import math
from typing import List, Optional, Tuple

import arcade

from client.audio_manager import AudioManager
from client.camera_controller import CameraController
from client.deployment_menu_controller import DeploymentMenuController
from client.game_action_handler import GameActionHandler
from client.renderer_2d import Renderer2D
from client.renderer_3d import Renderer3D
from client.ui.arcade_ui import UIManager
from client.ui.chat_widget import ChatWidget
from game.combat import CombatSystem
from game.game_state import GameState
from game.movement import MovementSystem
from game.mystery_square import MysterySquareSystem
from shared.constants import (
    BACKGROUND_COLOR,
    CELL_SIZE,
    CHAT_WIDGET_HEIGHT,
    CHAT_WIDGET_WIDTH,
    CHAT_WIDGET_X,
    CHAT_WIDGET_Y,
    CIRCLE_SEGMENTS,
    CORNER_INDICATOR_MARGIN,
    CORNER_INDICATOR_SIZE,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    DEPLOYMENT_MENU_SPACING,
    HEXAGON_SIDES,
    HUD_HEIGHT,
    MENU_OPTION_CLICK_RADIUS,
    MYSTERY_ANIMATION_DURATION,
    PLAYER_COLORS,
)
from shared.enums import TurnPhase, CellType
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

        # Selection state
        self.selected_token_id: Optional[int] = None
        self.valid_moves: List[Tuple[int, int]] = []
        self.turn_phase = TurnPhase.MOVEMENT

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
        self.mystery_animation_duration = MYSTERY_ANIMATION_DURATION  # Duration in seconds

        # Background color will be set in on_show_view()

    def on_show_view(self):
        """Called when this view is shown."""
        # Set background color
        arcade.set_background_color(BACKGROUND_COLOR)

        # Initialize components that need window dimensions
        self.camera_controller = CameraController(self.window.width, self.window.height, self.start_in_3d)
        self.ui_manager = UIManager(self.window.width, self.window.height)
        self.deployment_controller = DeploymentMenuController(self.window.width, self.window.height)

        # Initialize action handler (needs renderer and ui_manager references)
        self.action_handler = GameActionHandler(
            self.game_state,
            self.movement_system,
            self.renderer_2d,
            self.renderer_3d,
            self.ui_manager,
            self.audio_manager,
        )

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
                height=chat_height
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
        logger.debug(f"Setup called - Game state has {len(self.game_state.players)} players, {len(self.game_state.tokens)} tokens")

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
        self.renderer_3d.create(self.game_state, self.window.ctx, self.mystery_animations)

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

        # Turn phase
        self.phase_text.text = f"Phase: {self.turn_phase.name}"
        self.phase_text.y = self.window.height - 60
        self.phase_text.draw()

        # Instructions
        if self.deployment_controller.selected_deploy_health:
            instruction = f"Selected {self.deployment_controller.selected_deploy_health}hp token - click a corner position to deploy (ESC to cancel)"
        elif self.turn_phase == TurnPhase.MOVEMENT:
            if self.camera_controller.camera_mode == "3D":
                instruction = "Click a token to select, then move OR attack (not both) | Right-click + drag to look around"
            else:
                instruction = "Click a token to select, then move OR attack (not both)"
        elif self.turn_phase == TurnPhase.ACTION:
            instruction = (
                "Click an adjacent enemy to attack, or press SPACE to end turn"
            )
        else:
            instruction = "Press SPACE to end turn"

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
                    reserve_counts = self.game_state.get_reserve_token_counts(current_player.id)
                    self.deployment_controller.draw_menu(current_player, reserve_counts)

    def on_update(self, delta_time: float):
        """
        Update game state and animations.

        Args:
            delta_time: Time since last update in seconds
        """
        # Update animations
        self.renderer_2d.update(delta_time)
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
        if not hasattr(self, "camera_controller") or not self.camera_controller:
            return

        # Handle mouse-look in 3D mode
        if self.camera_controller.handle_mouse_motion(x, y, dx, dy, self.window):
            return  # Mouse-look handled, skip UI hover effects

        # Normal UI hover effects
        self.ui_manager.handle_mouse_motion(x, y)

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
        if not hasattr(self, "camera_controller") or not self.camera_controller:
            return

        if button == arcade.MOUSE_BUTTON_RIGHT and self.camera_controller.camera_mode == "3D":
            # Activate mouse-look in 3D mode
            self.camera_controller.activate_mouse_look(x, y, self.window)
            return

        if button == arcade.MOUSE_BUTTON_LEFT:
            # Check UI first (prevents click-through)
            ui_action = self.ui_manager.handle_mouse_click(x, y)
            if ui_action == "end_turn":
                self._handle_end_turn()
                return
            elif ui_action == "cancel":
                self._handle_cancel()
                return

            current_player = self.game_state.get_current_player()

            # First, convert screen coordinates to world/grid to check for tokens
            world_pos = None
            grid_pos = None
            clicked_on_token = False

            if self.camera_controller.camera_mode == "2D":
                world_pos = self.camera_controller.screen_to_world_2d(x, y)
                grid_x = int(world_pos[0] // CELL_SIZE)
                grid_y = int(world_pos[1] // CELL_SIZE)
                grid_pos = (grid_x, grid_y)
            else:
                grid_pos = self.camera_controller.screen_to_grid_3d(x, y, self.window.width, self.window.height)

            # Check if there's a token at the click position
            if grid_pos and self.game_state.board.is_valid_position(grid_pos[0], grid_pos[1]):
                for player in self.game_state.players.values():
                    for token_id in player.token_ids:
                        token = self.game_state.get_token(token_id)
                        if (token and token.is_alive and token.is_deployed and
                            token.position == grid_pos):
                            clicked_on_token = True
                            break
                    if clicked_on_token:
                        break

            # Check corner menu if open (UI-based menu) - do this before indicator check
            if self.deployment_controller.menu_open and current_player:
                reserve_counts = self.game_state.get_reserve_token_counts(current_player.id)
                selected_health = self.deployment_controller.handle_menu_click((x, y), current_player, reserve_counts)
                if selected_health:
                    # Clear any existing token selection to prevent conflicts
                    self.selected_token_id = None
                    self.valid_moves = []
                    self.renderer_2d.update_selection_visuals(
                        self.selected_token_id, self.valid_moves, self.game_state
                    )
                    return

            # Check if clicking on R hexagon to open menu - but NOT if clicking on a token
            if (not clicked_on_token and
                not self.deployment_controller.menu_open and
                self.deployment_controller.is_click_on_indicator(x, y, current_player)):
                if current_player and self.turn_phase == TurnPhase.MOVEMENT:
                    self.deployment_controller.open_menu()
                    return

            # Proceed with world interaction
            if self.camera_controller.camera_mode == "2D":
                if world_pos:
                    self._handle_select((world_pos[0], world_pos[1]))
            else:
                if grid_pos:
                    logger.debug(f"3D click detected at grid {grid_pos}")
                    self._handle_select_3d(grid_pos)
                else:
                    logger.debug("3D ray casting: no intersection with board plane")

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
        if not hasattr(self, "camera_controller") or not self.camera_controller:
            return

        if button == arcade.MOUSE_BUTTON_RIGHT and self.camera_controller.camera_mode == "3D":
            # Deactivate mouse-look in 3D mode
            self.camera_controller.deactivate_mouse_look(self.window)

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float):
        """
        Handle mouse scroll events (for zooming).

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            scroll_x: Horizontal scroll amount
            scroll_y: Vertical scroll amount
        """
        if scroll_y > 0:
            self.camera_controller.zoom_in()
        elif scroll_y < 0:
            self.camera_controller.zoom_out()

    def on_key_press(self, symbol: int, modifiers: int):
        """
        Handle key press events.

        Args:
            symbol: Key that was pressed
            modifiers: Key modifiers (Shift, Ctrl, etc.)
        """
        # Handle chat widget input first
        if self.chat_widget:
            if self.chat_widget.on_key_press(symbol, modifiers):
                return  # Chat widget handled the input
        
        # Camera panning
        if symbol == arcade.key.W or symbol == arcade.key.UP:
            self.camera_controller.pan(0, self.camera_controller.camera_speed)
        elif symbol == arcade.key.S or symbol == arcade.key.DOWN:
            self.camera_controller.pan(0, -self.camera_controller.camera_speed)
        elif symbol == arcade.key.A or symbol == arcade.key.LEFT:
            self.camera_controller.pan(-self.camera_controller.camera_speed, 0)
        elif symbol == arcade.key.D or symbol == arcade.key.RIGHT:
            self.camera_controller.pan(self.camera_controller.camera_speed, 0)

        # Zoom
        elif symbol == arcade.key.PLUS or symbol == arcade.key.EQUAL:
            self.camera_controller.zoom_in()
        elif symbol == arcade.key.MINUS:
            self.camera_controller.zoom_out()

        # Game controls
        elif symbol == arcade.key.SPACE or symbol == arcade.key.ENTER:
            self._handle_end_turn()
        elif symbol == arcade.key.ESCAPE:
            self._handle_cancel()

        # Music toggle
        elif symbol == arcade.key.M:
            self.audio_manager.toggle_music()
            # Update generator hums to respect captured state when resuming
            if self.audio_manager.music_playing:
                self.audio_manager.update_generator_hums(self.game_state.generators)

        # 3D View controls
        elif symbol == arcade.key.V:
            # Check if initialization is complete
            if (
                not hasattr(self, "camera_controller")
                or not hasattr(self, "board_3d")
                or not hasattr(self, "shader_3d")
            ):
                return

            # Toggle between 2D and 3D views (only if 3D rendering is available)
            self.camera_controller.toggle_mode(self.renderer_3d.is_available())

        elif (
            symbol == arcade.key.TAB
            and hasattr(self, "camera_controller")
            and self.camera_controller.camera_mode == "3D"
        ):
            # Cycle to next token
            self.camera_controller.cycle_controlled_token(self.game_state)

        elif symbol == arcade.key.Q and not (modifiers & arcade.key.MOD_CTRL):
            # Rotate camera left (only in 3D mode, and not Ctrl+Q which is quit)
            self.camera_controller.rotate_camera_left(self.game_state)

        elif symbol == arcade.key.E:
            # Rotate camera right (only in 3D mode)
            self.camera_controller.rotate_camera_right(self.game_state)

        # Quit
        elif symbol == arcade.key.Q and (modifiers & arcade.key.MOD_CTRL):
            self.window.close()

    def on_text(self, text: str):
        """
        Handle text input events.

        Args:
            text: Character(s) to add
        """
        # Pass text input to chat widget if active
        if self.chat_widget and self.chat_widget.input_active:
            if self.chat_widget.on_text(text):
                return  # Chat widget handled the text

    def _handle_select(self, world_pos: Tuple[float, float]):
        """
        Handle selection at world position.

        Args:
            world_pos: Position in world coordinates
        """
        # Convert world coordinates to grid coordinates
        grid_pos = (int(world_pos[0] // CELL_SIZE), int(world_pos[1] // CELL_SIZE))

        # Get current player
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        # Handle menu state
        if not self._handle_menu_state():
            return  # Menu just opened, don't process clicks

        # Find token at clicked position
        clicked_token = self._find_token_at_position(grid_pos)

        if clicked_token:
            self._handle_token_click(clicked_token, current_player, grid_pos)
        else:
            self._handle_empty_cell_click(grid_pos, current_player)

    def _handle_menu_state(self) -> bool:
        """
        Handle deployment menu state.

        Returns:
            False if menu just opened (block further clicks), True otherwise
        """
        if self.deployment_controller.menu_just_opened:
            self.deployment_controller.clear_just_opened_flag()
            return False

        if self.deployment_controller.menu_open:
            self.deployment_controller.close_menu()

        return True

    def _find_token_at_position(self, grid_pos: Tuple[int, int]):
        """Find token at grid position."""
        for player in self.game_state.players.values():
            for token_id in player.token_ids:
                token = self.game_state.get_token(token_id)
                if (token and token.is_alive and token.is_deployed and
                    token.position == grid_pos):
                    return token
        return None

    def _handle_token_click(self, clicked_token, current_player, grid_pos: Tuple[int, int]):
        """Handle clicking on a token."""
        if clicked_token.player_id == current_player.id:
            self._handle_own_token_click(clicked_token, grid_pos)
        else:
            self._handle_enemy_token_click(clicked_token)

    def _handle_own_token_click(self, clicked_token, grid_pos: Tuple[int, int]):
        """Handle clicking on own token."""
        if self.turn_phase != TurnPhase.MOVEMENT:
            return

        # Check if trying to stack on generator/crystal
        cell = self.game_state.board.get_cell_at(grid_pos)
        if (self.selected_token_id and grid_pos in self.valid_moves and
            cell and cell.cell_type in (CellType.GENERATOR, CellType.CRYSTAL)):
            self._try_move_to_cell(grid_pos)
        else:
            # Select this token for movement
            self.selected_token_id = clicked_token.id
            self.valid_moves = self.movement_system.get_valid_moves(
                clicked_token,
                self.game_state.board,
                tokens_dict=self.game_state.tokens,
            )
            self.renderer_2d.update_selection_visuals(
                self.selected_token_id, self.valid_moves, self.game_state
            )
            logger.debug(f"Selected token {clicked_token.id} at {clicked_token.position}")
            logger.debug(f"Valid moves: {len(self.valid_moves)}")

    def _handle_enemy_token_click(self, clicked_token):
        """Handle clicking on enemy token (attack)."""
        if self.turn_phase == TurnPhase.MOVEMENT and self.selected_token_id:
            self._try_attack(clicked_token)

    def _handle_empty_cell_click(self, grid_pos: Tuple[int, int], current_player):
        """Handle clicking on empty cell."""
        if self.selected_token_id and self.turn_phase == TurnPhase.MOVEMENT:
            self._try_move_selected_token(grid_pos)
        elif self.deployment_controller.selected_deploy_health and self.turn_phase == TurnPhase.MOVEMENT:
            self._try_deploy_token(grid_pos, current_player)

    def _try_move_selected_token(self, grid_pos: Tuple[int, int]):
        """Try to move selected token to grid position."""
        if grid_pos in self.valid_moves:
            self._try_move_to_cell(grid_pos)
        else:
            logger.warning(f"Cannot move to {grid_pos} - not a valid move")

    def _try_deploy_token(self, grid_pos: Tuple[int, int], current_player):
        """Try to deploy token at grid position."""
        if self.deployment_controller.is_valid_deployment_position(
            grid_pos, current_player.id, self.game_state
        ):
            deployed_token = self.action_handler.execute_deployment(
                current_player.id,
                self.deployment_controller.selected_deploy_health,
                grid_pos,
                self.window.ctx,
            )

            if deployed_token:
                self.deployment_controller.selected_deploy_health = None
                self.turn_phase = TurnPhase.ACTION
                logger.info("Deployment complete - you can attack or end turn")
        else:
            logger.warning("Cannot deploy outside your corner area")
            self.deployment_controller.selected_deploy_health = None

    def _handle_select_3d(self, grid_pos: Tuple[int, int]):
        """
        Handle selection in 3D mode using ray-cast grid position.
        Supports token selection, movement, attack, and deployment.

        Args:
            grid_pos: Grid coordinates (x, y)
        """
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        logger.debug(f"3D click at grid {grid_pos}")

        # Find token at clicked position
        clicked_token = self._find_token_at_position(grid_pos)

        if clicked_token:
            self._handle_token_click(clicked_token, current_player, grid_pos)
        else:
            self._handle_empty_cell_click(grid_pos, current_player)

    def _try_move_to_cell(self, cell: Tuple[int, int]):
        """
        Try to move the selected token to a cell.

        Args:
            cell: Target cell coordinates
        """
        if self.selected_token_id is None:
            return

        # Execute move through action handler
        success, final_position = self.action_handler.execute_move(
            self.selected_token_id, cell, self.mystery_animations, self.window.ctx
        )

        if success:
            # Clear selection
            self.selected_token_id = None
            self.valid_moves = []
            self.renderer_2d.update_selection_visuals(
                self.selected_token_id, self.valid_moves, self.game_state
            )

            # Can't attack after moving - go directly to end turn phase
            self.turn_phase = TurnPhase.END_TURN
            logger.info("Turn complete - press SPACE to end turn")

    def _try_attack(self, target_token):
        """
        Try to attack a target token.

        Args:
            target_token: Token to attack
        """
        if not self.selected_token_id:
            return

        # Execute attack through action handler
        success = self.action_handler.execute_attack(
            self.selected_token_id, target_token.id
        )

        if success:
            # Clear selection and move to end turn phase
            self.selected_token_id = None
            self.valid_moves = []
            self.renderer_2d.update_selection_visuals(
                self.selected_token_id, self.valid_moves, self.game_state
            )
            self.turn_phase = TurnPhase.END_TURN

    def _handle_cancel(self):
        """Handle cancel action."""
        if self.selected_token_id:
            logger.debug("Cancelled token selection")
            self.selected_token_id = None
            self.valid_moves = []
            self.renderer_2d.update_selection_visuals(
            self.selected_token_id, self.valid_moves, self.game_state
        )
        else:
            # Let deployment controller handle its own cancel logic
            self.deployment_controller.cancel_selection()

    def _handle_end_turn(self):
        """Handle end turn action."""
        # Clear selection
        self.selected_token_id = None
        self.valid_moves = []

        # Execute end turn through action handler
        self.action_handler.execute_end_turn(self.mystery_animations)

        # Reset to movement phase
        self.turn_phase = TurnPhase.MOVEMENT
