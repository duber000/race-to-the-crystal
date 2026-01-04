"""
Input handling and routing for the game view.

This module handles all input events (mouse, keyboard, text) and coordinates
with other controllers to execute game actions.
"""

from typing import List, Optional, Set, Tuple

import arcade

from client.audio_manager import AudioManager
from client.camera_controller import CameraController
from client.deployment_menu_controller import DeploymentMenuController
from client.game_action_handler import GameActionHandler
from client.renderer_2d import Renderer2D
from client.renderer_3d import Renderer3D
from client.ui.arcade_ui import UIManager
from game.game_state import GameState
from game.movement import MovementSystem
from shared.constants import CELL_SIZE
from shared.enums import CellType, TurnPhase
from shared.logging_config import setup_logger

logger = setup_logger(__name__)


class InputHandler:
    """
    Handles all input events and coordinates actions with game systems.

    This class manages:
    - Mouse events (motion, press, release, scroll)
    - Keyboard events (key press, text input)
    - Selection state (selected tokens, valid moves)
    - Input routing to appropriate handlers
    """

    def __init__(
        self,
        game_state: GameState,
        camera_controller: CameraController,
        deployment_controller: DeploymentMenuController,
        ui_manager: UIManager,
        action_handler: GameActionHandler,
        renderer_2d: Renderer2D,
        renderer_3d: Renderer3D,
        movement_system: MovementSystem,
        audio_manager: AudioManager,
    ):
        """
        Initialize the input handler.

        Args:
            game_state: Game state reference
            camera_controller: Camera controller for coordinate conversion
            deployment_controller: Deployment menu controller
            ui_manager: UI manager for UI interactions
            action_handler: Action handler for executing game actions
            renderer_2d: 2D renderer for updating visuals
            renderer_3d: 3D renderer for checking availability
            movement_system: Movement system for calculating valid moves
            audio_manager: Audio manager for music controls
        """
        self.game_state = game_state
        self.camera_controller = camera_controller
        self.deployment_controller = deployment_controller
        self.ui_manager = ui_manager
        self.action_handler = action_handler
        self.renderer_2d = renderer_2d
        self.renderer_3d = renderer_3d
        self.movement_system = movement_system
        self.audio_manager = audio_manager

        # Selection state
        self.selected_token_id: Optional[int] = None
        self.valid_moves: Set[Tuple[int, int]] = set()
        self.turn_phase = TurnPhase.MOVEMENT

        # Mystery animations reference (will be set by GameView)
        self.mystery_animations = {}

    def set_mystery_animations(self, mystery_animations: dict):
        """Set reference to mystery animations dict."""
        self.mystery_animations = mystery_animations

    def handle_mouse_motion(self, x: int, y: int, dx: int, dy: int, window) -> bool:
        """
        Handle mouse motion for UI hover effects and mouse-look in 3D mode.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            dx: Change in x
            dy: Change in y
            window: Arcade window reference

        Returns:
            True if event was handled, False otherwise
        """
        # Handle mouse-look in 3D mode
        if self.camera_controller.handle_mouse_motion(x, y, dx, dy, window):
            return True  # Mouse-look handled, skip UI hover effects

        # Normal UI hover effects
        self.ui_manager.handle_mouse_motion(x, y)
        return True

    def handle_mouse_press(
        self, x: int, y: int, button: int, modifiers: int, window
    ) -> bool:
        """
        Handle mouse press events with support for 2D and 3D picking.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            button: Which button was pressed
            modifiers: Key modifiers (Shift, Ctrl, etc.)
            window: Arcade window reference

        Returns:
            True if event was handled, False otherwise
        """
        if (
            button == arcade.MOUSE_BUTTON_RIGHT
            and self.camera_controller.camera_mode == "3D"
        ):
            # Activate mouse-look in 3D mode
            self.camera_controller.activate_mouse_look(x, y, window)
            return True

        if button == arcade.MOUSE_BUTTON_LEFT:
            # Check UI first (prevents click-through)
            ui_action = self.ui_manager.handle_mouse_click(x, y)
            if ui_action == "end_turn":
                self._handle_end_turn()
                return True
            elif ui_action == "cancel":
                self._handle_cancel()
                return True

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
                grid_pos = self.camera_controller.screen_to_grid_3d(
                    x, y, window.width, window.height
                )

            # Check if there's a token at the click position
            if grid_pos and self.game_state.board.is_valid_position(
                grid_pos[0], grid_pos[1]
            ):
                for player in self.game_state.players.values():
                    for token_id in player.token_ids:
                        token = self.game_state.get_token(token_id)
                        if (
                            token
                            and token.is_alive
                            and token.is_deployed
                            and token.position == grid_pos
                        ):
                            clicked_on_token = True
                            break
                    if clicked_on_token:
                        break

            # Check corner menu if open (UI-based menu) - do this before indicator check
            if self.deployment_controller.menu_open and current_player:
                reserve_counts = self.game_state.get_reserve_token_counts(
                    current_player.id
                )
                selected_health = self.deployment_controller.handle_menu_click(
                    (x, y), current_player, reserve_counts
                )
                if selected_health:
                    # Clear any existing token selection to prevent conflicts
                    self.selected_token_id = None
                    self.valid_moves = set()
                    self.renderer_2d.update_selection_visuals(
                        self.selected_token_id, self.valid_moves, self.game_state
                    )
                    return True

            # Check if clicking on R hexagon to open menu - but NOT if clicking on a token
            if (
                not clicked_on_token
                and not self.deployment_controller.menu_open
                and self.deployment_controller.is_click_on_indicator(
                    x, y, current_player
                )
            ):
                if current_player and self.turn_phase == TurnPhase.MOVEMENT:
                    self.deployment_controller.open_menu()
                    return True

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

            return True

        return False

    def handle_mouse_release(
        self, x: int, y: int, button: int, modifiers: int, window
    ) -> bool:
        """
        Handle mouse release events.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            button: Which button was released
            modifiers: Key modifiers (Shift, Ctrl, etc.)
            window: Arcade window reference

        Returns:
            True if event was handled, False otherwise
        """
        if (
            button == arcade.MOUSE_BUTTON_RIGHT
            and self.camera_controller.camera_mode == "3D"
        ):
            # Deactivate mouse-look in 3D mode
            self.camera_controller.deactivate_mouse_look(window)
            return True

        return False

    def handle_mouse_scroll(self, scroll_y: float) -> bool:
        """
        Handle mouse scroll events (for zooming).

        Args:
            scroll_y: Vertical scroll amount

        Returns:
            True if event was handled, False otherwise
        """
        if scroll_y > 0:
            self.camera_controller.zoom_in()
        elif scroll_y < 0:
            self.camera_controller.zoom_out()
        return True

    def handle_key_press(
        self, symbol: int, modifiers: int, chat_widget, window
    ) -> bool:
        """
        Handle key press events.

        Args:
            symbol: Key that was pressed
            modifiers: Key modifiers (Shift, Ctrl, etc.)
            chat_widget: Chat widget reference (or None)
            window: Arcade window reference

        Returns:
            True if event was handled, False otherwise
        """
        # Handle chat widget input first
        if chat_widget:
            if chat_widget.on_key_press(symbol, modifiers):
                return True  # Chat widget handled the input

        # Camera panning
        if symbol == arcade.key.W or symbol == arcade.key.UP:
            self.camera_controller.pan(0, self.camera_controller.camera_speed)
            return True
        elif symbol == arcade.key.S or symbol == arcade.key.DOWN:
            self.camera_controller.pan(0, -self.camera_controller.camera_speed)
            return True
        elif symbol == arcade.key.A or symbol == arcade.key.LEFT:
            self.camera_controller.pan(-self.camera_controller.camera_speed, 0)
            return True
        elif symbol == arcade.key.D or symbol == arcade.key.RIGHT:
            self.camera_controller.pan(self.camera_controller.camera_speed, 0)
            return True

        # Zoom
        elif symbol == arcade.key.PLUS or symbol == arcade.key.EQUAL:
            self.camera_controller.zoom_in()
            return True
        elif symbol == arcade.key.MINUS:
            self.camera_controller.zoom_out()
            return True

        # Game controls
        elif symbol == arcade.key.SPACE or symbol == arcade.key.ENTER:
            self._handle_end_turn()
            return True
        elif symbol == arcade.key.ESCAPE:
            self._handle_cancel()
            return True

        # Music toggle
        elif symbol == arcade.key.M:
            self.audio_manager.toggle_music()
            # Update generator hums to respect captured state when resuming
            if self.audio_manager.music_playing:
                self.audio_manager.update_generator_hums(self.game_state.generators)
            return True

        # 3D View controls
        elif symbol == arcade.key.V:
            # Toggle between 2D and 3D views (only if 3D rendering is available)
            self.camera_controller.toggle_mode(self.renderer_3d.is_available())
            return True

        elif symbol == arcade.key.TAB and self.camera_controller.camera_mode == "3D":
            # Cycle to next token
            self.camera_controller.cycle_controlled_token(self.game_state)
            return True

        elif symbol == arcade.key.Q and not (modifiers & arcade.key.MOD_CTRL):
            # Rotate camera left (only in 3D mode, and not Ctrl+Q which is quit)
            self.camera_controller.rotate_camera_left(self.game_state)
            return True

        elif symbol == arcade.key.E:
            # Rotate camera right (only in 3D mode)
            self.camera_controller.rotate_camera_right(self.game_state)
            return True

        # Quit
        elif symbol == arcade.key.Q and (modifiers & arcade.key.MOD_CTRL):
            window.close()
            return True

        return False

    def handle_text(self, text: str, chat_widget) -> bool:
        """
        Handle text input events.

        Args:
            text: Character(s) to add
            chat_widget: Chat widget reference (or None)

        Returns:
            True if event was handled, False otherwise
        """
        # Pass text input to chat widget if active
        if chat_widget and chat_widget.input_active:
            if chat_widget.on_text(text):
                return True  # Chat widget handled the text

        return False

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
                if (
                    token
                    and token.is_alive
                    and token.is_deployed
                    and token.position == grid_pos
                ):
                    return token
        return None

    def _handle_token_click(
        self, clicked_token, current_player, grid_pos: Tuple[int, int]
    ):
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
        if (
            self.selected_token_id
            and grid_pos in self.valid_moves
            and cell
            and cell.cell_type in (CellType.GENERATOR, CellType.CRYSTAL)
        ):
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
            logger.debug(
                f"Selected token {clicked_token.id} at {clicked_token.position}"
            )
            logger.debug(f"Valid moves: {len(self.valid_moves)}")

    def _handle_enemy_token_click(self, clicked_token):
        """Handle clicking on enemy token (attack)."""
        if self.turn_phase == TurnPhase.MOVEMENT and self.selected_token_id:
            self._try_attack(clicked_token)

    def _handle_empty_cell_click(self, grid_pos: Tuple[int, int], current_player):
        """Handle clicking on empty cell."""
        if self.selected_token_id and self.turn_phase == TurnPhase.MOVEMENT:
            self._try_move_selected_token(grid_pos)
        elif (
            self.deployment_controller.selected_deploy_health
            and self.turn_phase == TurnPhase.MOVEMENT
        ):
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
            # Get window context from renderer_3d
            ctx = getattr(self.renderer_3d, "ctx", None)
            # Assert selected_deploy_health is not None
            health = self.deployment_controller.selected_deploy_health
            assert health is not None
            deployed_token = self.action_handler.execute_deployment(
                current_player.id,
                health,
                grid_pos,
                ctx,
            )

            if deployed_token:
                self.deployment_controller.selected_deploy_health = None
                self.turn_phase = TurnPhase.ACTION
                logger.info("Deployment complete - you can attack or end turn")
            else:
                # In network mode, we assume the action was queued/sent successfully
                # Clear the UI selection state to prevent double-deploys
                self.deployment_controller.selected_deploy_health = None
                logger.debug("Deployment action sent to server - cleared UI state")
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

        # Get window context from renderer_3d
        ctx = getattr(self.renderer_3d, "ctx", None)

        # Execute move through action handler
        success, final_position = self.action_handler.execute_move(
            self.selected_token_id, cell, self.mystery_animations, ctx
        )

        if success:
            # Clear selection
            self.selected_token_id = None
            self.valid_moves = set()
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
            self.valid_moves = set()
            self.renderer_2d.update_selection_visuals(
                self.selected_token_id, self.valid_moves, self.game_state
            )
            self.turn_phase = TurnPhase.END_TURN

    def _handle_cancel(self):
        """Handle cancel action."""
        if self.selected_token_id:
            logger.debug("Cancelled token selection")
            self.selected_token_id = None
            self.valid_moves = set()
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
        self.valid_moves = set()

        # Execute end turn through action handler
        self.action_handler.execute_end_turn(self.mystery_animations)

        # Reset to movement phase
        self.turn_phase = TurnPhase.MOVEMENT
