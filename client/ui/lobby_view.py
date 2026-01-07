"""Lobby view for network multiplayer games.

Displays connected players, ready status, and game start controls.
"""

import arcade
import arcade.gui
import logging
import pyperclip
from typing import Optional, Callable, Dict, List
from queue import Queue

from client.network_client import NetworkClient
from client.ui.async_arcade import schedule_async
from client.ui.chat_widget import ChatWidget
from network.messages import MessageType
from shared.constants import BACKGROUND_COLOR, PLAYER_COLORS

logger = logging.getLogger(__name__)


class LobbyView(arcade.View):
    """
    Lobby view for network multiplayer games.

    Shows:
    - Game name
    - Connected players with ready status
    - Ready/Unready button
    - Start game button (host only)
    - Leave game button
    """

    def __init__(self, network_client: NetworkClient, is_host: bool = False):
        """
        Initialize lobby view.

        Args:
            network_client: Connected network client
            is_host: True if this player is the host
        """
        super().__init__()

        self.network_client = network_client
        self.is_host = is_host
        self.manager = arcade.gui.UIManager()

        # Lobby state
        self.game_name = "Lobby"
        self.max_players = 4
        self.players: Dict[str, Dict] = {}  # player_id -> player_info
        self.is_ready = False
        self.game_started = False
        self.pending_game_state = (
            None  # Store FULL_STATE that arrives before game view is ready
        )

        # UI elements
        self.title_text = None
        self.game_id_text = None
        self.copy_feedback_text = None
        self.copy_feedback_timer = 0.0
        self.status_text = None
        self.player_texts: List[arcade.Text] = []

        # Message queue for polling pattern (thread-safe)
        # Background thread puts messages here, on_update() processes them
        self._message_queue: Queue = Queue()

        # UI update flags
        self._needs_text_update = False  # Set when text needs updating
        self._needs_initial_setup = False  # Set when initial setup needed

        # Chat widget (will be created in setup)
        self.chat_widget: Optional[ChatWidget] = None

        # Callbacks
        self.on_game_start: Optional[Callable[[Dict], None]] = None
        self.on_leave: Optional[Callable[[], None]] = None

        # Set up network message handler
        self.network_client.on_message = self._handle_network_message

        logger.info(f"Lobby view created (host={is_host})")

    def setup(self):
        """Set up the lobby UI."""
        self.manager.clear()

        # Title
        self.title_text = arcade.Text(
            f"LOBBY: {self.game_name}",
            self.window.width // 2,
            self.window.height - 80,
            arcade.color.CYAN,
            font_size=32,
            anchor_x="center",
            bold=True,
        )

        # Game ID display
        game_id = self.network_client.game_id or "Unknown"
        self.game_id_text = arcade.Text(
            f"Game ID: {game_id}",
            self.window.width // 2,
            self.window.height - 120,
            arcade.color.GRAY,
            font_size=14,
            anchor_x="center",
        )

        # Copy feedback text (shown briefly after copying)
        self.copy_feedback_text = arcade.Text(
            "Copied!",
            self.window.width // 2,
            self.window.height - 145,
            arcade.color.GREEN,
            font_size=12,
            anchor_x="center",
            bold=True,
        )

        # Status text
        status = "You are the host" if self.is_host else "Waiting for host to start..."
        self.status_text = arcade.Text(
            status,
            self.window.width // 2,
            self.window.height - 170,
            arcade.color.WHITE,
            font_size=16,
            anchor_x="center",
        )

        # Create button layout
        v_box = arcade.gui.UIBoxLayout(space_between=15)

        button_style = {
            "font_size": 18,
            "height": 50,
            "width": 250,
        }

        # Copy Game ID button
        copy_button = arcade.gui.UIFlatButton(text="Copy Game ID", **button_style)
        copy_button.on_click = self._on_copy_game_id_click
        v_box.add(copy_button)

        # Ready/Unready button
        ready_text = "Unready" if self.is_ready else "Ready"
        self.ready_button = arcade.gui.UIFlatButton(text=ready_text, **button_style)
        self.ready_button.on_click = self._on_ready_click
        v_box.add(self.ready_button)

        # Start game button (host only)
        if self.is_host:
            self.start_button = arcade.gui.UIFlatButton(
                text="Start Game", **button_style
            )
            self.start_button.on_click = self._on_start_click
            v_box.add(self.start_button)

        # Leave button
        leave_button = arcade.gui.UIFlatButton(text="Leave Lobby", **button_style)
        leave_button.on_click = self._on_leave_click
        v_box.add(leave_button)

        # Position buttons at bottom
        self.manager.add(
            arcade.gui.UIAnchorLayout(
                anchor_x="center_x", anchor_y="bottom", children=[v_box], align_y=50
            )
        )

        # Build player list display
        self._update_player_list()

        # Create chat widget
        if self.window:
            self.chat_widget = ChatWidget(
                self.network_client, x=10, y=120, width=400, height=250
            )

    def on_show_view(self):
        """Called when this view is shown."""
        # Defer setup to on_update to ensure GL context is ready
        self._needs_initial_setup = True
        self.manager.enable()
        arcade.set_background_color(BACKGROUND_COLOR)
        logger.info("Lobby view shown")

    def on_hide_view(self):
        """Called when this view is hidden."""
        self.manager.disable()

    def on_update(self, delta_time: float):
        """Update the lobby view."""
        # Perform initial setup if needed (deferred from on_show_view)
        # This ensures GL context is fully ready before creating text objects
        if self._needs_initial_setup:
            self._needs_initial_setup = False
            self.setup()
            logger.info("Deferred initial setup completed")

        # Apply deferred text updates from previous frame (if needed)
        # This ensures text GL resources are created before drawing
        if self._needs_text_update:
            self._needs_text_update = False
            self._apply_text_updates()

        # Poll message queue and process all pending messages
        # This updates data and sets _needs_text_update flag
        while not self._message_queue.empty():
            try:
                message = self._message_queue.get_nowait()
                self._process_message(message)
            except Exception as e:
                logger.error(f"Error processing queued message: {e}", exc_info=True)

        # Update chat widget
        if self.chat_widget:
            self.chat_widget.update(delta_time)

        # Update copy feedback timer
        if self.copy_feedback_timer > 0:
            self.copy_feedback_timer -= delta_time

    def _apply_text_updates(self):
        """Apply text updates (deferred to avoid OpenGL timing issues)."""
        # Update title
        if self.title_text:
            self.title_text.text = f"LOBBY: {self.game_name}"

        # Update game ID
        if self.game_id_text and self.network_client.game_id:
            self.game_id_text.text = f"Game ID: {self.network_client.game_id}"

        # Rebuild player list
        self._update_player_list()

    def on_draw(self):
        """Render the lobby."""
        self.clear()

        # Draw title and status
        if self.title_text:
            self.title_text.draw()
        if self.game_id_text:
            self.game_id_text.draw()
        if self.copy_feedback_timer > 0 and self.copy_feedback_text:
            self.copy_feedback_text.draw()
        if self.status_text:
            self.status_text.draw()

        # Draw player list
        for text in self.player_texts:
            text.draw()

        # Draw UI manager (buttons)
        self.manager.draw()

        # Draw chat widget
        if self.chat_widget:
            self.chat_widget.draw()

    def on_key_press(self, key: int, modifiers: int):
        """Handle key press events."""
        # Let chat widget handle keys first
        if self.chat_widget and self.chat_widget.on_key_press(key, modifiers):
            return  # Chat widget handled the event

    def on_text(self, text: str):
        """Handle text input events."""
        # Let chat widget handle text input
        if self.chat_widget:
            self.chat_widget.on_text(text)

    def _update_player_list(self):
        """Rebuild the player list display."""
        self.player_texts = []

        # Title for player list with count
        y_pos = self.window.height - 200
        player_count_text = f"Players: {len(self.players)}/{self.max_players}"
        title = arcade.Text(
            player_count_text,
            self.window.width // 2,
            y_pos,
            arcade.color.WHITE,
            font_size=20,
            anchor_x="center",
            bold=True,
        )
        self.player_texts.append(title)

        # List players (adjusted position for game ID display)
        y_pos -= 60
        for i, (player_id, player_info) in enumerate(self.players.items()):
            name = player_info.get("player_name", "Unknown")
            is_ready = player_info.get("is_ready", False)
            color_index = player_info.get("color_index", 0)

            # Get player color (PLAYER_COLORS is a list, not dict)
            if 0 <= color_index < len(PLAYER_COLORS):
                color = PLAYER_COLORS[color_index]
            else:
                color = arcade.color.WHITE

            # Format: "Player Name [READY]" or "Player Name"
            ready_status = " [READY]" if is_ready else ""
            host_marker = (
                " (Host)"
                if player_id == self.network_client.player_id and self.is_host
                else ""
            )
            text_content = f"{name}{host_marker}{ready_status}"

            player_text = arcade.Text(
                text_content,
                self.window.width // 2,
                y_pos,
                color,
                font_size=18,
                anchor_x="center",
            )
            self.player_texts.append(player_text)
            y_pos -= 35

    async def _handle_network_message(self, message):
        """
        Handle incoming network messages (runs on background thread).

        Just queues messages for processing on main thread.

        Args:
            message: NetworkMessage from server
        """
        logger.debug(f"Lobby received: {message.type.value}, queuing for processing")

        # Queue message for processing on main thread (thread-safe)
        self._message_queue.put(message)

    def _process_message(self, message):
        """
        Process a network message (runs on main thread).

        All UI updates happen here, safely on the main thread.

        Args:
            message: NetworkMessage from server
        """
        try:
            if message.type == MessageType.CREATE_GAME:
                self._handle_create_game(message)

            elif message.type == MessageType.PLAYER_JOINED:
                self._handle_player_joined(message)

            elif message.type == MessageType.PLAYER_LEFT:
                self._handle_player_left(message)

            elif message.type == MessageType.READY:
                self._handle_ready_update(message)

            elif message.type == MessageType.START_GAME:
                self._handle_game_start(message)

            elif message.type == MessageType.FULL_STATE:
                self._handle_full_state(message)

            elif message.type == MessageType.CHAT:
                self._handle_chat_message(message)

            elif message.type == MessageType.ERROR:
                data = message.data or {}
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Server error: {error_msg}")

        except Exception as e:
            logger.error(
                f"Error processing message {message.type.value}: {e}", exc_info=True
            )

    def _handle_create_game(self, message):
        """Handle CREATE_GAME response - initialize lobby with host player (main thread)."""
        data = message.data or {}

        # Extract and store game ID
        game_id = data.get("game_id")
        if game_id:
            self.network_client.game_id = game_id
            logger.info(f"Game ID set: {game_id}")

        # Update lobby info
        self.game_name = data.get("game_name", "Lobby")
        self.max_players = data.get("max_players", 4)
        players_list = data.get("players", [])

        # Clear and populate player list
        self.players.clear()
        for player_info in players_list:
            player_id = player_info.get("player_id")
            if player_id:
                self.players[player_id] = {
                    "player_name": player_info.get("player_name", "Unknown"),
                    "is_ready": player_info.get("is_ready", False),
                    "color_index": player_info.get("color_index", 0),
                }

        logger.info(
            f"Lobby created: {self.game_name} with {len(self.players)} player(s), max {self.max_players}"
        )

        # Mark text for update on next frame
        self._needs_text_update = True

    def _handle_player_joined(self, message):
        """Handle PLAYER_JOINED message (main thread)."""
        data = message.data or {}
        player_id = data.get("player_id")
        player_name = data.get("player_name", "Unknown")
        lobby_data = data.get("lobby", {})

        # Try to get color_index from lobby data if available
        color_index = data.get("color_index", 0)

        # If lobby data is available, use it to get the complete player info
        if lobby_data:
            players_list = lobby_data.get("players", [])
            # Find the player in the lobby's player list
            for player_info in players_list:
                if player_info.get("player_id") == player_id:
                    color_index = player_info.get("color_index", 0)
                    break

        if player_id:
            logger.info(f"Player joined: {player_name}")
            self.players[player_id] = {
                "player_name": player_name,
                "is_ready": False,
                "color_index": color_index,
            }
            self._needs_text_update = True

    def _handle_player_left(self, message):
        """Handle PLAYER_LEFT message (main thread)."""
        data = message.data or {}
        player_id = data.get("player_id")

        if player_id and player_id in self.players:
            player_name = self.players[player_id].get("player_name", "Unknown")
            logger.info(f"Player left: {player_name}")
            del self.players[player_id]
            self._needs_text_update = True

    def _handle_ready_update(self, message):
        """Handle READY message (main thread)."""
        data = message.data or {}
        player_id = data.get("player_id")
        is_ready = data.get("ready", False)

        if player_id and player_id in self.players:
            logger.info(f"Player ready update: {player_id[:8]} = {is_ready}")
            self.players[player_id]["is_ready"] = is_ready
            self._needs_text_update = True

    def _handle_game_start(self, message):
        """Handle START_GAME message (main thread)."""
        logger.info("Game starting!")
        self.game_started = True

        # Update status text
        if self.status_text:
            self.status_text.text = "Game starting..."

        # Prepare callback data
        data = message.data or {}
        if self.pending_game_state:
            data["initial_game_state"] = self.pending_game_state
            logger.info("Passing pending game state to NetworkGameView")

        # Notify callback (this triggers view change)
        if self.on_game_start:
            self.on_game_start(data)

    def _handle_full_state(self, message):
        """Handle FULL_STATE message (main thread)."""
        data = message.data or {}
        game_state_data = data.get("game_state", {})
        lobby_data = data.get("lobby", {})

        # If we receive a FULL_STATE with actual game state data (tokens, board, etc.),
        # it's for the game view, not the lobby. Store it for NetworkGameView.
        # Check if game_state has the "tokens" field which indicates it's actual game state
        if game_state_data and "tokens" in game_state_data:
            logger.info(
                "Lobby view received game FULL_STATE - storing for NetworkGameView"
            )
            self.pending_game_state = game_state_data
            return  # Don't process as lobby update

        # Update lobby info
        if lobby_data:
            # Extract and store game ID if present
            game_id = lobby_data.get("game_id")
            if game_id and not self.network_client.game_id:
                self.network_client.game_id = game_id
                logger.info(f"Game ID set from FULL_STATE: {game_id}")

            self.game_name = lobby_data.get("game_name", "Lobby")
            self.max_players = lobby_data.get("max_players", 4)
            players_list = lobby_data.get("players", [])

            # Clear and populate player list
            self.players.clear()
            for player_info in players_list:
                player_id = player_info.get("player_id")
                if player_id:
                    self.players[player_id] = {
                        "player_name": player_info.get("player_name", "Unknown"),
                        "is_ready": player_info.get("is_ready", False),
                        "color_index": player_info.get("color_index", 0),
                    }

            # Mark text for update on next frame
            self._needs_text_update = True

    def _handle_chat_message(self, message):
        """Handle CHAT message (main thread)."""
        data = message.data or {}
        player_name = data.get("player_name", "Unknown")
        chat_text = data.get("message", "")

        if chat_text and self.chat_widget:
            logger.debug(f"Chat from {player_name}: {chat_text}")
            self.chat_widget.add_message(player_name, chat_text, message.player_id)

    def _on_copy_game_id_click(self, event):
        """Handle copy game ID button click."""
        game_id = self.network_client.game_id
        if game_id:
            try:
                pyperclip.copy(game_id)
                logger.info(f"Copied game ID to clipboard: {game_id[:8]}...")
                # Show feedback
                self.copy_feedback_timer = 2.0  # Show "Copied!" for 2 seconds
            except Exception as e:
                logger.error(f"Failed to copy game ID to clipboard: {e}")
        else:
            logger.warning("No game ID available to copy")

    def _on_ready_click(self, event):
        """Handle ready button click."""
        self.is_ready = not self.is_ready
        logger.info(f"Setting ready status: {self.is_ready}")

        # Send ready message to server
        schedule_async(self.network_client.set_ready(self.is_ready))

        # Update button text
        self.ready_button.text = "Unready" if self.is_ready else "Ready"

    def _on_start_click(self, event):
        """Handle start game button click (host only)."""
        if not self.is_host:
            return

        logger.info("Host starting game...")

        # Check if all players are ready
        all_ready = all(p.get("is_ready", False) for p in self.players.values())

        if not all_ready:
            logger.warning("Not all players are ready")
            # Show error message
            not_ready_players = [
                p.get("name", "Unknown")
                for p in self.players.values()
                if not p.get("is_ready", False)
            ]
            message = f"Cannot start game!\n\nWaiting for players to be ready:\n{', '.join(not_ready_players)}"

            message_box = arcade.gui.UIMessageBox(
                width=400, height=200, message_text=message, buttons=["OK"]
            )
            self.manager.add(message_box)
            return

        # Send start game message
        # Note: The server will handle this and send START_GAME back
        schedule_async(self._send_start_game())

    async def _send_start_game(self):
        """Send start game request to server."""
        from network.protocol import NetworkMessage
        import time

        msg = NetworkMessage(
            type=MessageType.START_GAME,
            timestamp=time.time(),
            player_id=self.network_client.player_id,
            data={"game_id": self.network_client.game_id},
        )
        await self.network_client.connection.send_message(msg)

    def _on_leave_click(self, event):
        """Handle leave button click."""
        logger.info("Leaving lobby...")

        # Leave game on server
        schedule_async(self.network_client.leave_game())

        # Notify callback
        if self.on_leave:
            self.on_leave()
