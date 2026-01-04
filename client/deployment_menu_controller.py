"""
Deployment menu controller for Race to the Crystal.

This module handles the deployment menu UI that allows players to select
and deploy tokens from their reserve.
"""

import math
from typing import Dict, Optional, Tuple

import arcade

from shared.constants import (
    CORNER_INDICATOR_MARGIN,
    CORNER_INDICATOR_SIZE,
    DEPLOYMENT_MENU_SPACING,
    HEXAGON_SIDES,
    HUD_HEIGHT,
    MENU_OPTION_CLICK_RADIUS,
    PLAYER_COLORS,
)
from shared.corner_layout import get_ui_corner_config
from shared.logging_config import setup_logger
from shared.ui_config import ViewportConfig, UIStyleConfig

logger = setup_logger(__name__)


class DeploymentMenuController:
    """
    Manages the deployment menu UI for token deployment.

    The DeploymentMenuController handles:
    - Tracking menu open/closed state
    - Calculating indicator and menu positions
    - Rendering the corner indicator (R hexagon)
    - Rendering the deployment menu options
    - Handling clicks on menu options
    - Validating deployment positions
    """

    def __init__(self, window_width: int, window_height: int):
        """
        Initialize deployment menu controller.

        Args:
            window_width: Window width in pixels
            window_height: Window height in pixels
        """
        self.window_width = window_width
        self.window_height = window_height

        # Menu state
        self.menu_open = False
        self.menu_just_opened = False
        self.selected_deploy_health: Optional[int] = None

        # Pre-create text objects for performance
        self.reserve_text = arcade.Text(
            "R", 0, 0, (255, 255, 255), font_size=24, bold=True, anchor_x="center"
        )

        # Health text objects (health values are 2, 4, 6, 8, 10, 12)
        self.health_texts = {
            health: arcade.Text(
                str(health),
                0,
                0,
                (255, 255, 255),
                font_size=20,
                bold=True,
                anchor_x="center",
                anchor_y="center",
            )
            for health in [2, 4, 6, 8, 10, 12]
        }

        # Count text objects will be created dynamically as needed
        self.count_texts: Dict[str, arcade.Text] = {}

    def get_indicator_position(
        self, current_player
    ) -> Optional[Tuple[float, float, float]]:
        """
        Get the position and size of the corner indicator.

        Args:
            current_player: Current player object

        Returns:
            Tuple of (center_x, center_y, size) or None if no current player
        """
        if not current_player:
            return None

        player_index = current_player.color.value

        # Create configuration objects
        viewport = ViewportConfig(
            window_width=self.window_width,
            window_height=self.window_height,
            hud_height=HUD_HEIGHT,
        )
        style = UIStyleConfig(
            margin=CORNER_INDICATOR_MARGIN,
            indicator_size=CORNER_INDICATOR_SIZE,
            spacing=DEPLOYMENT_MENU_SPACING,
        )

        config = get_ui_corner_config(player_index)
        center_x, center_y = config.get_indicator_position(viewport, style)

        return (center_x, center_y, style.indicator_size)

    def is_click_on_indicator(self, x: int, y: int, current_player) -> bool:
        """
        Check if a screen-space click is on the corner indicator.

        Args:
            x: Screen x coordinate
            y: Screen y coordinate
            current_player: Current player object

        Returns:
            True if click is within the indicator hexagon
        """
        pos = self.get_indicator_position(current_player)
        if not pos:
            return False

        center_x, center_y, size = pos

        # Simple circle collision for now (hexagon would be more accurate but this works)
        distance_sq = (x - center_x) ** 2 + (y - center_y) ** 2
        return distance_sq <= (size * 1.2) ** 2  # Slightly larger hit box

    def open_menu(self) -> None:
        """Open deployment menu."""
        self.menu_open = True
        self.menu_just_opened = True
        logger.debug("Opened deployment menu at R hexagon")

    def close_menu(self) -> None:
        """Close deployment menu."""
        self.menu_open = False
        self.menu_just_opened = False
        logger.debug("Closed deployment menu")

    def clear_just_opened_flag(self) -> None:
        """Clear the just_opened flag to allow clicks."""
        self.menu_just_opened = False

    def cancel_selection(self) -> None:
        """Cancel current deployment selection."""
        if self.selected_deploy_health:
            logger.debug("Cancelled deployment selection")
            self.selected_deploy_health = None
        elif self.menu_open:
            self.close_menu()

    def handle_menu_click(
        self,
        screen_pos: Tuple[int, int],
        current_player,
        reserve_counts: Dict[int, int],
    ) -> Optional[int]:
        """
        Handle click on UI-based corner menu (around R hexagon).

        Args:
            screen_pos: Click position in screen coordinates
            current_player: Current player object
            reserve_counts: Dict mapping health values to available counts

        Returns:
            Selected health value if a valid token type was selected, None otherwise
        """
        if not self.menu_open:
            return None

        if not current_player:
            return None

        # Get R hexagon position
        pos = self.get_indicator_position(current_player)
        if not pos:
            return None

        center_x, center_y, indicator_size = pos
        spacing = DEPLOYMENT_MENU_SPACING

        # Calculate menu option positions using corner configuration
        player_index = current_player.color.value
        config = get_ui_corner_config(player_index)
        positions = config.get_menu_option_positions(center_x, center_y, spacing)

        # Build options list: (health_value, x, y)
        health_values = [10, 8, 6, 4]
        options = [(health, x, y) for (health, (x, y)) in zip(health_values, positions)]

        click_x, click_y = screen_pos

        # Check which option was clicked
        click_radius = MENU_OPTION_CLICK_RADIUS
        for health, option_x, option_y in options:
            distance = ((click_x - option_x) ** 2 + (click_y - option_y) ** 2) ** 0.5
            if distance <= click_radius:
                # Check if player has this token type in reserve
                if reserve_counts.get(health, 0) > 0:
                    # Select this token type for deployment
                    self.selected_deploy_health = health
                    logger.debug(
                        f"Selected {health}hp token for deployment - "
                        "click a deployment area position to deploy"
                    )

                    # Close the menu
                    self.close_menu()
                    return health
                else:
                    logger.warning(f"No {health}hp tokens available in reserve")
                    return None

        return None

    def draw_indicator(self, current_player) -> None:
        """
        Draw a visual indicator in UI space showing the player's deployment corner.

        Args:
            current_player: Current player object
        """
        pos = self.get_indicator_position(current_player)
        if not pos:
            return

        center_x, center_y, indicator_size = pos

        player_index = current_player.color.value
        player_color = PLAYER_COLORS[player_index]

        # Draw hexagon indicator with glow
        num_sides = HEXAGON_SIDES
        points = []
        for i in range(num_sides):
            angle = (i / num_sides) * 2 * math.pi - math.pi / 2
            x = center_x + indicator_size * math.cos(angle)
            y = center_y + indicator_size * math.sin(angle)
            points.append((x, y))

        # Draw glow layers
        for glow in range(4, 0, -1):
            alpha = int(100 / (glow + 1))
            glow_points = []
            for i in range(num_sides):
                angle = (i / num_sides) * 2 * math.pi - math.pi / 2
                x = center_x + (indicator_size + glow * 3) * math.cos(angle)
                y = center_y + (indicator_size + glow * 3) * math.sin(angle)
                glow_points.append((x, y))
            arcade.draw_polygon_outline(
                glow_points, (*player_color, alpha), max(1, 4 - glow)
            )

        # Draw main hexagon outline
        arcade.draw_polygon_outline(points, player_color, 3)

        # Draw "R" for Reserve/Repository in the center
        self.reserve_text.x = center_x
        self.reserve_text.y = center_y
        self.reserve_text.color = player_color
        self.reserve_text.draw()

    def draw_menu(self, current_player, reserve_counts: Dict[int, int]) -> None:
        """
        Draw the corner deployment menu in UI space around the R hexagon.

        Args:
            current_player: Current player object
            reserve_counts: Dict mapping health values to available counts
        """
        if not self.menu_open:
            return

        if not current_player:
            return

        # Get R hexagon position
        pos = self.get_indicator_position(current_player)
        if not pos:
            return

        center_x, center_y, indicator_size = pos

        # Menu spacing around the R hexagon
        spacing = DEPLOYMENT_MENU_SPACING

        # Get menu option positions using corner configuration
        player_index = current_player.color.value
        config = get_ui_corner_config(player_index)
        positions = config.get_menu_option_positions(center_x, center_y, spacing)

        # Build options list: (health_value, x, y, count)
        health_values = [10, 8, 6, 4]
        options = [
            (health, x, y, reserve_counts.get(health, 0))
            for (health, (x, y)) in zip(health_values, positions)
        ]

        # Draw each option
        for health, x, y, count in options:
            if count > 0:
                # Draw available option in cyan
                arcade.draw_circle_filled(x, y, 30, (0, 255, 255, 200))
                arcade.draw_circle_outline(x, y, 30, (0, 255, 255), 3)
            else:
                # Draw unavailable option in dark gray
                arcade.draw_circle_filled(x, y, 30, (50, 50, 50, 100))
                arcade.draw_circle_outline(x, y, 30, (100, 100, 100), 2)

            # Draw health value using Text object for performance
            health_text = self.health_texts.get(health)
            if health_text:
                health_text.x = x
                health_text.y = y
                health_text.color = (255, 255, 255) if count > 0 else (100, 100, 100)
                health_text.draw()

            # Draw count if available
            if count > 0:
                text_key = f"{x}_{y}"  # Use position as key since count can change
                if text_key not in self.count_texts:
                    # Create new text object
                    self.count_texts[text_key] = arcade.Text(
                        f"({count})",
                        x,
                        y - 15,
                        (200, 200, 200),
                        font_size=12,
                        anchor_x="center",
                        anchor_y="center",
                    )
                else:
                    # Update existing text object
                    count_text = self.count_texts[text_key]
                    count_text.text = f"({count})"

                self.count_texts[text_key].draw()

    def is_valid_deployment_position(
        self, grid_pos: Tuple[int, int], player_id: str, game_state
    ) -> bool:
        """
        Check if a position is valid for deployment.

        Args:
            grid_pos: Grid position to check
            player_id: Player ID
            game_state: Game state object

        Returns:
            True if position is in the player's deployment zone
        """
        player = game_state.get_player(player_id)
        if not player:
            return False

        player_index = player.color.value
        deployable_positions = game_state.board.get_deployable_positions(player_index)
        return grid_pos in deployable_positions

    def resize(self, width: int, height: int) -> None:
        """
        Handle window resize.

        Args:
            width: New window width
            height: New window height
        """
        self.window_width = width
        self.window_height = height
