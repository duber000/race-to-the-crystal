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
        initial_game_state: Optional[GameState] = None,
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
        self._pending_move_rollback = None

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
        logger.info(
            f"Network game view shown with game state: {len(self.game_state.players)} players, {len(self.game_state.tokens)} tokens"
        )

        # Create game view (using new View architecture)
        self.game_view = GameView(
            self.game_state,
            start_in_3d=False,
            is_network_game=True,
            network_client=self.network_client,
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

        def network_on_key_press(symbol, modifiers):
            """Intercept key press (like Space for end turn)."""
            if symbol == arcade.key.SPACE or symbol == arcade.key.ENTER:
                # End turn
                logger.info(
                    f"Space/Enter pressed. waiting_for_server={self.waiting_for_server}"
                )
                if not self.waiting_for_server:
                    logger.info("Sending END_TURN to server...")
                    schedule_async(self._send_end_turn())
                    self.waiting_for_server = True
                else:
                    logger.info("Already waiting for server, ignoring key press")
                return

            # Pass through other keys
            original_on_key_press(symbol, modifiers)

        # Store original _handle_end_turn (now in InputHandler)
        if not self.game_view.input_handler:
            logger.warning("InputHandler not yet initialized, skipping end turn hook")
            return

        original_handle_end_turn = self.game_view.input_handler._handle_end_turn

        def network_handle_end_turn():
            """Intercept _handle_end_turn to prevent local turn advancement."""
            logger.info("InputHandler._handle_end_turn() called - intercepting!")
            if not self.waiting_for_server:
                logger.info(
                    "Sending END_TURN to server instead of advancing locally..."
                )
                schedule_async(self._send_end_turn())
                self.waiting_for_server = True
                # Clear selection like the original does
                if self.game_view.input_handler:
                    self.game_view.input_handler.selected_token_id = None
                    self.game_view.input_handler.valid_moves = []
            else:
                logger.info("Already waiting for server, ignoring _handle_end_turn")

        # Replace methods
        self.game_view.on_key_press = network_on_key_press
        self.game_view.input_handler._handle_end_turn = network_handle_end_turn

        # Hook game state methods
        self._hook_game_state_methods()

    def _hook_game_state_methods(self):
        """
        Hook game state methods to intercept actions and send to server.

        This method can be called multiple times as the game state gets updated.
        """
        # Store original methods from the current game_state
        original_move_token = self.game_state.move_token
        original_attack_token = self.game_state.attack_token
        original_deploy_token = self.game_state.deploy_token
        original_end_turn = self.game_state.end_turn

        def network_move_token(token_id, new_position):
            """Intercept move and send to server with client-side prediction."""
            if not self.waiting_for_server:
                # Store original position for potential rollback
                original_token = self.game_state.get_token(token_id)
                if original_token:
                    self._pending_move_rollback = {
                        "token_id": token_id,
                        "original_position": original_token.position,  # tuple is immutable, no need to copy
                        "original_health": original_token.health,
                    }
                else:
                    self._pending_move_rollback = None
                
                # Apply client-side prediction - update local state immediately
                success = original_move_token(token_id, new_position)
                
                if success:
                    schedule_async(self._send_move(token_id, new_position))
                    self.waiting_for_server = True
                    return True
                else:
                    # Local validation failed, don't send to server
                    return False
            return False

        def network_attack_token(attacker_id, defender_id):
            """Intercept attack and send to server."""
            if not self.waiting_for_server:
                schedule_async(self._send_attack(attacker_id, defender_id))
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
            logger.info(
                f"network_end_turn() called! waiting_for_server={self.waiting_for_server}"
            )
            if not self.waiting_for_server:
                logger.info("Scheduling _send_end_turn()...")
                schedule_async(self._send_end_turn())
                self.waiting_for_server = True
                logger.info("END_TURN scheduled and waiting_for_server set to True")
                return
            else:
                logger.info("Already waiting for server, skipping END_TURN send")
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
        action = AttackAction(attacker_id=attacker_id, defender_id=target_id)
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
        logger.info("_send_end_turn() called - creating END_TURN action")
        action = EndTurnAction()
        logger.info(f"Sending END_TURN action to server via network_client...")
        success = await self.network_client.send_action(action)
        if not success:
            logger.error("Failed to send end turn action")
            self.waiting_for_server = False
        else:
            logger.info("END_TURN action sent successfully")

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

            elif message.type == MessageType.CHAT:
                # Chat message
                await self._handle_chat_message(message)

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
            logger.info(
                f"Game state deserialized - Players: {len(self.game_state.players)}, Tokens: {len(self.game_state.tokens)}"
            )

            # Update game view to use new state
            if self.game_view:
                logger.info("Updating game view with new state")

                self.game_view.game_state = self.game_state

                # Sync tokens instead of full setup (preserves/triggers animations)
                self.game_view.renderer_2d.sync_tokens(self.game_state)

                # Sync 3D tokens
                if hasattr(self.game_view.renderer_3d, "sync_tokens"):
                    self.game_view.renderer_3d.sync_tokens(
                        self.game_state, self.game_view.window.ctx
                    )

                # We still need to recreate board sprites for generator/crystal updates
                # but we don't want to nuke the tokens
                self.game_view.renderer_2d.create_board_sprites(
                    self.game_state.board,
                    self.game_state.generators,
                    self.game_state.crystal,
                    self.game_view.mystery_animations,
                )

                # Rebuild UI
                self.game_view.ui_manager.rebuild_visuals(self.game_state)

                # Update InputHandler reference
                if self.game_view.input_handler:
                    self.game_view.input_handler.game_state = self.game_state
                    self.game_view.action_handler.game_state = self.game_state

                # Sync the InputHandler's local turn_phase with the server's game_state.turn_phase
                if self.game_view.input_handler:
                    self.game_view.input_handler.turn_phase = self.game_state.turn_phase
                    logger.info(
                        f"Synced turn_phase to {self.game_state.turn_phase.name}"
                    )

                # Re-hook the game state methods since we just replaced the game state object
                self._hook_game_state_methods()
                logger.info("Re-hooked game state methods after state update")
            else:
                logger.warning(
                    "No game view exists yet - will be created with this state"
                )

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

    def _rollback_move_prediction(self):
        """Rollback client-side prediction when server rejects a move."""
        if not self._pending_move_rollback:
            return
            
        rollback_info = self._pending_move_rollback
        token_id = rollback_info["token_id"]
        original_position = rollback_info["original_position"]
        original_health = rollback_info["original_health"]
        
        # Get the token and revert its state
        token = self.game_state.get_token(token_id)
        if token:
            logger.info(f"Rolling back token {token_id} from {token.position} to {original_position}")
            
            # Revert position
            token.position = original_position.copy()
            
            # Revert health if it changed (e.g., from mystery square)
            if token.health != original_health:
                token.health = original_health
                
            # Update visuals to reflect rollback
            if self.game_view:
                # Update 2D renderer
                if hasattr(self.game_view.renderer_2d, 'sync_tokens'):
                    self.game_view.renderer_2d.sync_tokens(self.game_state)
                    
                # Update 3D renderer
                if hasattr(self.game_view.renderer_3d, 'sync_tokens'):
                    self.game_view.renderer_3d.sync_tokens(self.game_state, self.game_view.window.ctx)
                    
                # Clear selection
                if self.game_view.input_handler:
                    self.game_view.input_handler.selected_token_id = None
                    self.game_view.input_handler.valid_moves = set()
                    self.game_view.renderer_2d.update_selection_visuals(
                        None, set(), self.game_state
                    )

    async def _handle_invalid_action(self, message):
        """Handle INVALID_ACTION message when action was rejected."""
        data = message.data or {}
        action_type = data.get("action_type", "unknown")
        reason = data.get("reason", "Unknown reason")

        logger.warning(f"Action rejected by server: {action_type} - {reason}")
        
        # Rollback client-side prediction if this was a move action
        if action_type == "MOVE" and self._pending_move_rollback:
            self._rollback_move_prediction()
            self._pending_move_rollback = None
        
        self.waiting_for_server = False

        # Show error message to player
        error_message = f"Invalid Action!\n\n{action_type} was rejected:\n{reason}"

        # Create a simple error dialog
        message_box = arcade.gui.UIMessageBox(
            width=400, height=200, message_text=error_message, buttons=["OK"]
        )

        # Add to current view's UI manager if available
        if self.game_view and hasattr(self.game_view, "manager"):
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

    async def _handle_chat_message(self, message):
        """Handle CHAT message."""
        data = message.data or {}
        player_name = data.get("player_name", "Unknown")
        chat_message = data.get("message", "")
        player_id = message.player_id

        logger.info(f"Chat message from {player_name}: {chat_message}")

        # Add message to chat widget if available
        if self.game_view and self.game_view.chat_widget:
            self.game_view.chat_widget.add_message(player_name, chat_message, player_id)

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
