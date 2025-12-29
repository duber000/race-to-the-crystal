"""Victory screen for Race to the Crystal.

Shows game results, statistics, and winner announcement.
"""

import arcade
import arcade.gui
import logging
from typing import Optional, Callable, Dict, List

from shared.constants import BACKGROUND_COLOR, PLAYER_COLORS

logger = logging.getLogger(__name__)


class VictoryView(arcade.View):
    """
    Victory screen showing game results.

    Displays:
    - Winner announcement
    - Player statistics
    - Final scores
    - Return to menu button
    """

    def __init__(
        self,
        winner_name: str,
        winner_id: Optional[str] = None,
        game_stats: Optional[Dict] = None
    ):
        """
        Initialize victory view.

        Args:
            winner_name: Name of the winning player
            winner_id: ID of the winning player
            game_stats: Optional dictionary of game statistics
        """
        super().__init__()

        self.winner_name = winner_name
        self.winner_id = winner_id
        self.game_stats = game_stats or {}

        # UI manager
        self.manager = arcade.gui.UIManager()

        # Callbacks
        self.on_return_to_menu: Optional[Callable[[], None]] = None

        # UI elements
        self.title_text = None
        self.stat_texts: List[arcade.Text] = []

        logger.info(f"Victory view created for winner: {winner_name}")

    def setup(self):
        """Set up the victory screen UI."""
        self.manager.clear()

        # Victory title
        self.title_text = arcade.Text(
            f"🏆 {self.winner_name} WINS! 🏆",
            self.window.width // 2,
            self.window.height - 100,
            arcade.color.GOLD,
            font_size=48,
            anchor_x="center",
            bold=True
        )

        # Subtitle
        self.subtitle_text = arcade.Text(
            "Victory is yours!",
            self.window.width // 2,
            self.window.height - 160,
            arcade.color.WHITE,
            font_size=24,
            anchor_x="center",
            italic=True
        )

        # Build statistics display
        self._build_statistics()

        # Create buttons
        v_box = arcade.gui.UIBoxLayout(space_between=15)

        button_style = {
            "font_size": 20,
            "height": 60,
            "width": 300,
        }

        # Return to menu button
        menu_button = arcade.gui.UIFlatButton(
            text="Return to Main Menu",
            **button_style
        )
        menu_button.on_click = self._on_menu_click
        v_box.add(menu_button)

        # Quit button
        quit_button = arcade.gui.UIFlatButton(
            text="Quit Game",
            **button_style
        )
        quit_button.on_click = self._on_quit_click
        v_box.add(quit_button)

        # Position buttons at bottom
        self.manager.add(
            arcade.gui.UIAnchorLayout(
                anchor_x="center_x",
                anchor_y="bottom",
                children=[v_box],
                align_y=50
            )
        )

    def _build_statistics(self):
        """Build the statistics display."""
        self.stat_texts = []

        # Statistics title
        stats_y = self.window.height - 240

        stats_title = arcade.Text(
            "Game Statistics",
            self.window.width // 2,
            stats_y,
            arcade.color.CYAN,
            font_size=28,
            anchor_x="center",
            bold=True
        )
        self.stat_texts.append(stats_title)

        stats_y -= 60

        # Display available statistics
        if self.game_stats:
            # Player rankings
            players = self.game_stats.get("players", [])
            if players:
                # Sort by score (if available)
                sorted_players = sorted(
                    players,
                    key=lambda p: p.get("score", 0),
                    reverse=True
                )

                for i, player_data in enumerate(sorted_players):
                    name = player_data.get("name", "Unknown")
                    tokens_deployed = player_data.get("tokens_deployed", 0)
                    tokens_alive = player_data.get("tokens_alive", 0)
                    attacks_made = player_data.get("attacks_made", 0)

                    # Get player color (if available)
                    color_index = player_data.get("color_index", i)
                    color = PLAYER_COLORS.get(color_index, arcade.color.WHITE)

                    # Build stat line
                    stat_line = (
                        f"#{i + 1} {name}: "
                        f"{tokens_alive}/{tokens_deployed} tokens, "
                        f"{attacks_made} attacks"
                    )

                    stat_text = arcade.Text(
                        stat_line,
                        self.window.width // 2,
                        stats_y,
                        color,
                        font_size=18,
                        anchor_x="center"
                    )
                    self.stat_texts.append(stat_text)
                    stats_y -= 35

            # General game stats
            stats_y -= 20
            general_stats = []

            total_turns = self.game_stats.get("total_turns", 0)
            if total_turns:
                general_stats.append(f"Total Turns: {total_turns}")

            game_duration = self.game_stats.get("duration", 0)
            if game_duration:
                minutes = int(game_duration // 60)
                seconds = int(game_duration % 60)
                general_stats.append(f"Duration: {minutes}m {seconds}s")

            for stat in general_stats:
                stat_text = arcade.Text(
                    stat,
                    self.window.width // 2,
                    stats_y,
                    arcade.color.LIGHT_GRAY,
                    font_size=16,
                    anchor_x="center"
                )
                self.stat_texts.append(stat_text)
                stats_y -= 30

        else:
            # No stats available
            no_stats_text = arcade.Text(
                "No statistics available",
                self.window.width // 2,
                stats_y,
                arcade.color.GRAY,
                font_size=18,
                anchor_x="center",
                italic=True
            )
            self.stat_texts.append(no_stats_text)

    def on_show_view(self):
        """Called when this view is shown."""
        self.setup()
        self.manager.enable()
        arcade.set_background_color(BACKGROUND_COLOR)
        logger.info("Victory view shown")

    def on_hide_view(self):
        """Called when this view is hidden."""
        self.manager.disable()

    def on_draw(self):
        """Render the victory screen."""
        self.clear()

        # Draw confetti effect (simple colored rectangles falling)
        # TODO: Add particle effect for celebration

        # Draw title
        if self.title_text:
            self.title_text.draw()
        if hasattr(self, 'subtitle_text') and self.subtitle_text:
            self.subtitle_text.draw()

        # Draw statistics
        for text in self.stat_texts:
            text.draw()

        # Draw UI manager (buttons)
        self.manager.draw()

    def _on_menu_click(self, event):
        """Handle return to menu button click."""
        logger.info("Returning to main menu")
        if self.on_return_to_menu:
            self.on_return_to_menu()

    def _on_quit_click(self, event):
        """Handle quit button click."""
        logger.info("Quitting game")
        arcade.exit()


class VictoryViewSimple(arcade.View):
    """
    Simplified victory view for local games without network stats.
    """

    def __init__(self, winner_name: str):
        """
        Initialize simple victory view.

        Args:
            winner_name: Name of the winner
        """
        super().__init__()

        self.winner_name = winner_name
        self.manager = arcade.gui.UIManager()
        self.on_return_to_menu: Optional[Callable[[], None]] = None

        logger.info(f"Simple victory view created for: {winner_name}")

    def setup(self):
        """Set up the victory screen."""
        self.manager.clear()

        # Create button
        menu_button = arcade.gui.UIFlatButton(
            text="Return to Main Menu",
            width=300,
            height=60,
            font_size=20
        )
        menu_button.on_click = lambda e: (
            self.on_return_to_menu() if self.on_return_to_menu else None
        )

        self.manager.add(
            arcade.gui.UIAnchorLayout(
                anchor_x="center_x",
                anchor_y="bottom",
                children=[menu_button],
                align_y=50
            )
        )

    def on_show_view(self):
        """Called when view is shown."""
        self.setup()
        self.manager.enable()
        arcade.set_background_color(BACKGROUND_COLOR)

    def on_hide_view(self):
        """Called when view is hidden."""
        self.manager.disable()

    def on_draw(self):
        """Render the screen."""
        self.clear()

        # Draw victory text
        arcade.draw_text(
            f"🏆 {self.winner_name} WINS! 🏆",
            self.window.width // 2,
            self.window.height // 2 + 50,
            arcade.color.GOLD,
            font_size=48,
            anchor_x="center",
            anchor_y="center",
            bold=True
        )

        arcade.draw_text(
            "Congratulations!",
            self.window.width // 2,
            self.window.height // 2 - 20,
            arcade.color.WHITE,
            font_size=24,
            anchor_x="center",
            anchor_y="center",
            italic=True
        )

        self.manager.draw()
