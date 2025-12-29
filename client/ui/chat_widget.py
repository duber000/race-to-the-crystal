"""Chat widget for in-game communication.

Provides a chat overlay that can be added to any game view.
"""

import arcade
import arcade.gui
import logging
from typing import Optional, Callable, List
from dataclasses import dataclass
import time

from client.network_client import NetworkClient
from client.ui.async_arcade import schedule_async

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a single chat message."""
    player_name: str
    message: str
    timestamp: float
    player_id: Optional[str] = None


class ChatWidget:
    """
    Chat widget for displaying and sending chat messages.

    Shows recent chat messages and provides an input box.
    """

    def __init__(
        self,
        network_client: NetworkClient,
        x: float,
        y: float,
        width: float = 400,
        height: float = 250
    ):
        """
        Initialize chat widget.

        Args:
            network_client: Network client for sending messages
            x: X position (left edge)
            y: Y position (bottom edge)
            width: Widget width
            height: Widget height
        """
        self.network_client = network_client
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # Chat state
        self.messages: List[ChatMessage] = []
        self.max_messages = 50
        self.visible_messages = 8
        self.scroll_offset = 0

        # UI state
        self.visible = True
        self.input_active = False
        self.input_text = ""
        self.cursor_visible = True
        self.cursor_blink_time = 0.5
        self.last_cursor_toggle = time.time()

        # UI elements
        self.background_color = (0, 0, 0, 180)  # Semi-transparent black
        self.text_color = arcade.color.WHITE
        self.input_bg_color = (30, 30, 30, 220)
        self.border_color = arcade.color.CYAN

        logger.info("Chat widget created")

    def add_message(self, player_name: str, message: str, player_id: Optional[str] = None):
        """
        Add a chat message to the history.

        Args:
            player_name: Name of the player
            message: Chat message text
            player_id: Optional player ID
        """
        chat_msg = ChatMessage(
            player_name=player_name,
            message=message,
            timestamp=time.time(),
            player_id=player_id
        )

        self.messages.append(chat_msg)

        # Keep only recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

        # Auto-scroll to bottom
        self.scroll_offset = max(0, len(self.messages) - self.visible_messages)

    def toggle_visibility(self):
        """Toggle chat widget visibility."""
        self.visible = not self.visible
        logger.info(f"Chat visibility: {self.visible}")

    def toggle_input(self):
        """Toggle chat input active state."""
        self.input_active = not self.input_active

        if self.input_active:
            # Clear input when activating
            self.input_text = ""
            logger.info("Chat input activated")
        else:
            logger.info("Chat input deactivated")

    def on_key_press(self, key: int, modifiers: int):
        """
        Handle key press events.

        Args:
            key: Key code
            modifiers: Key modifiers
        """
        if not self.input_active:
            # Toggle input on Enter/Return when not active
            if key == arcade.key.ENTER or key == arcade.key.RETURN:
                self.toggle_input()
                return True  # Event handled
            return False

        # Input is active - handle typing
        if key == arcade.key.ENTER or key == arcade.key.RETURN:
            # Send message
            if self.input_text.strip():
                schedule_async(self._send_message(self.input_text.strip()))
            self.input_text = ""
            self.toggle_input()
            return True

        elif key == arcade.key.ESCAPE:
            # Cancel input
            self.input_text = ""
            self.toggle_input()
            return True

        elif key == arcade.key.BACKSPACE:
            # Delete character
            if self.input_text:
                self.input_text = self.input_text[:-1]
            return True

        return False

    def on_text(self, text: str):
        """
        Handle text input.

        Args:
            text: Character(s) to add
        """
        if not self.input_active:
            return False

        # Add character to input (limit length)
        if len(self.input_text) < 200:
            self.input_text += text
        return True

    async def _send_message(self, message: str):
        """
        Send chat message to server.

        Args:
            message: Message to send
        """
        try:
            from network.protocol import NetworkMessage
            from network.messages import MessageType

            chat_msg = NetworkMessage(
                type=MessageType.CHAT,
                timestamp=time.time(),
                player_id=self.network_client.player_id,
                data={"message": message}
            )

            await self.network_client.connection.send_message(chat_msg)
            logger.info(f"Sent chat message: {message}")

        except Exception as e:
            logger.error(f"Error sending chat message: {e}", exc_info=True)

    def update(self, delta_time: float):
        """
        Update chat widget (cursor blink, etc.).

        Args:
            delta_time: Time since last update
        """
        if not self.input_active:
            return

        # Update cursor blink
        current_time = time.time()
        if current_time - self.last_cursor_toggle > self.cursor_blink_time:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_toggle = current_time

    def draw(self):
        """Draw the chat widget."""
        if not self.visible:
            return

        # Draw background
        arcade.draw_rectangle_filled(
            self.x + self.width / 2,
            self.y + self.height / 2,
            self.width,
            self.height,
            self.background_color
        )

        # Draw border
        arcade.draw_rectangle_outline(
            self.x + self.width / 2,
            self.y + self.height / 2,
            self.width,
            self.height,
            self.border_color,
            2
        )

        # Draw messages
        message_y = self.y + self.height - 40
        message_height = 20

        visible_start = self.scroll_offset
        visible_end = min(visible_start + self.visible_messages, len(self.messages))

        for i in range(visible_start, visible_end):
            msg = self.messages[i]

            # Format: "PlayerName: message"
            display_text = f"{msg.player_name}: {msg.message}"

            # Draw message text (with wrapping if needed)
            arcade.draw_text(
                display_text,
                self.x + 10,
                message_y,
                self.text_color,
                font_size=12,
                width=self.width - 20,
                multiline=False
            )

            message_y -= message_height

        # Draw input box
        input_y = self.y + 5
        input_height = 30

        # Input background
        arcade.draw_rectangle_filled(
            self.x + self.width / 2,
            input_y + input_height / 2,
            self.width - 10,
            input_height,
            self.input_bg_color
        )

        # Input border (highlighted if active)
        border_color = arcade.color.YELLOW if self.input_active else self.border_color
        arcade.draw_rectangle_outline(
            self.x + self.width / 2,
            input_y + input_height / 2,
            self.width - 10,
            input_height,
            border_color,
            2
        )

        # Draw input text
        display_input = self.input_text
        if self.input_active and self.cursor_visible:
            display_input += "|"

        arcade.draw_text(
            display_input,
            self.x + 15,
            input_y + 8,
            self.text_color,
            font_size=12
        )

        # Draw help text if not active
        if not self.input_active and not self.input_text:
            arcade.draw_text(
                "Press Enter to chat...",
                self.x + 15,
                input_y + 8,
                (150, 150, 150),
                font_size=12,
                italic=True
            )
