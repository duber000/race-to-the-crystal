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
from client.ui.lobby_view import LobbyView
from client.ui.network_game_view import NetworkGameView
from client.ui.victory_view import VictoryView, VictoryViewSimple
from client.ui.game_browser_view import GameBrowserView
from client.ui.async_arcade import AsyncWindow, schedule_async
from client.client_main import setup_game_state
from client.game_window import GameWindow
from client.network_client import NetworkClient
from network.messages import ClientType
from shared.constants import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MenuGameWindow(AsyncWindow):
    """
    Main window that manages menu and game views with async support.

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
        self.lobby_view: Optional[LobbyView] = None
        self.network_game_view: Optional[NetworkGameView] = None

        # Network client (when connected)
        self.network_client: Optional[NetworkClient] = None

        # Game window reference (when game is active)
        self.game_window: Optional[GameWindow] = None

        logger.info("Menu game window initialized with async support")

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

        # Create network client and connect
        schedule_async(
            self._connect_and_create_game(player_name, host, port, game_name or "My Game")
        )

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
            f"Showing game browser: player={player_name}, {host}:{port}"
        )

        # Show game browser to select which game to join
        browser_view = GameBrowserView(player_name, host, port, self.main_menu)
        browser_view.on_game_selected = lambda game_id: self._join_selected_game(
            browser_view, game_id
        )
        self.show_view(browser_view)

    def _join_selected_game(self, browser_view: GameBrowserView, game_id: str):
        """
        Join a selected game from the browser.

        Args:
            browser_view: The browser view (contains network client)
            game_id: ID of game to join
        """
        logger.info(f"Joining selected game: {game_id[:8]}")

        # Take ownership of the network client from browser
        self.network_client = browser_view.network_client
        browser_view.network_client = None  # Prevent cleanup

        # Join the game
        schedule_async(self._join_game_async(game_id))

    async def _join_game_async(self, game_id: str):
        """
        Async task to join a game.

        Args:
            game_id: ID of game to join
        """
        try:
            if not self.network_client:
                logger.error("No network client available")
                self.show_view(self.main_menu)
                return

            # Join the game
            logger.info(f"Joining game {game_id[:8]}...")
            success = await self.network_client.join_game(game_id)

            if not success:
                logger.error("Failed to join game")
                await self.network_client.disconnect()
                self.show_view(self.main_menu)
                return

            # Show lobby view
            self._show_lobby(is_host=False)

        except Exception as e:
            logger.error(f"Error joining game: {e}", exc_info=True)
            if self.network_client:
                await self.network_client.disconnect()
            self.show_view(self.main_menu)

    async def _connect_and_create_game(
        self,
        player_name: str,
        host: str,
        port: int,
        game_name: str
    ):
        """
        Connect to server and create a game.

        Args:
            player_name: Player name
            host: Server host
            port: Server port
            game_name: Name for the game
        """
        try:
            # Create network client
            self.network_client = NetworkClient(player_name, ClientType.HUMAN)

            # Connect to server
            logger.info(f"Connecting to server {host}:{port}...")
            success = await self.network_client.connect(host, port)

            if not success:
                logger.error("Failed to connect to server")
                # TODO: Show error dialog
                self.show_view(self.main_menu)
                return

            # Create game
            logger.info(f"Creating game '{game_name}'...")
            success = await self.network_client.create_game(game_name, max_players=4)

            if not success:
                logger.error("Failed to create game")
                await self.network_client.disconnect()
                self.show_view(self.main_menu)
                return

            # Show lobby view
            self._show_lobby(is_host=True)

        except Exception as e:
            logger.error(f"Error connecting/creating game: {e}", exc_info=True)
            self.show_view(self.main_menu)

    def _show_lobby(self, is_host: bool = False):
        """
        Show the lobby view.

        Args:
            is_host: True if this player is the host
        """
        if not self.network_client:
            logger.error("Cannot show lobby: No network client")
            return

        # Create lobby view
        self.lobby_view = LobbyView(self.network_client, is_host=is_host)

        # Set up callbacks
        self.lobby_view.on_game_start = self._start_network_game
        self.lobby_view.on_leave = self._leave_lobby

        # Show lobby
        self.show_view(self.lobby_view)
        logger.info("Showing lobby view")

    def _start_network_game(self, game_data: dict):
        """
        Start the network game (called from lobby when game starts).

        Args:
            game_data: Game start data from server
        """
        logger.info("Starting network game from lobby")

        # Create network game view
        self.network_game_view = NetworkGameView(self.network_client)

        # Set up callbacks
        self.network_game_view.on_game_end = self._handle_game_end
        self.network_game_view.on_disconnect = self._handle_network_disconnect

        # Show game view
        self.show_view(self.network_game_view)

    def _leave_lobby(self):
        """Leave the lobby and return to main menu."""
        logger.info("Leaving lobby")

        # Disconnect from server
        if self.network_client:
            schedule_async(self.network_client.disconnect())
            self.network_client = None

        # Return to main menu
        self.show_view(self.main_menu)

    def _handle_game_end(self, winner_name: str):
        """
        Handle game ending.

        Args:
            winner_name: Name of the winner
        """
        logger.info(f"Game ended! Winner: {winner_name}")

        # Show victory screen
        victory_view = VictoryViewSimple(winner_name)
        victory_view.on_return_to_menu = lambda: self.show_view(self.main_menu)
        self.show_view(victory_view)

    def _handle_network_disconnect(self):
        """Handle disconnection from network game."""
        logger.warning("Disconnected from network game")

        # TODO: Show reconnection dialog or error message
        # For now, return to main menu
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
