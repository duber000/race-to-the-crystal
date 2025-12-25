"""Main rendering coordinator for the game."""

import pygame
from typing import Optional, List, Tuple

from game.game_state import GameState
from shared.constants import (
    BACKGROUND_COLOR,
    CELL_SIZE,
    BOARD_WIDTH,
    BOARD_HEIGHT,
)
from client.ui.camera import Camera
from client.ui.board_view import BoardView
from client.ui.token_view import TokenView
from client.ui.ui_elements import HUD


class Renderer:
    """
    Main rendering coordinator that manages all visual components.

    Handles:
    - Rendering the game board
    - Rendering tokens
    - Rendering the HUD
    - Managing the camera
    - Coordinating animations
    """

    def __init__(self, screen_width: int, screen_height: int):
        """
        Initialize the renderer.

        Args:
            screen_width: Width of the game window in pixels
            screen_height: Height of the game window in pixels
        """
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Initialize Pygame display
        pygame.init()
        pygame.display.set_caption("Race to the Crystal")
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.clock = pygame.time.Clock()

        # Calculate world dimensions
        world_width = BOARD_WIDTH * CELL_SIZE
        world_height = BOARD_HEIGHT * CELL_SIZE

        # Initialize camera
        self.camera = Camera(screen_width, screen_height, world_width, world_height)

        # Center camera on board
        self.camera.center_on(world_width / 2, world_height / 2)

        # Set initial zoom to fit board on screen
        zoom_x = (screen_width * 0.8) / world_width
        zoom_y = (screen_height * 0.8) / world_height
        initial_zoom = min(zoom_x, zoom_y)
        self.camera.set_zoom(initial_zoom)

        # Initialize view components (will be set when game state is available)
        self.board_view: Optional[BoardView] = None
        self.token_view = TokenView(CELL_SIZE)
        self.hud = HUD(screen_width, screen_height)

        # Delta time tracking
        self.dt = 0.0

    def set_game_state(self, game_state: GameState):
        """
        Set the game state to render.

        Args:
            game_state: The game state
        """
        if self.board_view is None:
            self.board_view = BoardView(game_state.board)

    def render(self, game_state: GameState):
        """
        Render the entire game scene.

        Args:
            game_state: Current game state to render
        """
        # Update delta time
        self.dt = self.clock.tick(60) / 1000.0  # Convert to seconds

        # Set game state if not already set
        self.set_game_state(game_state)

        # Clear screen
        self.screen.fill(BACKGROUND_COLOR)

        # Render game world (board and tokens)
        if self.board_view:
            self.board_view.render(self.screen, self.camera)

        self.token_view.render(self.screen, list(game_state.tokens.values()), list(game_state.players.values()), self.camera, self.dt)

        # Render HUD on top
        self.hud.render(self.screen, game_state)

        # Update display
        pygame.display.flip()

    def render_with_selection(self, game_state: GameState, selected_token_id: Optional[int], valid_moves: List[Tuple[int, int]]):
        """
        Render the game with a selected token and valid moves highlighted.

        Args:
            game_state: Current game state
            selected_token_id: ID of selected token
            valid_moves: List of valid move positions
        """
        # Update delta time
        self.dt = self.clock.tick(60) / 1000.0

        # Set game state if not already set
        self.set_game_state(game_state)

        # Clear screen
        self.screen.fill(BACKGROUND_COLOR)

        # Render game world
        if self.board_view:
            self.board_view.render(self.screen, self.camera)

        # Render valid moves
        if valid_moves:
            self.token_view.render_movement_range(self.screen, valid_moves, self.camera)

        # Set selected token
        self.token_view.set_selected_token(selected_token_id)

        # Render tokens
        self.token_view.render(self.screen, list(game_state.tokens.values()), list(game_state.players.values()), self.camera, self.dt)

        # Render HUD
        self.hud.render(self.screen, game_state)

        # Update display
        pygame.display.flip()

    def get_cell_at_mouse(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """
        Get the board cell at the mouse position.

        Args:
            mouse_pos: Mouse position in screen coordinates

        Returns:
            Cell coordinates (x, y) or None
        """
        if self.board_view:
            return self.board_view.get_cell_at_screen_pos(mouse_pos, self.camera)
        return None

    def get_token_at_mouse(self, mouse_pos: Tuple[int, int], game_state: GameState):
        """
        Get the token at the mouse position.

        Args:
            mouse_pos: Mouse position in screen coordinates
            game_state: Current game state

        Returns:
            Token at position or None
        """
        return self.token_view.get_token_at_screen_pos(mouse_pos, list(game_state.tokens.values()), self.camera)

    def start_move_animation(self, token_id: int, start_cell: Tuple[int, int], end_cell: Tuple[int, int], game_state: GameState):
        """
        Start a movement animation for a token.

        Args:
            token_id: ID of token to animate
            start_cell: Starting cell coordinates
            end_cell: Ending cell coordinates
            game_state: Current game state
        """
        token = next((t for t in game_state.tokens if t.id == token_id), None)
        if token:
            self.token_view.start_move_animation(token, start_cell, end_cell)

    def handle_zoom(self, zoom_in: bool):
        """
        Handle zoom in/out.

        Args:
            zoom_in: True to zoom in, False to zoom out
        """
        if zoom_in:
            self.camera.zoom_in(1.1)
        else:
            self.camera.zoom_out(1.1)

    def handle_pan(self, dx: float, dy: float):
        """
        Handle camera panning.

        Args:
            dx: Change in X position (screen pixels)
            dy: Change in Y position (screen pixels)
        """
        # Convert screen delta to world delta
        world_dx = -dx / self.camera.zoom
        world_dy = -dy / self.camera.zoom

        self.camera.pan(world_dx, world_dy)

    def center_on_cell(self, cell_x: int, cell_y: int):
        """
        Center camera on a specific cell.

        Args:
            cell_x: Cell X coordinate
            cell_y: Cell Y coordinate
        """
        if self.board_view:
            world_pos = self.board_view.get_cell_center_world(cell_x, cell_y)
            self.camera.center_on(*world_pos)

    def handle_mouse_motion(self, pos: Tuple[int, int]):
        """
        Handle mouse motion for HUD elements.

        Args:
            pos: Mouse position
        """
        self.hud.handle_mouse_motion(pos)

    def handle_mouse_click(self, pos: Tuple[int, int]) -> Optional[str]:
        """
        Handle mouse click for HUD elements.

        Args:
            pos: Mouse position

        Returns:
            Action string if a UI button was clicked, None otherwise
        """
        return self.hud.handle_mouse_click(pos)

    def quit(self):
        """Clean up and quit Pygame."""
        pygame.quit()
