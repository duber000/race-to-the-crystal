"""Game browser view for joining network games.

Displays available games and allows player to select one to join.
"""

import arcade
import arcade.gui
import logging
from typing import Optional, Callable, Dict, List

from client.network_client import NetworkClient
from client.ui.async_arcade import schedule_async
from network.messages import MessageType, ClientType
from shared.constants import BACKGROUND_COLOR

logger = logging.getLogger(__name__)


class GameBrowserView(arcade.View):
    """
    Game browser view for joining network games.

    Shows:
    - List of available games
    - Game info (name, players, status)
    - Join button for each game
    - Refresh button
    """

    def __init__(
        self,
        player_name: str,
        host: str,
        port: int,
        main_menu_view: arcade.View
    ):
        """
        Initialize game browser view.

        Args:
            player_name: Player's display name
            host: Server host
            port: Server port
            main_menu_view: Reference to main menu for back navigation
        """
        super().__init__()

        self.player_name = player_name
        self.host = host
        self.port = port
        self.main_menu_view = main_menu_view

        self.manager = arcade.gui.UIManager()

        # Network client (will be created when connecting)
        self.network_client: Optional[NetworkClient] = None

        # Game list state
        self.games: List[Dict] = []
        self.selected_game_id: Optional[str] = None
        self.loading = True
        self.error_message: Optional[str] = None

        # UI elements
        self.title_text = None
        self.status_text = None
        self.game_list_widgets: List = []

        # Callbacks
        self.on_game_selected: Optional[Callable[[str], None]] = None

        logger.info(f"Game browser created for {player_name} @ {host}:{port}")

    def setup(self):
        """Set up the browser UI."""
        self.manager.clear()

        # Title
        self.title_text = arcade.Text(
            "AVAILABLE GAMES",
            self.window.width // 2,
            self.window.height - 80,
            arcade.color.CYAN,
            font_size=32,
            anchor_x="center",
            bold=True
        )

        # Status text
        status = "Loading games..." if self.loading else f"Found {len(self.games)} game(s)"
        if self.error_message:
            status = f"Error: {self.error_message}"

        self.status_text = arcade.Text(
            status,
            self.window.width // 2,
            self.window.height - 130,
            arcade.color.WHITE,
            font_size=16,
            anchor_x="center"
        )
        
        # No games message text
        self.no_games_text = arcade.Text(
            "No games available. Create a game from 'Host Network Game'.",
            self.window.width // 2,
            self.window.height // 2,
            arcade.color.GRAY,
            font_size=14,
            anchor_x="center",
            anchor_y="center"
        )

        # Create button layout
        v_box = arcade.gui.UIBoxLayout(space_between=15)

        button_style = {
            "font_size": 18,
            "height": 50,
            "width": 400,
        }

        # If we have games, show them
        if not self.loading and not self.error_message and self.games:
            for game in self.games:
                game_id = game.get("game_id", "")
                game_name = game.get("name", "Unknown Game")
                num_players = game.get("num_players", 0)
                max_players = game.get("max_players", 4)
                status = game.get("status", "waiting")

                # Format button text
                button_text = f"{game_name} ({num_players}/{max_players}) - {status}"

                # Create button for this game
                game_button = arcade.gui.UIFlatButton(
                    text=button_text,
                    **button_style
                )

                # Use closure to capture game_id
                def make_join_handler(gid):
                    return lambda e: self._on_join_game(gid)

                game_button.on_click = make_join_handler(game_id)
                v_box.add(game_button)

        # Refresh button
        refresh_button = arcade.gui.UIFlatButton(
            text="Refresh Game List",
            **button_style
        )
        refresh_button.on_click = self._on_refresh_click
        v_box.add(refresh_button)

        # Back button
        back_button = arcade.gui.UIFlatButton(
            text="Back to Menu",
            **button_style
        )
        back_button.on_click = self._on_back_click
        v_box.add(back_button)

        # Center the layout
        self.manager.add(
            arcade.gui.UIAnchorLayout(
                anchor_x="center_x",
                anchor_y="center_y",
                children=[v_box],
                align_y=-50
            )
        )

    def on_show_view(self):
        """Called when this view is shown."""
        self.setup()
        self.manager.enable()
        arcade.set_background_color(BACKGROUND_COLOR)

        # Start loading games
        schedule_async(self._load_games())

        logger.info("Game browser view shown")

    def on_hide_view(self):
        """Called when this view is hidden."""
        self.manager.disable()

        # Disconnect if connected
        if self.network_client:
            schedule_async(self._cleanup())

    async def _cleanup(self):
        """Clean up network resources."""
        if self.network_client and self.network_client.is_connected():
            await self.network_client.disconnect()
            self.network_client = None

    def on_draw(self):
        """Render the browser screen."""
        self.clear()

        # Draw title and status
        if self.title_text:
            self.title_text.draw()
        if self.status_text:
            self.status_text.draw()

        # Draw UI manager (buttons)
        self.manager.draw()

        # Show help text if no games
        if not self.loading and not self.error_message and len(self.games) == 0:
            self.no_games_text.draw()

    async def _load_games(self):
        """Connect to server and load available games."""
        try:
            logger.info("=== Starting _load_games ===")
            self.loading = True
            self.error_message = None
            self.setup()  # Refresh UI

            # Create network client
            logger.info("Creating network client...")
            self.network_client = NetworkClient(self.player_name, ClientType.HUMAN)

            # Connect to server
            logger.info(f"Connecting to {self.host}:{self.port}...")
            success = await self.network_client.connect(self.host, self.port)
            logger.info(f"Connect result: {success}")

            if not success:
                self.error_message = "Failed to connect to server"
                self.loading = False
                self.setup()
                logger.error("Connection failed")
                return

            # Request game list
            logger.info("Requesting game list...")
            games = await self.network_client.list_games()
            logger.info(f"list_games returned: {games}")

            if games is None:
                self.error_message = "Failed to get game list"
                logger.error("No games returned")
            else:
                self.games = games
                logger.info(f"Loaded {len(self.games)} games")

            self.loading = False
            self.setup()  # Refresh UI with games
            logger.info("=== Finished _load_games ===")

        except Exception as e:
            logger.error(f"Error loading games: {e}", exc_info=True)
            self.error_message = str(e)
            self.loading = False
            self.setup()

    def _on_join_game(self, game_id: str):
        """
        Handle join game button click.

        Args:
            game_id: ID of game to join
        """
        logger.info(f"Joining game: {game_id[:8]}")
        self.selected_game_id = game_id

        # Notify callback
        if self.on_game_selected:
            self.on_game_selected(game_id)

    def _on_refresh_click(self, event):
        """Handle refresh button click."""
        logger.info("Refreshing game list...")

        # Disconnect current client if any
        if self.network_client:
            schedule_async(self._cleanup())

        # Reload games
        schedule_async(self._load_games())

    def _on_back_click(self, event):
        """Return to main menu."""
        logger.info("Returning to main menu from browser")

        # Clean up connection
        if self.network_client:
            schedule_async(self._cleanup())

        self.window.show_view(self.main_menu_view)
