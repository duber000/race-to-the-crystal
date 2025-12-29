"""
Main entry point with menu system for Race to the Crystal.

This is the new primary entry point that provides a main menu
for choosing between local and network games.
"""

import sys
import arcade
import asyncio
import logging
from typing import Optional

from client.ui.main_menu import MainMenuView, SettingsView, NetworkSetupView
from client.client_main import setup_game_state
from client.game_window import GameWindow
from shared.constants import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MenuGameWindow(arcade.Window):
    """
    Main window that manages menu and game views.

    This window handles transitions between:
    - Main menu
    - Settings
    - Local game
    - Network lobby/game
    """

    def __init__(self):
        """Initialize the menu game window."""
        super().__init__(
            DEFAULT_WINDOW_WIDTH,
            DEFAULT_WINDOW_HEIGHT,
            "Race to the Crystal",
            resizable=True
        )

        # Create menu views
        self.main_menu = MainMenuView()
        self.settings_view = SettingsView(self.main_menu)

        # Set up menu callbacks
        self.main_menu.on_local_game = self._start_local_game
        self.main_menu.on_host_game = self._show_host_setup
        self.main_menu.on_join_game = self._show_join_setup
        self.main_menu.on_settings = self._show_settings

        # Network views (created on demand)
        self.host_setup_view: Optional[NetworkSetupView] = None
        self.join_setup_view: Optional[NetworkSetupView] = None

        # Game window reference (when game is active)
        self.game_window: Optional[GameWindow] = None

        logger.info("Menu game window initialized")

    def setup(self):
        """Set up the initial view (main menu)."""
        self.show_view(self.main_menu)
        logger.info("Showing main menu")

    def _start_local_game(self, num_players: int, start_in_3d: bool):
        """
        Start a local hot-seat game.

        Args:
            num_players: Number of players (2-4)
            start_in_3d: Whether to start in 3D mode
        """
        logger.info(f"Starting local game: {num_players} players, 3D={start_in_3d}")

        # Set up game state
        game_state = setup_game_state(num_players)

        # Create game window view
        # Note: GameWindow is currently an arcade.Window, not a View
        # For now, we'll create a new window and switch to it
        # TODO: Refactor GameWindow to be a View instead of Window

        # Close this menu window
        self.close()

        # Create and run game window
        game_window = GameWindow(
            game_state,
            self.width,
            self.height,
            "Race to the Crystal - Local Game"
        )
        game_window.setup()

        # Set camera mode
        if start_in_3d:
            game_window.camera_mode = "3D"

        # The arcade.run() call from main() will continue with the new window
        logger.info("Local game window created")

    def _show_host_setup(self):
        """Show the host network game setup screen."""
        logger.info("Showing host setup")

        self.host_setup_view = NetworkSetupView(self.main_menu, is_host=True)
        self.host_setup_view.on_start_network_game = self._start_host_game
        self.show_view(self.host_setup_view)

    def _show_join_setup(self):
        """Show the join network game setup screen."""
        logger.info("Showing join setup")

        self.join_setup_view = NetworkSetupView(self.main_menu, is_host=False)
        self.join_setup_view.on_start_network_game = self._start_join_game
        self.show_view(self.join_setup_view)

    def _show_settings(self):
        """Show the settings screen."""
        logger.info("Showing settings")
        self.show_view(self.settings_view)

    def _start_host_game(
        self,
        player_name: str,
        host: str,
        port: int,
        game_name: Optional[str]
    ):
        """
        Start hosting a network game.

        Args:
            player_name: Player's display name
            host: Server host (should be localhost for hosting)
            port: Server port
            game_name: Name of the game to create
        """
        logger.info(
            f"Starting host game: player={player_name}, "
            f"port={port}, game='{game_name}'"
        )

        # TODO: Implement network game hosting
        # For now, show a placeholder message
        print("=" * 60)
        print("NETWORK HOSTING NOT YET IMPLEMENTED")
        print("=" * 60)
        print(f"Player: {player_name}")
        print(f"Port: {port}")
        print(f"Game Name: {game_name}")
        print("\nTo host a game, use:")
        print("  Terminal 1: uv run race-server")
        print("  Terminal 2: uv run race-ai-client --create 'Game Name'")
        print("=" * 60)

        # Return to main menu
        self.show_view(self.main_menu)

    def _start_join_game(
        self,
        player_name: str,
        host: str,
        port: int,
        game_name: Optional[str]
    ):
        """
        Join a network game.

        Args:
            player_name: Player's display name
            host: Server host
            port: Server port
            game_name: Not used for joining (None)
        """
        logger.info(
            f"Joining network game: player={player_name}, {host}:{port}"
        )

        # TODO: Implement network game joining
        # For now, show a placeholder message
        print("=" * 60)
        print("NETWORK JOINING NOT YET IMPLEMENTED")
        print("=" * 60)
        print(f"Player: {player_name}")
        print(f"Server: {host}:{port}")
        print("\nTo join a game, use:")
        print("  uv run race-ai-client --join <game-id>")
        print("=" * 60)

        # Return to main menu
        self.show_view(self.main_menu)


def main():
    """Main entry point with menu system."""
    print("=" * 60)
    print("Race to the Crystal - Main Menu")
    print("=" * 60)

    # Create and set up the menu window
    window = MenuGameWindow()
    window.setup()

    # Run the application
    arcade.run()


if __name__ == "__main__":
    main()
