"""Main menu view for Race to the Crystal.

Provides menu navigation for local games, network games, and settings.
"""

import arcade
import arcade.gui
from typing import Optional, Callable
import logging

from shared.constants import BACKGROUND_COLOR

logger = logging.getLogger(__name__)


class MainMenuView(arcade.View):
    """
    Main menu view with options for local and network gameplay.

    Provides buttons for:
    - Local Hot-Seat Game
    - Host Network Game
    - Join Network Game
    - Settings
    - Quit
    """

    def __init__(self):
        """Initialize the main menu view."""
        super().__init__()

        # UI Manager for buttons and widgets
        self.manager = arcade.gui.UIManager()

        # Callbacks for menu actions
        self.on_local_game: Optional[Callable[[int, bool], None]] = None
        self.on_host_game: Optional[Callable[[], None]] = None
        self.on_join_game: Optional[Callable[[], None]] = None
        self.on_settings: Optional[Callable[[], None]] = None

        # Settings (defaults)
        self.num_players = 4
        self.start_in_3d = False
        self.music_enabled = True

        # Visual elements
        self.title_text = None
        self.version_text = None

        logger.info("Main menu view created")

    def setup(self):
        """Set up the menu UI elements."""
        self.manager.clear()

        # Create a vertical box for buttons
        v_box = arcade.gui.UIBoxLayout(space_between=20)

        # Title (will be drawn separately for better styling)
        self.title_text = arcade.Text(
            "RACE TO THE CRYSTAL",
            self.window.width // 2,
            self.window.height - 100,
            arcade.color.CYAN,
            font_size=48,
            anchor_x="center",
            bold=True
        )

        self.version_text = arcade.Text(
            "Phase 4: Polish & Features",
            self.window.width // 2,
            self.window.height - 150,
            arcade.color.WHITE,
            font_size=16,
            anchor_x="center"
        )

        # Button styling
        button_style = {
            "font_size": 18,
            "font_name": "Arial",
            "height": 50,
            "width": 300,
        }

        # Local Game button
        local_game_button = arcade.gui.UIFlatButton(
            text="Local Hot-Seat Game",
            **button_style
        )
        local_game_button.on_click = self._on_local_game_click
        v_box.add(local_game_button)

        # Host Network Game button
        host_game_button = arcade.gui.UIFlatButton(
            text="Host Network Game",
            **button_style
        )
        host_game_button.on_click = self._on_host_game_click
        v_box.add(host_game_button)

        # Join Network Game button
        join_game_button = arcade.gui.UIFlatButton(
            text="Join Network Game",
            **button_style
        )
        join_game_button.on_click = self._on_join_game_click
        v_box.add(join_game_button)

        # Settings button
        settings_button = arcade.gui.UIFlatButton(
            text="Settings",
            **button_style
        )
        settings_button.on_click = self._on_settings_click
        v_box.add(settings_button)

        # Quit button
        quit_button = arcade.gui.UIFlatButton(
            text="Quit",
            **button_style
        )
        quit_button.on_click = self._on_quit_click
        v_box.add(quit_button)

        # Center the button box
        self.manager.add(
            arcade.gui.UIAnchorLayout(
                anchor_x="center_x",
                anchor_y="center_y",
                children=[v_box],
                align_y=-50  # Offset down a bit from center
            )
        )

    def on_show_view(self):
        """Called when this view is shown."""
        self.setup()
        self.manager.enable()
        arcade.set_background_color(BACKGROUND_COLOR)
        logger.info("Main menu view shown")

    def on_hide_view(self):
        """Called when this view is hidden."""
        self.manager.disable()

    def on_draw(self):
        """Render the menu."""
        self.clear()

        # Draw title
        if self.title_text:
            self.title_text.draw()
        if self.version_text:
            self.version_text.draw()

        # Draw UI manager (buttons)
        self.manager.draw()

    def _on_local_game_click(self, event):
        """Handle local game button click."""
        logger.info("Local game selected")
        if self.on_local_game:
            self.on_local_game(self.num_players, self.start_in_3d)

    def _on_host_game_click(self, event):
        """Handle host game button click."""
        logger.info("Host game selected")
        if self.on_host_game:
            self.on_host_game()

    def _on_join_game_click(self, event):
        """Handle join game button click."""
        logger.info("Join game selected")
        if self.on_join_game:
            self.on_join_game()

    def _on_settings_click(self, event):
        """Handle settings button click."""
        logger.info("Settings selected")
        if self.on_settings:
            self.on_settings()

    def _on_quit_click(self, event):
        """Handle quit button click."""
        logger.info("Quit selected")
        arcade.exit()


