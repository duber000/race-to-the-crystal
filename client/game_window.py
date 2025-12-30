"""
Main Arcade-based game window for Race to the Crystal.

This module implements the primary game window using the Arcade framework,
replacing the Pygame-based implementation with GPU-accelerated rendering.
"""

import arcade
from arcade.shape_list import (
    ShapeElementList,
    create_line,
)
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
from client.ui.arcade_ui import UIManager
from client.music_generator import generate_techno_music


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
    ):
        """
        Initialize the game view.

        Args:
            game_state: The game state to render
            start_in_3d: Whether to start in 3D mode
        """
        super().__init__()

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

        # Corner deployment menu
        self.corner_menu_open = False
        self.corner_menu_position: Optional[Tuple[int, int]] = None
        self.corner_menu_just_opened = False  # Flag to prevent immediate click-through
        self.selected_deploy_health: Optional[int] = (
            None  # Selected token type for deployment
        )

        # Camera controls
        self.camera_speed = 10
        self.zoom_level = 1.0

        # Mouse-look state for 3D mode
        self.mouse_look_active = False
        self.mouse_look_sensitivity = 0.2  # Mouse sensitivity for look around
        self.last_mouse_position = (0, 0)  # Track mouse position for delta calculation

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

        # 3D Rendering infrastructure
        self.camera_mode = "3D" if start_in_3d else "2D"  # Current view mode: "2D" or "3D"
        # camera_3d will be initialized in on_show_view() when window dimensions are available
        self.camera_3d = None
        self.board_3d = None  # Will be initialized in setup()
        self.tokens_3d = []  # List of Token3D instances
        self.shader_3d = None  # Shared shader for 3D rendering
        self.controlled_token_id: Optional[int] = None  # Token camera follows in 3D
        self.token_rotation = 0.0  # Camera rotation around token

        # UI Manager for panels and buttons (will be initialized in on_show_view)
        self.ui_manager = None

        # Background music
        self.background_music = None
        self.music_player = None
        self.music_volume = 0.3
        self.music_playing = True

        # Background color will be set in on_show_view()

    def on_show_view(self):
        """Called when this view is shown."""
        # Set background color
        arcade.set_background_color(BACKGROUND_COLOR)

        # Initialize components that need window dimensions
        self.camera_3d = FirstPersonCamera3D(self.window.width, self.window.height)
        self.ui_manager = UIManager(self.window.width, self.window.height)

        # Set up the game
        self.setup()

        print(f"Game view initialized: {self.window.width}x{self.window.height}")

    def on_hide_view(self):
        """Called when this view is hidden."""
        # Stop music when view is hidden
        if self.music_player and self.music_playing:
            self.music_player.pause()

        # Clean up OpenGL resources
        if self.board_3d is not None:
            self.board_3d.cleanup()
            self.board_3d = None

        for token_3d in self.tokens_3d:
            token_3d.cleanup()
        self.tokens_3d.clear()

    def _load_background_music(self):
        """Load and play background techno music."""
        music_path = "client/assets/music/techno.mp3"
        wav_path = "client/assets/music/techno.wav"

        try:
            # Try MP3 first
            self.background_music = arcade.Sound(music_path, streaming=True)
            if self.background_music:
                self.music_player = self.background_music.play(self.music_volume)
                print("Background music loaded and playing")
                return
        except FileNotFoundError:
            # Try WAV format
            try:
                self.background_music = arcade.Sound(wav_path, streaming=True)
                if self.background_music:
                    self.music_player = self.background_music.play(self.music_volume)
                    print("Background music loaded and playing")
                    return
            except FileNotFoundError:
                # Generate music if neither file exists
                print("No music file found, generating techno track...")
                try:
                    generate_techno_music(duration=30.0)
                    self.background_music = arcade.Sound(wav_path, streaming=True)
                    if self.background_music:
                        self.music_player = self.background_music.play(
                            self.music_volume
                        )
                        print("Generated background music playing")
                except Exception as e:
                    print(f"Error generating music: {e}")
        except Exception as e:
            print(f"Error loading background music: {e}")

    def _toggle_music(self):
        """Toggle background music on/off."""
        if self.music_player:
            if self.music_playing:
                self.music_player.pause()
                self.music_playing = False
                print("Music paused")
            else:
                self.music_player.play()
                self.music_playing = True
                print("Music playing")

    def setup(self):
        """Set up the window after initialization."""
        self._create_board_sprites()
        self._create_token_sprites()
        self._create_ui_sprites()
        self._create_3d_rendering()

        # Set up camera to fit entire board in view
        self._setup_camera_view()

        # Load and play background music
        self._load_background_music()

        # Build initial UI
        self.ui_manager.rebuild_visuals(self.game_state)

        print("Window setup complete")

    def _create_board_sprites(self):
        """Create shapes for the board (grid, generators, crystal, mystery squares)."""
        # Get crystal position
        crystal = self.game_state.crystal
        crystal_pos = crystal.position if crystal else None
        
        # Pass generators and crystal position for flowing line visualization
        self.board_shapes = create_board_shapes(
            self.game_state.board,
            generators=self.game_state.generators,
            crystal_pos=crystal_pos
        )

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
        try:
            # Clean up old 3D board if it exists
            if self.board_3d is not None:
                self.board_3d.cleanup()
                self.board_3d = None

            # Clean up old 3D tokens
            for token_3d in self.tokens_3d:
                token_3d.cleanup()
            self.tokens_3d.clear()

            # Get crystal position
            crystal = self.game_state.crystal
            crystal_pos = crystal.position if crystal else None

            # Create 3D board with generators and crystal position
            self.board_3d = Board3D(
                self.game_state.board,
                self.window.ctx,
                generators=self.game_state.generators,
                crystal_pos=crystal_pos
            )
            if self.board_3d.shader_program is None:
                print(
                    "WARNING: 3D shader compilation failed, 3D mode will not be available"
                )
                self.shader_3d = None
            else:
                self.shader_3d = self.board_3d.shader_program  # Reuse shader
                print("3D rendering initialized successfully")
        except Exception as e:
            print(f"ERROR: Failed to initialize 3D rendering: {e}")
            self.board_3d = None
            self.shader_3d = None
            return

        # Create 3D tokens
        for player in self.game_state.players.values():
            player_color = PLAYER_COLORS[player.color.value]

            for token_id in player.token_ids:
                token = self.game_state.get_token(token_id)
                if token and token.is_alive:
                    try:
                        token_3d = Token3D(token, player_color, self.window.ctx)
                        self.tokens_3d.append(token_3d)
                    except Exception as e:
                        print(f"ERROR: Failed to create 3D token {token_id}: {e}")

        print(f"Created {len(self.tokens_3d)} 3D tokens")

        # Don't auto-follow token - start with overview camera
        # Players can press TAB to cycle through tokens and start following
        # self.controlled_token_id remains None for free camera movement

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
        if self.selected_deploy_health:
            instruction = f"Selected {self.selected_deploy_health}hp token - click a corner position to deploy (ESC to cancel)"
        elif self.turn_phase == TurnPhase.MOVEMENT:
            if self.camera_mode == "3D":
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

    def _draw_corner_menu(self):
        """Draw the corner deployment menu with token type options (2D mode)."""
        if not self.corner_menu_position:
            return

        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        # Get reserve token counts
        counts = self.game_state.get_reserve_token_counts(current_player.id)

        grid_x, grid_y = self.corner_menu_position
        center_x = grid_x * CELL_SIZE + CELL_SIZE / 2
        center_y = grid_y * CELL_SIZE + CELL_SIZE / 2

        # Draw 4 options in a diamond pattern around the corner
        menu_distance = CELL_SIZE * 2
        options = [
            (10, center_x, center_y + menu_distance, counts[10]),  # Top
            (8, center_x + menu_distance, center_y, counts[8]),  # Right
            (6, center_x, center_y - menu_distance, counts[6]),  # Bottom
            (4, center_x - menu_distance, center_y, counts[4]),  # Left
        ]

        for health, x, y, count in options:
            if count > 0:
                # Draw available option in cyan
                arcade.draw_circle_filled(x, y, CELL_SIZE * 0.8, (0, 255, 255, 200))
                arcade.draw_circle_outline(x, y, CELL_SIZE * 0.8, (0, 255, 255), 3)
            else:
                # Draw unavailable option in dark gray
                arcade.draw_circle_filled(x, y, CELL_SIZE * 0.8, (50, 50, 50, 100))
                arcade.draw_circle_outline(x, y, CELL_SIZE * 0.8, (100, 100, 100), 2)

            # Draw health value
            arcade.draw_text(
                str(health),
                x,
                y,
                (255, 255, 255) if count > 0 else (100, 100, 100),
                font_size=20,
                bold=True,
                anchor_x="center",
                anchor_y="center",
            )

            # Draw count if available
            if count > 0:
                arcade.draw_text(
                    f"({count})",
                    x,
                    y - 15,
                    (200, 200, 200),
                    font_size=12,
                    anchor_x="center",
                    anchor_y="center",
                )

    def _draw_corner_menu_3d(self):
        """Draw the corner deployment menu as HUD overlay in 3D mode."""
        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        # Get reserve token counts
        counts = self.game_state.get_reserve_token_counts(current_player.id)

        # Draw menu in center of screen as HUD
        menu_width = 400
        menu_height = 200
        center_x = self.window.width / 2
        center_y = self.window.height / 2

        # Semi-transparent background (using lrbt API for Arcade 3.0+)
        left = center_x - menu_width / 2
        right = center_x + menu_width / 2
        top = center_y + menu_height / 2
        bottom = center_y - menu_height / 2

        arcade.draw_lrbt_rectangle_filled(
            left, right, bottom, top,
            (20, 20, 40, 220),
        )
        arcade.draw_lrbt_rectangle_outline(
            left, right, bottom, top, (0, 255, 255), 3
        )

        # Title
        arcade.draw_text(
            "SELECT TOKEN TYPE",
            center_x,
            center_y + 70,
            (0, 255, 255),
            font_size=18,
            bold=True,
            anchor_x="center",
            anchor_y="center",
        )

        # Options in a grid
        options = [
            (10, center_x - 100, center_y + 20, counts[10]),
            (8, center_x + 100, center_y + 20, counts[8]),
            (6, center_x - 100, center_y - 30, counts[6]),
            (4, center_x + 100, center_y - 30, counts[4]),
        ]

        for health, x, y, count in options:
            # Store click areas for hit detection
            if not hasattr(self, "_3d_menu_areas"):
                self._3d_menu_areas = {}

            if count > 0:
                color = (0, 255, 255)
                text_color = (255, 255, 255)
            else:
                color = (100, 100, 100)
                text_color = (100, 100, 100)

            # Draw option box (using lrbt API for Arcade 3.0+)
            box_left = x - 35
            box_right = x + 35
            box_top = y + 25
            box_bottom = y - 25

            arcade.draw_lrbt_rectangle_filled(
                box_left, box_right, box_bottom, box_top, (30, 30, 60, 200)
            )
            arcade.draw_lrbt_rectangle_outline(
                box_left, box_right, box_bottom, box_top, color, 2
            )

            # Store clickable area
            self._3d_menu_areas[health] = (box_left, box_right, box_bottom, box_top)

            # Draw health value
            arcade.draw_text(
                str(health),
                x,
                y + 5,
                text_color,
                font_size=16,
                bold=True,
                anchor_x="center",
                anchor_y="center",
            )

            # Draw count
            arcade.draw_text(
                f"({count})" if count > 0 else "N/A",
                x,
                y - 10,
                text_color,
                font_size=12,
                anchor_x="center",
                anchor_y="center",
            )

        # Instruction
        arcade.draw_text(
            "Click a token type (ESC to cancel)",
            center_x,
            center_y - 70,
            (200, 200, 200),
            font_size=12,
            anchor_x="center",
            anchor_y="center",
        )

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
                            points[j][0],
                            points[j][1],
                            points[j + 1][0],
                            points[j + 1][1],
                            (255, 255, 0, alpha),
                            max(1, 4 - i // 2),
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
                        points[j][0],
                        points[j][1],
                        points[j + 1][0],
                        points[j + 1][1],
                        (255, 255, 100, 255),
                        4,
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
                        points[j][0],
                        points[j][1],
                        points[j + 1][0],
                        points[j + 1][1],
                        (0, 255, 0, alpha),
                        max(1, 3 - i // 2),
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
                    points[j][0],
                    points[j][1],
                    points[j + 1][0],
                    points[j + 1][1],
                    (100, 255, 100, 255),
                    3,
                )
                self.selection_shapes.append(line)

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

        if self.camera_mode == "2D":
            # 2D top-down rendering
            with self.camera.activate():
                if self.board_shapes:
                    self.board_shapes.draw()
                self.selection_shapes.draw()
                self.token_sprites.draw()
        else:
            # 3D first-person rendering - enable depth test and blending
            self.window.ctx.enable(self.window.ctx.DEPTH_TEST)
            self.window.ctx.enable(self.window.ctx.BLEND)
            self.window.ctx.disable(self.window.ctx.CULL_FACE)

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

            # Reset state for UI
            self.window.ctx.disable(self.window.ctx.DEPTH_TEST)

        # Draw UI (no camera transform) - always in 2D
        with self.ui_camera.activate():
            self.ui_sprites.draw()
            self._draw_hud()
            self.ui_manager.draw()

        # Draw corner menu if open (in world coordinates)
        # Works in both 2D and 3D modes
        if self.corner_menu_open and self.corner_menu_position:
            if self.camera_mode == "2D":
                with self.camera.activate():
                    self._draw_corner_menu()
            else:
                # In 3D mode, draw menu in UI space (HUD-based)
                self._draw_corner_menu_3d()

    def on_update(self, delta_time: float):
        """
        Update game state and animations.

        Args:
            delta_time: Time since last update in seconds
        """
        # Loop background music if it has ended
        if self.background_music and self.music_player:
            position = self.background_music.get_stream_position(self.music_player)
            length = self.background_music.get_length()
            if position == 0.0 and self.music_playing:
                self.music_player.play()

        # Update animations
        self.token_sprites.update()
        self.ui_sprites.update()

    def on_resize(self, width: int, height: int):
        """
        Handle window resize events.

        Args:
            width: New window width
            height: New window height
        """
        # Check if initialization is complete (ui_manager exists)
        if hasattr(self, 'ui_manager') and self.ui_manager:
            # Update UI manager layout
            self.ui_manager.update_layout(width, height)
            self.ui_manager.rebuild_visuals(self.game_state)

            # Update camera setup to refit board
            self._setup_camera_view()

            # Update 3D camera aspect ratio if it exists
            if hasattr(self, 'camera_3d') and self.camera_3d:
                self.camera_3d = FirstPersonCamera3D(width, height)

            print(f"Game view resized to {width}x{height}")

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
        if not hasattr(self, 'camera_mode') or not hasattr(self, 'mouse_look_active'):
            return
            
        # Handle mouse-look in 3D mode
        if self.camera_mode == "3D" and self.mouse_look_active:
            # Apply mouse movement to camera rotation
            yaw_delta = -dx * self.mouse_look_sensitivity
            pitch_delta = -dy * self.mouse_look_sensitivity
            
            # Update camera rotation
            self.camera_3d.rotate(yaw_delta=yaw_delta, pitch_delta=pitch_delta)
            
            # If following a token, update the token rotation to match camera yaw
            if self.controlled_token_id:
                self.token_rotation = self.camera_3d.yaw
            
            # Store current mouse position for next frame
            self.last_mouse_position = (x, y)

            # Hide cursor during mouse-look for better immersion
            self.window.set_mouse_visible(False)

            return  # Skip UI hover effects during mouse-look
        else:
            # Normal UI hover effects
            self.ui_manager.handle_mouse_motion(x, y)
            self.window.set_mouse_visible(True)

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
        if not hasattr(self, 'camera_mode'):
            return
            
        if button == arcade.MOUSE_BUTTON_RIGHT and self.camera_mode == "3D":
            # Activate mouse-look in 3D mode
            self.mouse_look_active = True
            self.last_mouse_position = (x, y)
            self.window.set_mouse_visible(False)
            print("Mouse-look activated")
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

            # Check corner menu if open (in either 2D or 3D mode)
            current_player = self.game_state.get_current_player()
            if self.corner_menu_open and current_player:
                if self.camera_mode == "2D":
                    # 2D world-space menu
                    world_pos = self.camera.unproject((x, y))
                    handled = self._handle_corner_menu_click((world_pos[0], world_pos[1]), current_player.id)
                    if handled:
                        return
                else:
                    # 3D HUD-space menu
                    handled = self._handle_corner_menu_click_3d((x, y), current_player.id)
                    if handled:
                        return

            # No UI clicked, proceed with world interaction
            if self.camera_mode == "2D":
                # 2D picking using camera unproject
                world_pos = self.camera.unproject((x, y))
                self._handle_select((world_pos[0], world_pos[1]))
            else:
                # 3D ray casting
                ray_origin, ray_direction = self.camera_3d.screen_to_ray(
                    x, y, self.window.width, self.window.height
                )

                # Intersect with board plane (z=0)
                intersection = self.camera_3d.ray_intersect_plane(
                    ray_origin, ray_direction, plane_z=0.0
                )

                if intersection:
                    world_x, world_y = intersection
                    grid_x, grid_y = self.camera_3d.world_to_grid(world_x, world_y)
                    print(f"3D click detected at grid ({grid_x}, {grid_y})")  # Debug
                    self._handle_select_3d((grid_x, grid_y))
                else:
                    print(f"3D ray casting: no intersection with board plane")  # Debug

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
        if not hasattr(self, 'camera_mode') or not hasattr(self, 'mouse_look_active'):
            return
            
        if button == arcade.MOUSE_BUTTON_RIGHT and self.camera_mode == "3D":
            # Deactivate mouse-look in 3D mode
            self.mouse_look_active = False
            self.window.set_mouse_visible(True)
            print("Mouse-look deactivated")

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

        # Music toggle
        elif symbol == arcade.key.M:
            self._toggle_music()

        # 3D View controls
        elif symbol == arcade.key.V:
            # Check if initialization is complete
            if not hasattr(self, 'camera_mode') or not hasattr(self, 'board_3d') or not hasattr(self, 'shader_3d'):
                return
                
            # Toggle between 2D and 3D views (only if 3D rendering is available)
            if self.camera_mode == "2D":
                # Trying to enter 3D mode
                if self.board_3d is None or self.shader_3d is None:
                    print("ERROR: 3D rendering failed to initialize. Cannot switch to 3D mode.")
                    return
                self.camera_mode = "3D"
                print(f"Camera mode: {self.camera_mode}")
                # Don't auto-select a token - let players use TAB to follow if desired
                print("Press TAB to cycle through and follow your tokens")
            else:
                # Exiting 3D mode back to 2D
                self.camera_mode = "2D"
                print(f"Camera mode: {self.camera_mode}")

        elif symbol == arcade.key.TAB and hasattr(self, 'camera_mode') and self.camera_mode == "3D":
            # Cycle to next token
            self._cycle_controlled_token()

        elif symbol == arcade.key.Q and not (modifiers & arcade.key.MOD_CTRL):
            # Rotate camera left (only in 3D mode, and not Ctrl+Q which is quit)
            if hasattr(self, 'camera_mode') and self.camera_mode == "3D":
                self.token_rotation -= 15.0
                # Update camera position immediately
                if self.controlled_token_id:
                    token = self.game_state.get_token(self.controlled_token_id)
                    if token and token.is_alive:
                        self.camera_3d.follow_token(token.position, self.token_rotation)
                        print(f"Camera rotation: {self.token_rotation}, following token {token.id} at {token.position}")
                    else:
                        print(f"Camera rotation: {self.token_rotation}, but no valid token to follow")
                else:
                    print(f"Camera rotation: {self.token_rotation}, but no controlled token selected")

        elif symbol == arcade.key.E:
            # Rotate camera right (only in 3D mode)
            if self.camera_mode == "3D":
                self.token_rotation += 15.0
                # Update camera position immediately
                if self.controlled_token_id:
                    token = self.game_state.get_token(self.controlled_token_id)
                    if token and token.is_alive:
                        self.camera_3d.follow_token(token.position, self.token_rotation)
                        print(f"Camera rotation: {self.token_rotation}, following token {token.id} at {token.position}")
                    else:
                        print(f"Camera rotation: {self.token_rotation}, but no valid token to follow")
                else:
                    print(f"Camera rotation: {self.token_rotation}, but no controlled token selected")

        # Quit
        elif symbol == arcade.key.Q and (modifiers & arcade.key.MOD_CTRL):
            self.window.close()

    def _pan_camera(self, dx: float, dy: float):
        """
        Pan the camera by the given amount.

        Args:
            dx: Change in x
            dy: Change in y
        """
        self.camera.position = (
            self.camera.position[0] + dx,
            self.camera.position[1] + dy,
        )

    def _setup_camera_view(self):
        """Set up camera to show the entire board, accounting for HUD at top."""
        from shared.constants import BOARD_WIDTH, BOARD_HEIGHT, CELL_SIZE

        # Calculate board dimensions in pixels
        board_pixel_width = BOARD_WIDTH * CELL_SIZE
        board_pixel_height = BOARD_HEIGHT * CELL_SIZE

        # Account for HUD at top (80 pixels)
        HUD_HEIGHT = 80
        playable_height = self.window.height - HUD_HEIGHT

        # Calculate zoom to fit board in playable area
        zoom_x = self.window.width / board_pixel_width
        zoom_y = playable_height / board_pixel_height
        optimal_zoom = min(zoom_x, zoom_y) * 0.95  # 95% to add small margin

        # Apply zoom
        self.zoom_level = optimal_zoom
        self.camera.zoom = self.zoom_level

        # Center camera on board center, shifted down to account for HUD
        board_center_x = board_pixel_width / 2
        # Offset camera downward by half the HUD height (in world coordinates)
        hud_offset_world = (HUD_HEIGHT / 2) / self.zoom_level
        board_center_y = (board_pixel_height / 2) - hud_offset_world
        self.camera.position = (board_center_x, board_center_y)

        print(
            f"Camera setup: zoom={self.zoom_level:.2f}, position=({board_center_x:.1f}, {board_center_y:.1f}), HUD offset={hud_offset_world:.1f}"
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
        alive_tokens = []
        for token_id in current_player.token_ids:
            token = self.game_state.get_token(token_id)
            if token and token.is_alive:
                alive_tokens.append(token_id)

        if not alive_tokens:
            return

        # Find current index
        try:
            if self.controlled_token_id is not None:
                current_index = alive_tokens.index(self.controlled_token_id)
                next_index = (current_index + 1) % len(alive_tokens)
            else:
                next_index = 0
        except ValueError:
            next_index = 0

        # Set new controlled token
        self.controlled_token_id = alive_tokens[next_index]
        token = self.game_state.get_token(self.controlled_token_id)
        if token:
            print(f"Switched to token {self.controlled_token_id} at {token.position}")
        else:
            print(f"Switched to token {self.controlled_token_id} (token not found)")

    def _is_player_corner(self, grid_pos: Tuple[int, int], player_id: str) -> bool:
        """Check if a position is in the player's deployment zone (corner + adjacent cells)."""
        player = self.game_state.get_player(player_id)
        if not player:
            return False

        player_index = player.color.value
        deployable_positions = self.game_state.board.get_deployable_positions(
            player_index
        )
        return grid_pos in deployable_positions

    def _handle_corner_menu_click(
        self, world_pos: Tuple[float, float], player_id: str
    ) -> bool:
        """
        Handle click on corner menu to select a token type for deployment (2D mode).

        Args:
            world_pos: Click position in world coordinates
            player_id: Current player ID

        Returns:
            True if a token type was selected
        """
        if not self.corner_menu_position:
            return False

        grid_x, grid_y = self.corner_menu_position
        center_x = grid_x * CELL_SIZE + CELL_SIZE / 2
        center_y = grid_y * CELL_SIZE + CELL_SIZE / 2

        # Menu option positions (same as in _draw_corner_menu)
        menu_distance = CELL_SIZE * 2
        options = [
            (10, center_x, center_y + menu_distance),  # Top
            (8, center_x + menu_distance, center_y),  # Right
            (6, center_x, center_y - menu_distance),  # Bottom
            (4, center_x - menu_distance, center_y),  # Left
        ]

        click_x, click_y = world_pos

        # Check which option was clicked
        click_radius = CELL_SIZE * 0.8
        for health, option_x, option_y in options:
            distance = ((click_x - option_x) ** 2 + (click_y - option_y) ** 2) ** 0.5
            if distance <= click_radius:
                # Check if player has this token type in reserve
                reserve_counts = self.game_state.get_reserve_token_counts(player_id)
                if reserve_counts.get(health, 0) > 0:
                    # Select this token type for deployment
                    self.selected_deploy_health = health
                    print(
                        f"Selected {health}hp token for deployment - click a position to deploy"
                    )

                    # Close the menu
                    self.corner_menu_open = False
                    self.corner_menu_position = None
                    self.corner_menu_just_opened = False

                    return True
                else:
                    print(f"No {health}hp tokens available in reserve")
                    return False

        return False

    def _handle_corner_menu_click_3d(self, screen_pos: Tuple[int, int], player_id: str) -> bool:
        """
        Handle click on HUD corner menu in 3D mode.

        Args:
            screen_pos: Click position in screen coordinates
            player_id: Current player ID

        Returns:
            True if a token type was selected
        """
        if not hasattr(self, "_3d_menu_areas"):
            return False

        click_x, click_y = screen_pos

        # Check which menu option was clicked
        for health, (left, right, bottom, top) in self._3d_menu_areas.items():
            if left <= click_x <= right and bottom <= click_y <= top:
                # Check if player has this token type in reserve
                reserve_counts = self.game_state.get_reserve_token_counts(player_id)
                if reserve_counts.get(health, 0) > 0:
                    # Select this token type for deployment
                    self.selected_deploy_health = health
                    print(
                        f"Selected {health}hp token for deployment - click a position to deploy"
                    )

                    # Close the menu
                    self.corner_menu_open = False
                    self.corner_menu_position = None
                    self.corner_menu_just_opened = False

                    return True
                else:
                    print(f"No {health}hp tokens available in reserve")
                    return False

        return False

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

        # Check if clicked on corner menu option
        if (
            self.corner_menu_open
            and self.corner_menu_position
            and not self.corner_menu_just_opened
        ):
            deployed = self._handle_corner_menu_click(world_pos, current_player.id)
            if deployed:
                return

        # Reset the just-opened flag after first frame
        if self.corner_menu_just_opened:
            self.corner_menu_just_opened = False
            return  # Don't process any other clicks this frame

        # Close corner menu if clicking elsewhere
        if self.corner_menu_open:
            self.corner_menu_open = False
            self.corner_menu_position = None
            self.corner_menu_just_opened = False

        # Check if clicked on a token
        clicked_token = None
        for player in self.game_state.players.values():
            for token_id in player.token_ids:
                token = self.game_state.get_token(token_id)
                if (
                    token
                    and token.is_alive
                    and token.is_deployed
                    and token.position == (grid_x, grid_y)
                ):
                    clicked_token = token
                    break
            if clicked_token:
                break

        if clicked_token:
            # Clicked on a token
            if clicked_token.player_id == current_player.id:
                # Own token - select it for movement or attack
                if self.turn_phase == TurnPhase.MOVEMENT:
                    self.selected_token_id = clicked_token.id
                    self.valid_moves = self.movement_system.get_valid_moves(
                        clicked_token, self.game_state.board
                    )
                    self._update_selection_visuals()
                    print(
                        f"Selected token {clicked_token.id} at {clicked_token.position}"
                    )
                    print(f"Valid moves: {len(self.valid_moves)}")
            else:
                # Enemy token - try to attack (can't attack if you already moved)
                if self.turn_phase == TurnPhase.MOVEMENT and self.selected_token_id:
                    self._try_attack(clicked_token)
        else:
            # Clicked on empty cell
            if self.selected_token_id and self.turn_phase == TurnPhase.MOVEMENT:
                # First priority: try to move selected token
                if (grid_x, grid_y) in self.valid_moves:
                    self._try_move_to_cell((grid_x, grid_y))
                else:
                    print(f"Cannot move to ({grid_x}, {grid_y}) - not a valid move")
            elif self.selected_deploy_health and self.turn_phase == TurnPhase.MOVEMENT:
                # Second priority: deploy selected token type if one is selected
                if self._is_player_corner((grid_x, grid_y), current_player.id):
                    deployed_token = self.game_state.deploy_token(
                        current_player.id, self.selected_deploy_health, (grid_x, grid_y)
                    )

                    if deployed_token:
                        print(
                            f"Deployed {self.selected_deploy_health}hp token to {(grid_x, grid_y)}"
                        )

                        # Create sprite for the deployed token
                        from client.sprites.token_sprite import TokenSprite

                        player_color = PLAYER_COLORS[current_player.color.value]
                        sprite = TokenSprite(deployed_token, player_color)
                        self.token_sprites.append(sprite)

                        # Clear selection
                        self.selected_deploy_health = None

                        # Transition to ACTION phase after deploying
                        self.turn_phase = TurnPhase.ACTION
                        print("Deployment complete - you can attack or end turn")

                        # Update UI to reflect state changes
                        self.ui_manager.rebuild_visuals(self.game_state)
                    else:
                        print(
                            f"Cannot deploy to {(grid_x, grid_y)} - position occupied or invalid"
                        )
                else:
                    print("Cannot deploy outside your corner area")
                    self.selected_deploy_health = None
            elif (
                self._is_player_corner((grid_x, grid_y), current_player.id)
                and self.turn_phase == TurnPhase.MOVEMENT
                and not self.selected_token_id
            ):
                # Third priority: open deployment menu if clicking on starting corner
                player_index = current_player.color.value
                starting_corner = self.game_state.board.get_starting_position(
                    player_index
                )

                if (grid_x, grid_y) == starting_corner:
                    # Clicked on the starting corner - open menu to select token type
                    self.corner_menu_open = True
                    self.corner_menu_position = (grid_x, grid_y)
                    self.corner_menu_just_opened = True  # Prevent click-through
                    print(f"Opened deployment menu - select a token type")

    def _handle_select_3d(self, grid_pos: Tuple[int, int]):
        """
        Handle selection in 3D mode using ray-cast grid position.
        Supports token selection, movement, attack, and deployment.

        Args:
            grid_pos: Grid coordinates (x, y)
        """
        grid_x, grid_y = grid_pos

        current_player = self.game_state.get_current_player()
        if not current_player:
            return

        print(f"3D click at grid ({grid_x}, {grid_y})")

        # Check if clicked on a token
        clicked_token = None
        for player in self.game_state.players.values():
            for token_id in player.token_ids:
                token = self.game_state.get_token(token_id)
                if (
                    token
                    and token.is_alive
                    and token.is_deployed
                    and token.position == (grid_x, grid_y)
                ):
                    clicked_token = token
                    break
            if clicked_token:
                break

        if clicked_token:
            # Clicked on a token
            if clicked_token.player_id == current_player.id:
                # Own token - select it for movement or attack
                if self.turn_phase == TurnPhase.MOVEMENT:
                    self.selected_token_id = clicked_token.id
                    self.valid_moves = self.movement_system.get_valid_moves(
                        clicked_token, self.game_state.board
                    )
                    self._update_selection_visuals()
                    print(
                        f"Selected token {clicked_token.id} at {clicked_token.position}"
                    )
                    print(f"Valid moves: {len(self.valid_moves)}")
            else:
                # Enemy token - try to attack (can't attack if you already moved)
                if self.turn_phase == TurnPhase.MOVEMENT and self.selected_token_id:
                    self._try_attack(clicked_token)
        else:
            # Clicked on empty cell
            if self.selected_token_id and self.turn_phase == TurnPhase.MOVEMENT:
                # First priority: try to move selected token
                if (grid_x, grid_y) in self.valid_moves:
                    self._try_move_to_cell((grid_x, grid_y))
                else:
                    print(f"Cannot move to ({grid_x}, {grid_y}) - not a valid move")
            elif self.selected_deploy_health and self.turn_phase == TurnPhase.MOVEMENT:
                # Second priority: deploy selected token type if one is selected
                if self._is_player_corner((grid_x, grid_y), current_player.id):
                    deployed_token = self.game_state.deploy_token(
                        current_player.id, self.selected_deploy_health, (grid_x, grid_y)
                    )

                    if deployed_token:
                        print(
                            f"Deployed {self.selected_deploy_health}hp token to {(grid_x, grid_y)}"
                        )

                        # Create sprite for the deployed token
                        from client.sprites.token_sprite import TokenSprite

                        player_color = PLAYER_COLORS[current_player.color.value]
                        sprite = TokenSprite(deployed_token, player_color)
                        self.token_sprites.append(sprite)

                        # Create 3D token
                        try:
                            token_3d = Token3D(deployed_token, player_color, self.window.ctx)
                            self.tokens_3d.append(token_3d)
                        except Exception as e:
                            print(f"Warning: Failed to create 3D token: {e}")

                        # Clear selection
                        self.selected_deploy_health = None

                        # Transition to ACTION phase after deploying
                        self.turn_phase = TurnPhase.ACTION
                        print("Deployment complete - you can attack or end turn")

                        # Update UI to reflect state changes
                        self.ui_manager.rebuild_visuals(self.game_state)
                    else:
                        print(
                            f"Cannot deploy to {(grid_x, grid_y)} - position occupied or invalid"
                        )
                else:
                    print("Cannot deploy outside your corner area")
                    self.selected_deploy_health = None
            elif (
                self._is_player_corner((grid_x, grid_y), current_player.id)
                and self.turn_phase == TurnPhase.MOVEMENT
                and not self.selected_token_id
            ):
                # Third priority: open deployment menu if clicking on starting corner
                player_index = current_player.color.value
                starting_corner = self.game_state.board.get_starting_position(
                    player_index
                )

                if (grid_x, grid_y) == starting_corner:
                    # Clicked on the starting corner - open menu to select token type
                    self.corner_menu_open = True
                    self.corner_menu_position = (grid_x, grid_y)
                    self.corner_menu_just_opened = True  # Prevent click-through
                    print(f"Opened deployment menu - select a token type")

    def _try_move_to_cell(self, cell: Tuple[int, int]):
        """
        Try to move the selected token to a cell.

        Args:
            cell: Target cell coordinates
        """
        if self.selected_token_id is None:
            return

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
                if (
                    isinstance(sprite, TokenSprite)
                    and sprite.token.id == self.selected_token_id
                ):
                    sprite.update_position(cell[0], cell[1])
                    break

            # Clear selection
            self.selected_token_id = None
            self.valid_moves = []
            self._update_selection_visuals()

            # Can't attack after moving - go directly to end turn phase
            self.turn_phase = TurnPhase.END_TURN
            print("Turn complete - press SPACE to end turn")

            # Update UI to reflect state changes
            self.ui_manager.rebuild_visuals(self.game_state)

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
        if not self.movement_system.is_adjacent(
            attacker.position, target_token.position
        ):
            print("Target is not adjacent")
            return

        # Perform attack
        result = CombatSystem.resolve_combat(attacker, target_token)

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

        # Update UI to reflect state changes
        self.ui_manager.rebuild_visuals(self.game_state)

    def _handle_cancel(self):
        """Handle cancel action."""
        if self.selected_token_id:
            print("Cancelled token selection")
            self.selected_token_id = None
            self.valid_moves = []
            self._update_selection_visuals()
        elif self.selected_deploy_health:
            print("Cancelled deployment selection")
            self.selected_deploy_health = None
        elif self.corner_menu_open:
            print("Closed deployment menu")
            self.corner_menu_open = False
            self.corner_menu_position = None
            self.corner_menu_just_opened = False

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

        # Update UI to reflect new turn
        self.ui_manager.rebuild_visuals(self.game_state)
