"""
UI configuration parameter objects for Race to the Crystal.

This module provides parameter objects to reduce long parameter lists
in UI-related methods, improving readability and maintainability.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ViewportConfig:
    """
    Window and viewport dimensions.

    This parameter object groups all viewport-related dimensions
    to avoid passing them individually.

    Attributes:
        window_width: Width of the window in pixels
        window_height: Height of the window in pixels
        hud_height: Height of the HUD at top of screen
    """
    window_width: int
    window_height: int
    hud_height: int


@dataclass(frozen=True)
class UIStyleConfig:
    """
    UI styling constants and dimensions.

    This parameter object groups all UI styling parameters
    to avoid passing them individually.

    Attributes:
        margin: Margin from screen edges in pixels
        indicator_size: Size of corner indicator in pixels
        spacing: Base spacing between menu options in pixels
    """
    margin: int
    indicator_size: int
    spacing: float