class SettingsView(arcade.View):
    """
    Settings view for configuring game options.

    Options:
    - Number of players (2-4) for local games
    - Start in 2D or 3D mode
    - Music on/off
    """

    def __init__(self, main_menu: MainMenuView):
        """
        Initialize settings view.

        Args:
            main_menu: Reference to main menu for accessing/updating settings
        """
        super().__init__()
        self.main_menu = main_menu
        self.manager = arcade.gui.UIManager()

        # UI elements
        self.title_text = None
        self.num_players_text = None
        self.mode_text = None
        self.music_text = None

        logger.info("Settings view created")

    def setup(self):
        """Set up the settings UI."""
        self.manager.clear()

        # Title
        self.title_text = arcade.Text(
            "SETTINGS",
            self.window.width // 2,
            self.window.height - 100,
            arcade.color.CYAN,
            font_size=36,
            anchor_x="center",
            bold=True
        )

        # Create settings labels
        y_pos = self.window.height - 200
        spacing = 100

        # Number of players setting
        self.num_players_text = arcade.Text(
            f"Number of Players: {self.main_menu.num_players}",
            self.window.width // 2,
            y_pos,
            arcade.color.WHITE,
            font_size=20,
            anchor_x="center"
        )

        # Camera mode setting
        mode = "3D" if self.main_menu.start_in_3d else "2D"
        self.mode_text = arcade.Text(
            f"Start Camera Mode: {mode}",
            self.window.width // 2,
            y_pos - spacing,
            arcade.color.WHITE,
            font_size=20,
            anchor_x="center"
        )

        # Music setting
        music_status = "ON" if self.main_menu.music_enabled else "OFF"
        self.music_text = arcade.Text(
            f"Music: {music_status}",
            self.window.width // 2,
            y_pos - spacing * 2,
            arcade.color.WHITE,
            font_size=20,
            anchor_x="center"
        )

        # Create button layout
        v_box = arcade.gui.UIBoxLayout(space_between=20)

        button_style = {
            "font_size": 18,
            "height": 50,
            "width": 300,
        }

        # Player count buttons
        player_2_button = arcade.gui.UIFlatButton(text="2 Players", **button_style)
        player_2_button.on_click = lambda e: self._set_players(2)
        v_box.add(player_2_button)

        player_4_button = arcade.gui.UIFlatButton(text="4 Players", **button_style)
        player_4_button.on_click = lambda e: self._set_players(4)
        v_box.add(player_4_button)

        # Camera mode toggle
        toggle_mode_button = arcade.gui.UIFlatButton(
            text="Toggle Camera Mode (2D/3D)",
            **button_style
        )
        toggle_mode_button.on_click = self._toggle_camera_mode
        v_box.add(toggle_mode_button)

        # Music toggle
        toggle_music_button = arcade.gui.UIFlatButton(
            text="Toggle Music",
            **button_style
        )
        toggle_music_button.on_click = self._toggle_music
        v_box.add(toggle_music_button)

        # Back button
        back_button = arcade.gui.UIFlatButton(text="Back to Menu", **button_style)
        back_button.on_click = self._on_back_click
        v_box.add(back_button)

        # Center the button box
        self.manager.add(
            arcade.gui.UIAnchorLayout(
                anchor_x="center_x",
                anchor_y="center_y",
                children=[v_box],
                align_y=-100
            )
        )

    def on_show_view(self):
        """Called when this view is shown."""
        self.setup()
        self.manager.enable()
        arcade.set_background_color(BACKGROUND_COLOR)
        logger.info("Settings view shown")

    def on_hide_view(self):
        """Called when this view is hidden."""
        self.manager.disable()

    def on_draw(self):
        """Render the settings screen."""
        self.clear()

        # Draw title and settings text
        if self.title_text:
            self.title_text.draw()
        if self.num_players_text:
            self.num_players_text.draw()
        if self.mode_text:
            self.mode_text.draw()
        if self.music_text:
            self.music_text.draw()

        # Draw UI manager (buttons)
        self.manager.draw()

    def _set_players(self, num_players: int):
        """Set number of players."""
        self.main_menu.num_players = num_players
        logger.info(f"Players set to {num_players}")
        self.setup()  # Refresh UI

    def _toggle_camera_mode(self, event):
        """Toggle between 2D and 3D starting mode."""
        self.main_menu.start_in_3d = not self.main_menu.start_in_3d
        logger.info(f"Camera mode set to {'3D' if self.main_menu.start_in_3d else '2D'}")
        self.setup()  # Refresh UI

    def _toggle_music(self, event):
        """Toggle music on/off."""
        self.main_menu.music_enabled = not self.main_menu.music_enabled
        logger.info(f"Music set to {'ON' if self.main_menu.music_enabled else 'OFF'}")
        self.setup()  # Refresh UI

    def _on_back_click(self, event):
        """Return to main menu."""
        logger.info("Returning to main menu")
        self.window.show_view(self.main_menu)


