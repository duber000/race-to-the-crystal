"""Arcade-native UI components for Race to the Crystal."""

import arcade
from arcade.shape_list import ShapeElementList, create_rectangle_outline
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

from game.game_state import GameState
from shared.constants import PLAYER_COLORS


@dataclass
class Button:
    """Lightweight button state container."""

    rect: Tuple[float, float, float, float]  # (x, y, width, height)
    text: str
    color: Tuple[int, int, int]
    hover: bool = False
    enabled: bool = True


class UIManager:
    """Manages all UI rendering and interaction for the Arcade game window."""

    def __init__(self, window_width: int, window_height: int):
        """
        Initialize the UI manager.

        Args:
            window_width: Width of the game window
            window_height: Height of the game window
        """
        # Persistent visual elements
        self.panel_shapes = ShapeElementList()
        self.button_shapes = ShapeElementList()
        self.text_objects: List[arcade.Text] = []

        # Button state
        self.buttons: Dict[str, Button] = {}
        self.hovered_button: Optional[str] = None

        # Layout positions (updated on resize)
        self.layout = self._calculate_layout(window_width, window_height)

        # Initialize buttons
        button_y = 10
        button_width = 120
        button_height = 40
        button_spacing = 10

        self.buttons["end_turn"] = Button(
            rect=(
                window_width // 2 - button_width - button_spacing // 2,
                button_y,
                button_width,
                button_height
            ),
            text="End Turn",
            color=(0, 255, 0)  # Green
        )

        self.buttons["cancel"] = Button(
            rect=(
                window_width // 2 + button_spacing // 2,
                button_y,
                button_width,
                button_height
            ),
            text="Cancel",
            color=(255, 0, 255)  # Magenta
        )

    def _calculate_layout(self, window_width: int, window_height: int) -> Dict[str, any]:
        """
        Calculate UI element positions based on window dimensions.

        Args:
            window_width: Width of the game window
            window_height: Height of the game window

        Returns:
            Dictionary containing layout positions
        """
        return {
            "panel_x": window_width - 270,
            "panel_width": 250,
            "panel_y_start": window_height - 100,
            "height_per_player": 70,
            "generator_panel_height": 110,
            "button_y": 10,
            "button_width": 120,
            "button_height": 40,
            "button_spacing": 10,
        }

    def rebuild_visuals(self, game_state: GameState):
        """
        Rebuild all UI visuals based on current game state.

        Args:
            game_state: Current game state
        """
        # Clear existing shapes
        self.panel_shapes = ShapeElementList()
        self.button_shapes = ShapeElementList()
        self.text_objects = []

        # Build player info panel
        self._build_player_panel_shapes(game_state)

        # Build generator status panel
        self._build_generator_status_shapes(game_state)

        # Build buttons
        self._build_button_shapes()

    def _build_player_panel_shapes(self, game_state: GameState):
        """
        Build shapes and text for player info panel.

        Args:
            game_state: Current game state
        """
        panel_x = self.layout["panel_x"]
        panel_width = self.layout["panel_width"]
        panel_y_start = self.layout["panel_y_start"]
        height_per_player = self.layout["height_per_player"]

        # Get active players
        active_players = [p for p in game_state.players.values() if p.is_active]
        current_player_id = game_state.current_turn_player_id

        # Count alive tokens per player
        tokens_alive = {}
        for player in active_players:
            alive_count = sum(
                1 for token in game_state.tokens.values()
                if token.player_id == player.id and token.is_alive
            )
            tokens_alive[player.id] = alive_count

        # Build panel for each player
        for i, player in enumerate(active_players):
            y = panel_y_start - (i * height_per_player)
            color = PLAYER_COLORS[player.color.value]

            # Determine glow intensity based on current player
            is_current_player = (player.id == current_player_id)
            glow_intensity = 6 if is_current_player else 3

            # Create glow layers (outer to inner)
            for g in range(glow_intensity, 0, -1):
                alpha = int(180 / (g + 1))
                glow_rect = create_rectangle_outline(
                    panel_x + panel_width / 2,
                    y + 35,
                    panel_width + g * 4,
                    height_per_player - 5 + g * 4,
                    (*color, alpha),
                    border_width=max(1, 4 - g // 2)
                )
                self.panel_shapes.append(glow_rect)

            # Main bright border
            main_rect = create_rectangle_outline(
                panel_x + panel_width / 2,
                y + 35,
                panel_width,
                height_per_player - 5,
                color,
                border_width=3 if is_current_player else 2
            )
            self.panel_shapes.append(main_rect)

            # Player name text
            name_text = arcade.Text(
                player.name,
                panel_x + 10,
                y + 45,
                color,
                font_size=24,
                bold=True
            )
            self.text_objects.append(name_text)

            # Token count text
            count_text = arcade.Text(
                f"Tokens: {tokens_alive[player.id]}",
                panel_x + 10,
                y + 20,
                (255, 255, 255),
                font_size=18
            )
            self.text_objects.append(count_text)

    def _build_generator_status_shapes(self, game_state: GameState):
        """
        Build shapes and text for generator status panel.

        Args:
            game_state: Current game state
        """
        panel_x = self.layout["panel_x"]
        panel_width = self.layout["panel_width"]
        panel_height = self.layout["generator_panel_height"]

        # Calculate position below player panels
        active_players = [p for p in game_state.players.values() if p.is_active]
        player_count = len(active_players)
        panel_y_start = self.layout["panel_y_start"]
        height_per_player = self.layout["height_per_player"]
        panel_y = panel_y_start - (player_count * height_per_player) - 20

        # Subtle gray border with minimal glow (2 layers)
        for g in range(2, 0, -1):
            alpha = int(80 / (g + 1))
            glow_rect = create_rectangle_outline(
                panel_x + panel_width / 2,
                panel_y + panel_height / 2,
                panel_width + g * 2,
                panel_height + g * 2,
                (100, 100, 100, alpha),
                border_width=1
            )
            self.panel_shapes.append(glow_rect)

        # Main border
        main_rect = create_rectangle_outline(
            panel_x + panel_width / 2,
            panel_y + panel_height / 2,
            panel_width,
            panel_height,
            (150, 150, 150),
            border_width=1
        )
        self.panel_shapes.append(main_rect)

        # Title text
        title = arcade.Text(
            "Generators",
            panel_x + 10,
            panel_y + 80,
            (255, 255, 255),
            font_size=24,
            bold=True
        )
        self.text_objects.append(title)

        # Generator disabled count
        disabled_count = len([g for g in game_state.generators if g.is_disabled])
        total_count = len(game_state.generators)
        status = arcade.Text(
            f"Disabled: {disabled_count}/{total_count}",
            panel_x + 10,
            panel_y + 50,
            (255, 255, 255),
            font_size=18
        )
        self.text_objects.append(status)

        # Crystal requirement
        crystal_req = game_state.crystal.get_tokens_required(disabled_count)
        req_text = arcade.Text(
            f"Crystal Req: {crystal_req} tokens",
            panel_x + 10,
            panel_y + 25,
            (255, 255, 255),
            font_size=18
        )
        self.text_objects.append(req_text)

    def _build_button_shapes(self):
        """Build shapes and text for all buttons."""
        for button_name, button in self.buttons.items():
            x, y, width, height = button.rect
            center_x, center_y = x + width / 2, y + height / 2

            # Choose color and glow based on button state
            if not button.enabled:
                color = (128, 128, 128)
                glow_layers = 1
            elif button.hover:
                color = (255, 255, 255)
                glow_layers = 4
            else:
                color = button.color
                glow_layers = 2

            # Create glow layers (outer to inner)
            for g in range(glow_layers, 0, -1):
                alpha = int(180 / (g + 1))
                glow_rect = create_rectangle_outline(
                    center_x,
                    center_y,
                    width + g * 4,
                    height + g * 4,
                    (*color, alpha),
                    border_width=max(1, 3 - g // 2)
                )
                self.button_shapes.append(glow_rect)

            # Main border
            main_rect = create_rectangle_outline(
                center_x,
                center_y,
                width,
                height,
                color,
                border_width=2
            )
            self.button_shapes.append(main_rect)

            # Button text (centered)
            text_obj = arcade.Text(
                button.text,
                center_x,
                center_y,
                color,
                font_size=20,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )
            self.text_objects.append(text_obj)

    def draw(self):
        """Draw all UI elements (call under ui_camera.activate())."""
        self.panel_shapes.draw()
        self.button_shapes.draw()
        for text_obj in self.text_objects:
            text_obj.draw()

    def handle_mouse_motion(self, screen_x: float, screen_y: float):
        """
        Update button hover states based on mouse position.

        Args:
            screen_x: Mouse X coordinate in screen space
            screen_y: Mouse Y coordinate in screen space
        """
        old_hover = self.hovered_button
        self.hovered_button = None

        # Check each button for hover
        for name, button in self.buttons.items():
            x, y, w, h = button.rect
            if x <= screen_x <= x + w and y <= screen_y <= y + h:
                button.hover = True
                self.hovered_button = name
            else:
                button.hover = False

        # Rebuild buttons if hover changed
        if old_hover != self.hovered_button:
            self._rebuild_buttons()

    def handle_mouse_click(self, screen_x: float, screen_y: float) -> Optional[str]:
        """
        Handle mouse click on UI elements.

        Args:
            screen_x: Mouse X coordinate in screen space
            screen_y: Mouse Y coordinate in screen space

        Returns:
            Action string if button clicked ("end_turn", "cancel"), None otherwise
        """
        for name, button in self.buttons.items():
            if not button.enabled:
                continue

            x, y, w, h = button.rect
            if x <= screen_x <= x + w and y <= screen_y <= y + h:
                return name

        return None

    def _rebuild_buttons(self):
        """Rebuild only the button shapes (for hover state changes)."""
        self.button_shapes = ShapeElementList()
        # Remove existing button texts
        self.text_objects = [t for t in self.text_objects if not self._is_button_text(t)]
        # Rebuild button shapes and add new texts
        self._build_button_shapes()

    def _is_button_text(self, text_obj: arcade.Text) -> bool:
        """Check if a text object belongs to a button."""
        # Check if the text matches any button text
        for button in self.buttons.values():
            if text_obj.text == button.text:
                # Also check if it's center-aligned (buttons use center alignment)
                if (hasattr(text_obj, 'anchor_x') and text_obj.anchor_x == "center"):
                    return True
        return False

    def update_layout(self, window_width: int, window_height: int):
        """
        Recalculate layout positions when window is resized.

        Args:
            window_width: New window width
            window_height: New window height
        """
        self.layout = self._calculate_layout(window_width, window_height)

        # Update button positions
        button_y = self.layout["button_y"]
        button_width = self.layout["button_width"]
        button_height = self.layout["button_height"]
        button_spacing = self.layout["button_spacing"]

        self.buttons["end_turn"].rect = (
            window_width // 2 - button_width - button_spacing // 2,
            button_y,
            button_width,
            button_height
        )

        self.buttons["cancel"].rect = (
            window_width // 2 + button_spacing // 2,
            button_y,
            button_width,
            button_height
        )
