"""
Main entry point with menu system for Race to the Crystal.

This is the new primary entry point that provides a main menu
for choosing between local and network games.
"""

import sys
import arcade
import arcade.gui
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
from client.game_window import GameView
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

    def _show_error_dialog(self, title: str, message: str):
        """
        Show an error dialog to the user.

        Args:
            title: Dialog title
            message: Error message to display
        """
        # Create a simple error dialog using arcade.gui
        message_box = arcade.gui.UIMessageBox(
            width=400,
            height=200,
            message_text=message,
            buttons=["OK"]
        )

        # Add the message box to the current view's UI manager
        if hasattr(self.current_view, 'manager'):
            self.current_view.manager.add(message_box)

        logger.warning(f"Error dialog: {title} - {message}")

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

        # Create game view (now using View architecture)
        game_view = GameView(game_state, start_in_3d=start_in_3d)

        # Show the game view (no need to close window or create new one!)
        self.show_view(game_view)
        logger.info("Local game view shown")

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
        game_name: Optional[str],
        max_players: int = 4
    ):
        """
        Start hosting a network game.

        Args:
            player_name: Player's display name
            host: Server host (should be localhost for hosting)
            port: Server port
            game_name: Name of the game to create
            max_players: Maximum number of players (2-4)
        """
        logger.info(
            f"Starting host game: player={player_name}, "
            f"port={port}, game='{game_name}', max_players={max_players}"
        )

        # Create network client and connect
        schedule_async(
            self._connect_and_create_game(player_name, host, port, game_name or "My Game", max_players)
        )

    def _start_join_game(
        self,
        player_name: str,
        host: str,
        port: int,
        game_name: Optional[str],
        max_players: int = 4
    ):
        """
        Join a network game.

        Args:
            player_name: Player's display name
            host: Server host
            port: Server port
            game_name: Not used for joining (None)
            max_players: Not used for joining
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
        game_name: str,
        max_players: int = 4
    ):
        """
        Connect to server and create a game.

        Args:
            player_name: Player name
            host: Server host
            port: Server port
            game_name: Name for the game
            max_players: Maximum number of players (2-4)
        """
        try:
            # Create network client
            self.network_client = NetworkClient(player_name, ClientType.HUMAN)

            # Connect to server
            logger.info(f"Connecting to server {host}:{port}...")
            success = await self.network_client.connect(host, port)

            if not success:
                logger.error("Failed to connect to server")
                self._show_error_dialog(
                    "Connection Failed",
                    f"Could not connect to server at {host}:{port}\n\nPlease check the server address and try again."
                )
                self.show_view(self.main_menu)
                return

            # Create game
            logger.info(f"Creating game '{game_name}' with max {max_players} players...")
            success = await self.network_client.create_game(game_name, max_players=max_players)

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
            game_data: Game start data from server (may include initial_game_state)
        """
        logger.info("Starting network game from lobby")

        # Extract initial game state if provided
        initial_state = None
        if "initial_game_state" in game_data:
            from game.game_state import GameState
            try:
                game_state_dict = game_data["initial_game_state"]
                logger.info(f"Game state dict has keys: {list(game_state_dict.keys())}")
                logger.info(f"Tokens in dict: {len(game_state_dict.get('tokens', {}))}")

                initial_state = GameState.from_dict(game_state_dict)
                logger.info(f"Received initial game state with {len(initial_state.players)} players, {len(initial_state.tokens)} tokens")
            except Exception as e:
                logger.error(f"Failed to deserialize initial game state: {e}", exc_info=True)

        # Create network game view with initial state
        self.network_game_view = NetworkGameView(self.network_client, initial_state)

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

        self._show_error_dialog(
            "Connection Lost",
            "You have been disconnected from the network game.\n\nReturning to main menu."
        )
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