class NetworkSetupView(arcade.View):
    """
    View for setting up network games (host or join).
    """

    def __init__(self, main_menu: MainMenuView, is_host: bool = True):
        """
        Initialize network setup view.

        Args:
            main_menu: Reference to main menu
            is_host: True for hosting, False for joining
        """
        super().__init__()
        self.main_menu = main_menu
        self.is_host = is_host
        self.manager = arcade.gui.UIManager()

        # Input fields
        self.player_name_input = None
        self.server_host_input = None
        self.server_port_input = None
        self.game_name_input = None

        # Callbacks
        self.on_start_network_game: Optional[Callable[[str, str, int, Optional[str]], None]] = None

        logger.info(f"Network setup view created (host={is_host})")

    def setup(self):
        """Set up the network configuration UI."""
        self.manager.clear()

        # Title
        title = "HOST NETWORK GAME" if self.is_host else "JOIN NETWORK GAME"
        title_text = arcade.Text(
            title,
            self.window.width // 2,
            self.window.height - 100,
            arcade.color.CYAN,
            font_size=32,
            anchor_x="center",
            bold=True
        )

        # Create vertical layout
        v_box = arcade.gui.UIBoxLayout(space_between=15)

        # Player name input
        player_name_label = arcade.gui.UILabel(
            text="Your Name:",
            width=300,
            font_size=16
        )
        v_box.add(player_name_label)

        self.player_name_input = arcade.gui.UIInputText(
            width=300,
            height=40,
            font_size=16,
            text="Player"
        )
        v_box.add(self.player_name_input)

        # Server host input (only for joining)
        if not self.is_host:
            server_label = arcade.gui.UILabel(
                text="Server Address:",
                width=300,
                font_size=16
            )
            v_box.add(server_label)

            self.server_host_input = arcade.gui.UIInputText(
                width=300,
                height=40,
                font_size=16,
                text="localhost"
            )
            v_box.add(self.server_host_input)

        # Port input (for both)
        port_label = arcade.gui.UILabel(
            text="Port:",
            width=300,
            font_size=16
        )
        v_box.add(port_label)

        self.server_port_input = arcade.gui.UIInputText(
            width=300,
            height=40,
            font_size=16,
            text="8888"
        )
        v_box.add(self.server_port_input)

        # Game name (only for hosting)
        if self.is_host:
            game_name_label = arcade.gui.UILabel(
                text="Game Name:",
                width=300,
                font_size=16
            )
            v_box.add(game_name_label)

            self.game_name_input = arcade.gui.UIInputText(
                width=300,
                height=40,
                font_size=16,
                text="My Game"
            )
            v_box.add(self.game_name_input)

        # Buttons
        start_text = "Create Game" if self.is_host else "Join Game"
        start_button = arcade.gui.UIFlatButton(
            text=start_text,
            width=300,
            height=50,
            font_size=18
        )
        start_button.on_click = self._on_start_click
        v_box.add(start_button)

        back_button = arcade.gui.UIFlatButton(
            text="Back to Menu",
            width=300,
            height=50,
            font_size=18
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

        # Store title for drawing
        self.title_text = title_text

    def on_show_view(self):
        """Called when this view is shown."""
        self.setup()
        self.manager.enable()
        arcade.set_background_color(BACKGROUND_COLOR)
        logger.info("Network setup view shown")

    def on_hide_view(self):
        """Called when this view is hidden."""
        self.manager.disable()

    def on_draw(self):
        """Render the network setup screen."""
        self.clear()

        # Draw title
        if self.title_text:
            self.title_text.draw()

        # Draw UI manager
        self.manager.draw()

    def _on_start_click(self, event):
        """Handle start button click."""
        player_name = self.player_name_input.text.strip() or "Player"

        try:
            port = int(self.server_port_input.text)
        except ValueError:
            port = 8888

        if self.is_host:
            game_name = self.game_name_input.text.strip() or "My Game"
            logger.info(f"Starting host: {player_name}, port {port}, game '{game_name}'")
            if self.on_start_network_game:
                self.on_start_network_game(player_name, "localhost", port, game_name)
        else:
            host = self.server_host_input.text.strip() or "localhost"
            logger.info(f"Starting join: {player_name}, {host}:{port}")
            if self.on_start_network_game:
                self.on_start_network_game(player_name, host, port, None)

    def _on_back_click(self, event):
        """Return to main menu."""
        logger.info("Returning to main menu")
        self.window.show_view(self.main_menu)
