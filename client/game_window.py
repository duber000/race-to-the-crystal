"""
Main Arcade-based game window for Race to the Crystal.

This module implements the primary game window using the Arcade framework,
replacing the Pygame-based implementation with GPU-accelerated rendering.
"""

import arcade
from arcade.shape_list import ShapeElementList, create_rectangle_outline, create_ellipse_outline, create_line
from typing import Optional, Tuple, List
import math

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
from client.camera_3d import FirstPersonCamera3D
from client.board_3d import Board3D
from client.token_3d import Token3D


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

        # HUD Text objects (for performance)
        self.player_text = arcade.Text(
            "",
            10, 0,  # Y will be updated in _draw_hud
            (255, 255, 255),
            font_size=24,
            bold=True
        )
        self.turn_text = arcade.Text(
            "",
            10, 0,
            (200, 200, 200),
            font_size=16
        )
        self.phase_text = arcade.Text(
            "",
            200, 0,
            (200, 200, 200),
            font_size=16
        )
        self.instruction_text = arcade.Text(
            "",
            0, 0,  # X and Y will be updated in _draw_hud
            (150, 150, 150),
            font_size=14
        )

        # 3D Rendering infrastructure
        self.camera_mode = "2D"  # Current view mode: "2D" or "3D"
        self.camera_3d = FirstPersonCamera3D(width, height)
        self.board_3d = None  # Will be initialized in setup()
        self.tokens_3d = []  # List of Token3D instances
        self.shader_3d = None  # Shared shader for 3D rendering
        self.controlled_token_id: Optional[int] = None  # Token camera follows in 3D
        self.token_rotation = 0.0  # Camera rotation around token

        # Set background color
        arcade.set_background_color(BACKGROUND_COLOR)

        print(f"Arcade window initialized: {width}x{height}")

    def setup(self):
        """Set up the window after initialization."""
        self._create_board_sprites()
        self._create_token_sprites()
        self._create_ui_sprites()
        self._create_3d_rendering()

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

    def _create_3d_rendering(self):
        """Initialize 3D rendering components."""
        # Create 3D board
        self.board_3d = Board3D(self.game_state.board, self.ctx)
        self.shader_3d = self.board_3d.shader_program  # Reuse shader

        # Create 3D tokens
        self.tokens_3d.clear()
        for player in self.game_state.players.values():
            player_color = PLAYER_COLORS[player.color.value]

            for token_id in player.token_ids:
                token = self.game_state.get_token(token_id)
                if token and token.is_alive:
                    token_3d = Token3D(token, player_color, self.ctx)
                    self.tokens_3d.append(token_3d)

        # Set initial controlled token (first token of current player)
        current_player = self.game_state.get_current_player()
        if current_player and len(current_player.token_ids) > 0:
            self.controlled_token_id = current_player.token_ids[0]
            token = self.game_state.get_token(self.controlled_token_id)
            if token:
                self.camera_3d.follow_token(token.position, self.token_rotation)

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
        self.player_text.text = f"{current_player.name}'s Turn"
        self.player_text.color = player_color
        self.player_text.y = self.height - 30
        self.player_text.draw()

        # Turn number
        self.turn_text.text = f"Turn {self.game_state.turn_number}"
        self.turn_text.y = self.height - 60
        self.turn_text.draw()

        # Turn phase
        self.phase_text.text = f"Phase: {self.turn_phase.name}"
        self.phase_text.y = self.height - 60
        self.phase_text.draw()

        # Instructions
        if self.turn_phase == TurnPhase.MOVEMENT:
            instruction = "Click a token to select, then click a cell to move"
        elif self.turn_phase == TurnPhase.ACTION:
            instruction = "Click an adjacent enemy to attack, or press SPACE to end turn"
        else:
            instruction = "Press SPACE to end turn"

        self.instruction_text.text = instruction
        self.instruction_text.x = self.width - 500
        self.instruction_text.y = self.height - 60
        self.instruction_text.draw()

    def _update_selection_visuals(self):
        """Update visual feedback for selection and valid moves with vector glow."""
        self.selection_shapes = ShapeElementList()

        if self.selected_token_id:
            # Find selected token position
            selected_token = self.game_state.get_token(self.selected_token_id)
            if selected_token:
                # Draw pulsing selection highlight with glow
                x = selected_token.position[0] * CELL_SIZE + CELL_SIZE // 2
                y = selected_token.position[1] * CELL_SIZE + CELL_SIZE // 2
                size = CELL_SIZE * 0.8
                half = size / 2

                # Glow layers for selection
                for i in range(6, 0, -1):
                    alpha = int(180 / (i + 1))
                    glow_size = size + (i * 4)
                    glow_half = glow_size / 2
                    points = [
                        (x - glow_half, y - glow_half),
                        (x + glow_half, y - glow_half),
                        (x + glow_half, y + glow_half),
                        (x - glow_half, y + glow_half),
                        (x - glow_half, y - glow_half),
                    ]
                    for j in range(len(points) - 1):
                        line = create_line(
                            points[j][0], points[j][1],
                            points[j + 1][0], points[j + 1][1],
                            (255, 255, 0, alpha), max(1, 4 - i // 2)
                        )
                        self.selection_shapes.append(line)

                # Bright main selection square
                points = [
                    (x - half, y - half),
                    (x + half, y - half),
                    (x + half, y + half),
                    (x - half, y + half),
                    (x - half, y - half),
                ]
                for j in range(len(points) - 1):
                    line = create_line(
                        points[j][0], points[j][1],
                        points[j + 1][0], points[j + 1][1],
                        (255, 255, 100, 255), 4
                    )
                    self.selection_shapes.append(line)

        # Draw valid move indicators as glowing circles
        for move in self.valid_moves:
            x = move[0] * CELL_SIZE + CELL_SIZE // 2
            y = move[1] * CELL_SIZE + CELL_SIZE // 2
            radius = CELL_SIZE * 0.3
            segments = 12

            # Glow layers
            for i in range(4, 0, -1):
                alpha = int(120 / (i + 1))
                glow_radius = radius + (i * 3)
                points = []
                for seg in range(segments + 1):
                    angle = (seg / segments) * 2 * math.pi
                    px = x + glow_radius * math.cos(angle)
                    py = y + glow_radius * math.sin(angle)
                    points.append((px, py))

                for j in range(len(points) - 1):
                    line = create_line(
                        points[j][0], points[j][1],
                        points[j + 1][0], points[j + 1][1],
                        (0, 255, 0, alpha), max(1, 3 - i // 2)
                    )
                    self.selection_shapes.append(line)

            # Bright main circle
            points = []
            for seg in range(segments + 1):
                angle = (seg / segments) * 2 * math.pi
                px = x + radius * math.cos(angle)
                py = y + radius * math.sin(angle)
                points.append((px, py))

            for j in range(len(points) - 1):
                line = create_line(
                    points[j][0], points[j][1],
                    points[j + 1][0], points[j + 1][1],
                    (100, 255, 100, 255), 3
                )
                self.selection_shapes.append(line)

    def on_draw(self):
        """
        Render the screen.

        Called automatically by Arcade on each frame.
        """
        self.clear()

        if self.camera_mode == "2D":
            # 2D top-down rendering
            with self.camera.activate():
                if self.board_shapes:
                    self.board_shapes.draw()
                self.selection_shapes.draw()  # Draw selection highlights
                self.token_sprites.draw()
        else:
            # 3D first-person rendering
            if self.board_3d and self.shader_3d:
                # Update camera to follow controlled token
                if self.controlled_token_id:
                    token = self.game_state.get_token(self.controlled_token_id)
                    if token and token.is_alive:
                        self.camera_3d.follow_token(token.position, self.token_rotation)

                # Draw 3D board
                self.board_3d.draw(self.camera_3d)

                # Draw 3D tokens
                for token_3d in self.tokens_3d:
                    if token_3d.token.is_alive:
                        token_3d.draw(self.camera_3d, self.shader_3d)

        # Draw UI (no camera transform) - always in 2D
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
        Handle mouse press events with support for 2D and 3D picking.

        Args:
            x: Mouse x coordinate
            y: Mouse y coordinate
            button: Which button was pressed
            modifiers: Key modifiers (Shift, Ctrl, etc.)
        """
        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.camera_mode == "2D":
                # 2D picking using camera unproject
                world_pos = self.camera.unproject((x, y))
                self._handle_select((world_pos[0], world_pos[1]))
            else:
                # 3D ray casting
                ray_origin, ray_direction = self.camera_3d.screen_to_ray(
                    x, y, self.width, self.height
                )

                # Intersect with board plane (z=0)
                intersection = self.camera_3d.ray_intersect_plane(
                    ray_origin, ray_direction, plane_z=0.0
                )

                if intersection:
                    world_x, world_y = intersection
                    grid_x, grid_y = self.camera_3d.world_to_grid(world_x, world_y)
                    self._handle_select_3d((grid_x, grid_y))

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

        # 3D View controls
        elif symbol == arcade.key.V:
            # Toggle between 2D and 3D views
            self.camera_mode = "3D" if self.camera_mode == "2D" else "2D"
            print(f"Camera mode: {self.camera_mode}")
            if self.camera_mode == "3D" and not self.controlled_token_id:
                # Set initial controlled token when entering 3D
                current_player = self.game_state.get_current_player()
                if current_player and len(current_player.token_ids) > 0:
                    self.controlled_token_id = current_player.token_ids[0]

        elif symbol == arcade.key.TAB and self.camera_mode == "3D":
            # Cycle to next token
            self._cycle_controlled_token()

        elif symbol == arcade.key.Q and not (modifiers & arcade.key.MOD_CTRL):
            # Rotate camera left (only in 3D mode, and not Ctrl+Q which is quit)
            if self.camera_mode == "3D":
                self.token_rotation -= 15.0
                print(f"Camera rotation: {self.token_rotation}")

        elif symbol == arcade.key.E:
            # Rotate camera right (only in 3D mode)
            if self.camera_mode == "3D":
                self.token_rotation += 15.0
                print(f"Camera rotation: {self.token_rotation}")

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

    def _cycle_controlled_token(self):
        """Cycle to the next alive token of the current player."""
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        # Get all alive tokens
        alive_tokens = [
            token_id for token_id in current_player.token_ids
            if self.game_state.get_token(token_id) and self.game_state.get_token(token_id).is_alive
        ]

        if not alive_tokens:
            return

        # Find current index
        try:
            current_index = alive_tokens.index(self.controlled_token_id)
            next_index = (current_index + 1) % len(alive_tokens)
        except ValueError:
            next_index = 0

        # Set new controlled token
        self.controlled_token_id = alive_tokens[next_index]
        print(f"Switched to token {self.controlled_token_id}")

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
            for token_id in player.token_ids:
                token = self.game_state.get_token(token_id)
                if token and token.is_alive and token.position == (grid_x, grid_y):
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

    def _handle_select_3d(self, grid_pos: Tuple[int, int]):
        """
        Handle selection in 3D mode using ray-cast grid position.

        Args:
            grid_pos: Grid coordinates (x, y)
        """
        grid_x, grid_y = grid_pos

        # For now, just use the same logic as 2D
        # Convert grid to world position for compatibility
        world_x = grid_x * CELL_SIZE + CELL_SIZE / 2
        world_y = grid_y * CELL_SIZE + CELL_SIZE / 2

        self._handle_select((world_x, world_y))

        print(f"3D click at grid ({grid_x}, {grid_y})")

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
