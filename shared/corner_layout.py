"""
Corner layout configuration for player deployment areas and UI positioning.

This module eliminates code duplication by providing a data-driven approach
to corner-specific positioning logic.
"""

from dataclasses import dataclass
from typing import Tuple, List
from enum import Enum

from shared.ui_config import ViewportConfig, UIStyleConfig


class CornerPosition(Enum):
    """Screen position of corners for UI placement."""

    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass(frozen=True)
class BoardCornerConfig:
    """
    Configuration for board-space corner deployment logic.

    Attributes:
        player_index: Index of the player (0-3)
        corner_pos: Screen position of this corner
        x_range: Range for X coordinates in deployment area
        y_range: Range for Y coordinates in deployment area
    """

    player_index: int
    corner_pos: CornerPosition
    x_range: range
    y_range: range

    def get_deployable_positions(self) -> List[Tuple[int, int]]:
        """
        Get all valid deployment positions for this corner.

        Returns:
            List of (x, y) positions in the 3x3 deployment area
        """
        positions = []
        for x in self.x_range:
            for y in self.y_range:
                positions.append((x, y))
        return positions


@dataclass(frozen=True)
class UICornerConfig:
    """
    Configuration for UI-space corner indicator and menu positioning.

    Attributes:
        player_index: Index of the player (0-3)
        corner_pos: Screen position of this corner
        h_anchor: Horizontal anchor (-1 for left edge, 1 for right edge)
        v_anchor: Vertical anchor (-1 for bottom edge, 1 for top edge)
        menu_h_direction: Direction for menu options horizontally (1 = right, -1 = left)
        menu_v_direction: Direction for menu options vertically (1 = up, -1 = down)
    """

    player_index: int
    corner_pos: CornerPosition
    h_anchor: int  # -1 = left, 1 = right
    v_anchor: int  # -1 = bottom, 1 = top
    menu_h_direction: int  # 1 = expand right, -1 = expand left
    menu_v_direction: int  # 1 = expand up, -1 = expand down

    def get_indicator_position(
        self, viewport: ViewportConfig, style: UIStyleConfig
    ) -> Tuple[float, float]:
        """
        Calculate screen-space position for corner indicator.

        Args:
            viewport: Viewport configuration (window dimensions, HUD height)
            style: UI style configuration (margins, sizes)

        Returns:
            (center_x, center_y) position for indicator
        """
        # Calculate x position
        if self.h_anchor == -1:  # Left edge
            center_x = style.margin + style.indicator_size
        else:  # Right edge
            center_x = viewport.window_width - style.margin - style.indicator_size

        # Calculate y position
        if self.v_anchor == -1:  # Bottom edge
            center_y = style.margin + style.indicator_size
        else:  # Top edge
            center_y = (
                viewport.window_height
                - viewport.hud_height
                - style.margin
                - style.indicator_size
            )

        return (center_x, center_y)

    def get_menu_option_positions(
        self,
        center_x: float,
        center_y: float,
        spacing: float,
        far_spacing_multiplier: float = 1.8,
    ) -> List[Tuple[float, float]]:
        """
        Calculate positions for menu options around the corner indicator.

        Args:
            center_x: X position of corner indicator center
            center_y: Y position of corner indicator center
            spacing: Base spacing from center
            far_spacing_multiplier: Multiplier for far options (default 1.8)

        Returns:
            List of 4 (x, y) positions for menu options [10hp, 8hp, 6hp, 4hp]
        """
        h_dir = self.menu_h_direction
        v_dir = self.menu_v_direction
        far_spacing = spacing * far_spacing_multiplier

        # Options arranged in a grid pattern
        # Position 0: diagonal (both directions)
        # Position 1: far diagonal
        # Position 2: horizontal only
        # Position 3: far horizontal only
        return [
            (center_x + h_dir * spacing, center_y + v_dir * spacing),  # 10hp - diagonal
            (
                center_x + h_dir * far_spacing,
                center_y + v_dir * spacing,
            ),  # 8hp - far diagonal
            (center_x + h_dir * spacing, center_y),  # 6hp - horizontal
            (center_x + h_dir * far_spacing, center_y),  # 4hp - far horizontal
        ]


# Board corner configurations for all 4 players
BOARD_CORNER_CONFIGS = {
    0: BoardCornerConfig(
        player_index=0,
        corner_pos=CornerPosition.BOTTOM_LEFT,
        x_range=range(0, 3),
        y_range=range(0, 3),
    ),
    1: BoardCornerConfig(
        player_index=1,
        corner_pos=CornerPosition.BOTTOM_RIGHT,
        x_range=range(23, 20, -1),  # Reversed for right-to-left priority
        y_range=range(0, 3),
    ),
    2: BoardCornerConfig(
        player_index=2,
        corner_pos=CornerPosition.TOP_LEFT,
        x_range=range(0, 3),
        y_range=range(21, 24),
    ),
    3: BoardCornerConfig(
        player_index=3,
        corner_pos=CornerPosition.TOP_RIGHT,
        x_range=range(23, 20, -1),  # Reversed for right-to-left priority
        y_range=range(21, 24),
    ),
}


# UI corner configurations for all 4 players
UI_CORNER_CONFIGS = {
    0: UICornerConfig(
        player_index=0,
        corner_pos=CornerPosition.BOTTOM_LEFT,
        h_anchor=-1,  # Left edge
        v_anchor=-1,  # Bottom edge
        menu_h_direction=1,  # Menu expands right
        menu_v_direction=1,  # Menu expands up
    ),
    1: UICornerConfig(
        player_index=1,
        corner_pos=CornerPosition.BOTTOM_RIGHT,
        h_anchor=1,  # Right edge
        v_anchor=-1,  # Bottom edge
        menu_h_direction=-1,  # Menu expands left
        menu_v_direction=1,  # Menu expands up
    ),
    2: UICornerConfig(
        player_index=2,
        corner_pos=CornerPosition.TOP_LEFT,
        h_anchor=-1,  # Left edge
        v_anchor=1,  # Top edge
        menu_h_direction=1,  # Menu expands right
        menu_v_direction=-1,  # Menu expands down
    ),
    3: UICornerConfig(
        player_index=3,
        corner_pos=CornerPosition.TOP_RIGHT,
        h_anchor=1,  # Right edge
        v_anchor=1,  # Top edge
        menu_h_direction=-1,  # Menu expands left
        menu_v_direction=-1,  # Menu expands down
    ),
}


def get_board_corner_config(player_index: int) -> BoardCornerConfig:
    """
    Get board corner configuration for a player.

    Args:
        player_index: Player index (0-3)

    Returns:
        BoardCornerConfig for the player

    Raises:
        ValueError: If player_index is out of range
    """
    if player_index not in BOARD_CORNER_CONFIGS:
        raise ValueError(f"Invalid player_index: {player_index}. Must be 0-3.")
    return BOARD_CORNER_CONFIGS[player_index]


def get_ui_corner_config(player_index: int) -> UICornerConfig:
    """
    Get UI corner configuration for a player.

    Args:
        player_index: Player index (0-3)

    Returns:
        UICornerConfig for the player

    Raises:
        ValueError: If player_index is out of range
    """
    if player_index not in UI_CORNER_CONFIGS:
        raise ValueError(f"Invalid player_index: {player_index}. Must be 0-3.")
    return UI_CORNER_CONFIGS[player_index]
