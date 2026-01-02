"""Network game view for multiplayer games.

Integrates GameWindow with NetworkClient for server-authoritative gameplay.
"""

import arcade
import arcade.gui
import logging
from typing import Optional, Callable, Dict

from client.game_window import GameView
from client.network_client import NetworkClient
from client.ui.async_arcade import schedule_async
from game.game_state import GameState
from game.ai_actions import MoveAction, AttackAction, DeployAction, EndTurnAction
from network.messages import MessageType
from shared.constants import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT

logger = logging.getLogger(__name__)


class NetworkGameView(arcade.View):
    """
    Network multiplayer game view.

    Wraps GameWindow and handles network synchronization with server.
    """

    def __init__(
        self,
        network_client: NetworkClient,
        initial_game_state: Optional[GameState] = None
    ):
        """
        Initialize network game view.

        Args:
            network_client: Connected network client
            initial_game_state: Initial game state (from server)
        """
        super().__init__()

        self.network_client = network_client

        # Create a dummy game state if not provided
        # The server will send the real state
        if initial_game_state:
            self.game_state = initial_game_state
        else:
            self.game_state = GameState()

        # Game view (will be created in setup)
        self.game_view: Optional[GameView] = None

        # Network state
        self.waiting_for_server = False
        self.last_action_sent = None

        # Callbacks
        self.on_game_end: Optional[Callable[[str], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None

        # Set up network message handler
        self.network_client.on_message = self._handle_network_message
        self.network_client.on_disconnect = self._handle_disconnect
        self.network_client.on_reconnect = self._handle_reconnect

        logger.info("Network game view created")

    def setup(self):
        """Set up the game view."""
        # GameView is now a proper View that can be embedded directly
        # It will be created in on_show_view()

        logger.info("Network game view setup complete")

    def on_show_view(self):
        """Called when this view is shown."""
        logger.info(f"Network game view shown with game state: {len(self.game_state.players)} players, {len(self.game_state.tokens)} tokens")

        # Create game view (using new View architecture)
        self.game_view = GameView(
            self.game_state,
            start_in_3d=False,
            is_network_game=True,
            network_client=self.network_client
        )

        # Show the game view within the same window
        self.window.show_view(self.game_view)

        # Override game view's action execution
        # Intercept actions and send to server instead
        self._hook_game_view()

        logger.info("Game view created for network play")

    def _hook_game_view(self):
        """
        Hook into GameView to intercept actions.

        Replaces local action execution with network sending.
        """
        if not self.game_view:
            return

        # Store original methods
        original_on_mouse_press = self.game_view.on_mouse_press
        original_on_key_press = self.game_view.on_key_press

        # Create wrapped versions that send to server
        def network_on_mouse_press(x, y, button, modifiers):
            """Intercept mouse press and send action to server."""
            # Call original to update UI state (selection, etc.)
            original_on_mouse_press(x, y, button, modifiers)

            # Check if an action was generated
            # This is a simplified approach - in reality we'd need to detect
            # what action the player is trying to make
            # For now, we'll let the original GameWindow handle input
            # and intercept at the game_state level

        def network_on_key_press(key, modifiers):
            """Intercept key press (like Space for end turn)."""
            if key == arcade.key.SPACE or key == arcade.key.ENTER:
                # End turn
                if not self.waiting_for_server:
                    schedule_async(self._send_end_turn())
                return

            # Pass through other keys
            original_on_key_press(key, modifiers)

        # Replace methods
        self.game_view.on_key_press = network_on_key_press

        # Hook game state to intercept actual action execution
        # Store original methods
        original_move_token = self.game_state.move_token
        original_attack_token = self.game_state.attack_token
        original_deploy_token = self.game_state.deploy_token
        original_end_turn = self.game_state.end_turn

        def network_move_token(token_id, destination):
            """Intercept move and send to server."""
            if not self.waiting_for_server:
                schedule_async(self._send_move(token_id, destination))
                self.waiting_for_server = True
                return True  # Pretend success, server will validate
            return False

        def network_attack_token(attacker_id, target_id):
            """Intercept attack and send to server."""
            if not self.waiting_for_server:
                schedule_async(self._send_attack(attacker_id, target_id))
                self.waiting_for_server = True
                return True
            return False

        def network_deploy_token(player_id, health_value, position):
            """Intercept deploy and send to server."""
            if not self.waiting_for_server:
                schedule_async(self._send_deploy(health_value, position))
                self.waiting_for_server = True
                return None  # Return None like the original method
            return None

        def network_end_turn():
            """Intercept end turn and send to server."""
            if not self.waiting_for_server:
                schedule_async(self._send_end_turn())
                self.waiting_for_server = True
                return
            return

        # Replace game state methods
        self.game_state.move_token = network_move_token
        self.game_state.attack_token = network_attack_token
        self.game_state.deploy_token = network_deploy_token
        self.game_state.end_turn = network_end_turn

    # --- Network Action Sending ---

    async def _send_move(self, token_id: int, destination: tuple):
        """Send move action to server."""
        action = MoveAction(token_id=token_id, destination=destination)
        success = await self.network_client.send_action(action)
        if not success:
            logger.error("Failed to send move action")
            self.waiting_for_server = False

    async def _send_attack(self, attacker_id: int, target_id: int):
        """Send attack action to server."""
        action = AttackAction(attacker_id=attacker_id, target_id=target_id)
        success = await self.network_client.send_action(action)
        if not success:
            logger.error("Failed to send attack action")
            self.waiting_for_server = False

    async def _send_deploy(self, health_value: int, position: tuple):
        """Send deploy action to server."""
        action = DeployAction(health_value=health_value, position=position)
        success = await self.network_client.send_action(action)
        if not success:
            logger.error("Failed to send deploy action")
            self.waiting_for_server = False

    async def _send_end_turn(self):
        """Send end turn action to server."""
        action = EndTurnAction()
        success = await self.network_client.send_action(action)
        if not success:
            logger.error("Failed to send end turn action")
            self.waiting_for_server = False

    # --- Network Message Handling ---

    async def _handle_network_message(self, message):
        """
        Handle incoming network messages.

        Args:
            message: NetworkMessage from server
        """
        logger.info(f"NetworkGameView received message: {message.type.value}")

        try:
            if message.type == MessageType.FULL_STATE:
                # Full game state update from server
                await self._handle_full_state(message)

            elif message.type == MessageType.STATE_UPDATE:
                # Delta state update
                await self._handle_state_update(message)

            elif message.type == MessageType.INVALID_ACTION:
                # Action was rejected
                await self._handle_invalid_action(message)

            elif message.type == MessageType.GAME_WON:
                # Game ended
                await self._handle_game_won(message)

            elif message.type == MessageType.ERROR:
                # Error message
                data = message.data or {}
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Server error: {error_msg}")
                self.waiting_for_server = False

        except Exception as e:
            logger.error(f"Error handling game message: {e}", exc_info=True)

    async def _handle_full_state(self, message):
        """Handle FULL_STATE message with complete game state."""
        data = message.data or {}
        game_state_data = data.get("game_state")

        if not game_state_data:
            logger.warning("No game state in FULL_STATE message")
            return

        # Deserialize game state from server
        logger.info("Received full game state from server")

        try:
            # Use GameState.from_dict() to properly deserialize
            self.game_state = GameState.from_dict(game_state_data)
            logger.info(f"Game state deserialized - Players: {len(self.game_state.players)}, Tokens: {len(self.game_state.tokens)}")

            # Update game view to use new state
            if self.game_view:
                logger.info("Updating game view with new state and calling setup()")
                self.game_view.game_state = self.game_state
                self.game_view.setup()
                logger.info("Game view setup complete")
            else:
                logger.warning("No game view exists yet - will be created with this state")

        except Exception as e:
            logger.error(f"Failed to deserialize game state: {e}", exc_info=True)

        self.waiting_for_server = False

    async def _handle_state_update(self, message):
        """Handle STATE_UPDATE message with delta changes."""
        logger.info("Received state update from server")
        self.waiting_for_server = False

        # Refresh display
        if self.game_view:
            self.game_view.setup()

    async def _handle_invalid_action(self, message):
        """Handle INVALID_ACTION message when action was rejected."""
        data = message.data or {}
        action_type = data.get("action_type", "unknown")
        reason = data.get("reason", "Unknown reason")

        logger.warning(f"Action rejected by server: {action_type} - {reason}")
        self.waiting_for_server = False

        # Show error message to player
        error_message = f"Invalid Action!\n\n{action_type} was rejected:\n{reason}"

        # Create a simple error dialog
        message_box = arcade.gui.UIMessageBox(
            width=400,
            height=200,
            message_text=error_message,
            buttons=["OK"]
        )

        # Add to current view's UI manager if available
        if self.game_view and hasattr(self.game_view, 'manager'):
            # Game view doesn't have a UI manager, so we'll need to create one
            # For now, just log it prominently
            logger.error(f"ACTION REJECTED: {action_type} - {reason}")
            # TODO: Add UI manager to GameView for displaying error dialogs

    async def _handle_game_won(self, message):
        """Handle GAME_WON message."""
        data = message.data or {}
        winner_id = data.get("winner_id", "")
        winner_name = data.get("winner_name", "Unknown")

        logger.info(f"Game ended! Winner: {winner_name}")

        # Notify callback
        if self.on_game_end:
            self.on_game_end(winner_name)

    async def _handle_disconnect(self):
        """Handle disconnect from server."""
        logger.warning("Disconnected from server")

        # Notify callback
        if self.on_disconnect:
            self.on_disconnect()

    async def _handle_reconnect(self):
        """Handle successful reconnection."""
        logger.info("Reconnected to server")

        # Request full state sync
        # The server should automatically send it, but we can request if needed
