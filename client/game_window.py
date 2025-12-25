"""
Main Arcade-based game window for Race to the Crystal.

This module implements the primary game window using the Arcade framework,
replacing the Pygame-based implementation with GPU-accelerated rendering.
"""

import arcade
from arcade.shape_list import ShapeElementList, create_rectangle_outline, create_ellipse_outline
from typing import Optional, Tuple, List

from game.game_state import GameState
from game.movement import MovementSystem
from game.combat import CombatSystem
from shared.enums import TurnPhase
from shared.constants import (
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    BACKGROUND_COLOR,
    PLAYER_COLORS,
    CELL_SIZE,
)
from client.sprites.token_sprite import TokenSprite
from client.sprites.board_sprite import create_board_shapes


class GameWindow(arcade.Window):
    """
    Main Arcade window for the game.

    Handles rendering, input, and game loop using Arcade's event-driven architecture.
    """

    def __init__(self, game_state: GameState, width: int = DEFAULT_WINDOW_WIDTH,
                 height: int = DEFAULT_WINDOW_HEIGHT, title: str = "Race to the Crystal"):
        """
        Initialize the game window.

        Args:
            game_state: The game state to render
            width: Window width in pixels
            height: Window height in pixels
            title: Window title
        """
        super().__init__(width, height, title, resizable=True)

        # Game state
        self.game_state = game_state

        # Systems
        self.movement_system = MovementSystem()
        self.combat_system = CombatSystem()

        # Camera
        self.camera = arcade.camera.Camera2D()
        self.ui_camera = arcade.camera.Camera2D()  # For HUD (doesn't move with world)

        # Visual elements
        self.board_shapes = None  # ShapeElementList for board
        self.token_sprites = arcade.SpriteList()
        self.ui_sprites = arcade.SpriteList()
        self.selection_shapes = ShapeElementList()  # For selection highlights

        # Selection state
        self.selected_token_id: Optional[int] = None
        self.valid_moves: List[Tuple[int, int]] = []
        self.turn_phase = TurnPhase.MOVEMENT

        # Camera controls
        self.camera_speed = 10
        self.zoom_level = 1.0

        # Set background color
        arcade.set_background_color(BACKGROUND_COLOR)

        print(f"Arcade window initialized: {width}x{height}")

    def setup(self):
        """Set up the window after initialization."""
        self._create_board_sprites()
        self._create_token_sprites()
        self._create_ui_sprites()

        print("Window setup complete")

    def _create_board_sprites(self):
        """Create shapes for the board (grid, generators, crystal, mystery squares)."""
        self.board_shapes = create_board_shapes(self.game_state.board)

    def _create_token_sprites(self):
        """Create sprites for all tokens."""
        self.token_sprites.clear()

        for player in self.game_state.players.values():
            player_color = PLAYER_COLORS[player.color.value]

            for token_id in player.token_ids:
                token = self.game_state.get_token(token_id)
                if token and token.is_alive:
                    sprite = TokenSprite(token, player_color)
                    self.token_sprites.append(sprite)

    def _create_ui_sprites(self):
        """Create UI sprites (HUD, buttons, etc.)."""
        # For now, we'll use simple text rendering instead of complex UI sprites
        pass

    def _draw_hud(self):
        """Draw the heads-up display with game information."""
        # Get current player
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        # HUD background
        arcade.draw_lrbt_rectangle_filled(
            0, self.width,
            self.height - 80, self.height,
            (20, 20, 30, 200)  # Semi-transparent dark background
        )

        # Current player info
        player_color = PLAYER_COLORS[current_player.color.value]
        player_text = f"{current_player.name}'s Turn"
        arcade.draw_text(
            player_text,
            10, self.height - 30,
            player_color,
            font_size=24,
            bold=True
        )

        # Turn number
        turn_text = f"Turn {self.game_state.turn_number}"
        arcade.draw_text(
            turn_text,
            10, self.height - 60,
            (200, 200, 200),
            font_size=16
        )

        # Turn phase
        phase_text = f"Phase: {self.turn_phase.name}"
        arcade.draw_text(
            phase_text,
            200, self.height - 60,
            (200, 200, 200),
            font_size=16
        )

        # Instructions
        if self.turn_phase == TurnPhase.MOVEMENT:
            instruction = "Click a token to select, then click a cell to move"
        elif self.turn_phase == TurnPhase.ACTION:
            instruction = "Click an adjacent enemy to attack, or press SPACE to end turn"
        else:
            instruction = "Press SPACE to end turn"

        arcade.draw_text(
            instruction,
            self.width - 500, self.height - 60,
            (150, 150, 150),
            font_size=14
        )

    def _update_selection_visuals(self):
        """Update visual feedback for selection and valid moves."""
        self.selection_shapes = ShapeElementList()

        if self.selected_token_id:
            # Find selected token position
            selected_token = self.game_state.get_token(self.selected_token_id)
            if selected_token:
                # Draw selection highlight around selected token
                x = selected_token.position[0] * CELL_SIZE + CELL_SIZE // 2
                y = selected_token.position[1] * CELL_SIZE + CELL_SIZE // 2
                highlight = create_rectangle_outline(
                    x, y,
                    CELL_SIZE - 4, CELL_SIZE - 4,
                    (255, 255, 0, 255),  # Yellow
                    border_width=3
                )
                self.selection_shapes.append(highlight)

        # Draw valid move indicators
        for move in self.valid_moves:
            x = move[0] * CELL_SIZE + CELL_SIZE // 2
            y = move[1] * CELL_SIZE + CELL_SIZE // 2
            circle = create_ellipse_outline(
                x, y,
                CELL_SIZE // 3, CELL_SIZE // 3,
                (0, 255, 0, 180),  # Green
                border_width=2
            )
            self.selection_shapes.append(circle)

    def on_draw(self):
        """
        Render the screen.

        Called automatically by Arcade on each frame.
        """
        self.clear()

        # Draw world (with camera transform)
        with self.camera.activate():
            if self.board_shapes:
                self.board_shapes.draw()
            self.selection_shapes.draw()  # Draw selection highlights
            self.token_sprites.draw()

        # Draw UI (no camera transform)
        with self.ui_camera.activate():
            self.ui_sprites.draw()
            self._draw_hud()

    def on_update(self, delta_time: float):
        """
        Update game state and animations.

        Args:
            delta_time: Time since last update in seconds
        """
        # Update animations
        self.token_sprites.update()
        self.ui_sprites.update()

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int):
        """
        Handle mouse press events.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            button: Which button was pressed
            modifiers: Key modifiers (Shift, Ctrl, etc.)
        """
        if button == arcade.MOUSE_BUTTON_LEFT:
            # Convert screen coordinates to world coordinates
            world_x, world_y = self.camera.unproject((x, y))
            self._handle_select((world_x, world_y))

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int):
        """
        Handle mouse scroll events (for zooming).

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            scroll_x: Horizontal scroll amount
            scroll_y: Vertical scroll amount
        """
        if scroll_y > 0:
            self._zoom_in()
        elif scroll_y < 0:
            self._zoom_out()

    def on_key_press(self, symbol: int, modifiers: int):
        """
        Handle key press events.

        Args:
            symbol: Key that was pressed
            modifiers: Key modifiers (Shift, Ctrl, etc.)
        """
        # Camera panning
        if symbol == arcade.key.W or symbol == arcade.key.UP:
            self._pan_camera(0, self.camera_speed)
        elif symbol == arcade.key.S or symbol == arcade.key.DOWN:
            self._pan_camera(0, -self.camera_speed)
        elif symbol == arcade.key.A or symbol == arcade.key.LEFT:
            self._pan_camera(-self.camera_speed, 0)
        elif symbol == arcade.key.D or symbol == arcade.key.RIGHT:
            self._pan_camera(self.camera_speed, 0)

        # Zoom
        elif symbol == arcade.key.PLUS or symbol == arcade.key.EQUAL:
            self._zoom_in()
        elif symbol == arcade.key.MINUS:
            self._zoom_out()

        # Game controls
        elif symbol == arcade.key.SPACE or symbol == arcade.key.ENTER:
            self._handle_end_turn()
        elif symbol == arcade.key.ESCAPE:
            self._handle_cancel()

        # Quit
        elif symbol == arcade.key.Q and (modifiers & arcade.key.MOD_CTRL):
            arcade.close_window()

    def _pan_camera(self, dx: float, dy: float):
        """
        Pan the camera by the given amount.

        Args:
            dx: Change in x
            dy: Change in y
        """
        self.camera.position = (
            self.camera.position[0] + dx,
            self.camera.position[1] + dy
        )

    def _zoom_in(self):
        """Zoom in the camera."""
        self.zoom_level = min(2.0, self.zoom_level * 1.1)
        self.camera.zoom = self.zoom_level

    def _zoom_out(self):
        """Zoom out the camera."""
        self.zoom_level = max(0.5, self.zoom_level / 1.1)
        self.camera.zoom = self.zoom_level

    def _handle_select(self, world_pos: Tuple[float, float]):
        """
        Handle selection at world position.

        Args:
            world_pos: Position in world coordinates
        """
        # Convert world coordinates to grid coordinates
        grid_x = int(world_pos[0] // CELL_SIZE)
        grid_y = int(world_pos[1] // CELL_SIZE)

        # Get current player
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        # Check if clicked on a token
        clicked_token = None
        for player in self.game_state.players.values():
            for token in player.tokens.values():
                if token.is_alive and token.position == (grid_x, grid_y):
                    clicked_token = token
                    break
            if clicked_token:
                break

        if clicked_token:
            # Clicked on a token
            if clicked_token.player_id == current_player.id:
                # Own token - select it for movement
                if self.turn_phase == TurnPhase.MOVEMENT:
                    self.selected_token_id = clicked_token.id
                    self.valid_moves = self.movement_system.get_valid_moves(
                        clicked_token,
                        self.game_state.board
                    )
                    self._update_selection_visuals()
                    print(f"Selected token {clicked_token.id} at {clicked_token.position}")
                    print(f"Valid moves: {len(self.valid_moves)}")
            else:
                # Enemy token - try to attack if in action phase
                if self.turn_phase == TurnPhase.ACTION and self.selected_token_id:
                    self._try_attack(clicked_token)
        else:
            # Clicked on empty cell - try to move
            if self.selected_token_id and self.turn_phase == TurnPhase.MOVEMENT:
                if (grid_x, grid_y) in self.valid_moves:
                    self._try_move_to_cell((grid_x, grid_y))
                else:
                    print(f"Cannot move to ({grid_x}, {grid_y}) - not a valid move")

    def _try_move_to_cell(self, cell: Tuple[int, int]):
        """
        Try to move the selected token to a cell.

        Args:
            cell: Target cell coordinates
        """
        token = self.game_state.get_token(self.selected_token_id)
        if not token:
            return

        old_pos = token.position

        # Move the token
        success = self.game_state.move_token(self.selected_token_id, cell)

        if success:
            print(f"Moved token {self.selected_token_id} from {old_pos} to {cell}")

            # Update sprite position
            for sprite in self.token_sprites:
                if isinstance(sprite, TokenSprite) and sprite.token.id == self.selected_token_id:
                    sprite.update_position(cell[0], cell[1])
                    break

            # Clear selection
            self.selected_token_id = None
            self.valid_moves = []
            self._update_selection_visuals()

            # Move to action phase
            self.turn_phase = TurnPhase.ACTION

    def _try_attack(self, target_token):
        """
        Try to attack a target token.

        Args:
            target_token: Token to attack
        """
        if not self.selected_token_id:
            return

        attacker = self.game_state.get_token(self.selected_token_id)
        if not attacker:
            return

        # Check if adjacent
        if not self.combat_system.is_adjacent(attacker.position, target_token.position):
            print("Target is not adjacent")
            return

        # Perform attack
        result = self.combat_system.attack(attacker, target_token)

        print(f"Token {attacker.id} attacked token {target_token.id}: {result}")

        # Update token sprite health or remove if killed
        for sprite in self.token_sprites:
            if isinstance(sprite, TokenSprite) and sprite.token.id == target_token.id:
                if target_token.is_alive:
                    sprite.update_health()
                else:
                    self.token_sprites.remove(sprite)
                    self.game_state.board.clear_occupant(target_token.position)
                break

        # Clear selection and move to end turn phase
        self.selected_token_id = None
        self.valid_moves = []
        self._update_selection_visuals()
        self.turn_phase = TurnPhase.END_TURN

    def _handle_cancel(self):
        """Handle cancel action."""
        if self.selected_token_id:
            print("Cancelled selection")
            self.selected_token_id = None
            self.valid_moves = []
            self._update_selection_visuals()

    def _handle_end_turn(self):
        """Handle end turn action."""
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        print(f"Ending turn for {current_player.name}")

        # Clear selection
        self.selected_token_id = None
        self.valid_moves = []

        # Advance to next player
        self.game_state.end_turn()

        # Reset to movement phase
        self.turn_phase = TurnPhase.MOVEMENT
        self.game_state.turn_phase = TurnPhase.MOVEMENT

        next_player = self.game_state.get_current_player()
        if next_player:
            print(f"Turn {self.game_state.turn_number}: {next_player.name}'s turn")
