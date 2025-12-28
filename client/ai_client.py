"""
AI Client for Race to the Crystal.

An autonomous AI player that connects to the server and plays the game
using the AIObserver and AIActionExecutor.
"""
import asyncio
import argparse
import logging
import random
from typing import Optional

from client.network_client import NetworkClient
from network.messages import MessageType, ClientType
from network.protocol import NetworkMessage
from game.game_state import GameState
from game.ai_observation import AIObserver
from game.ai_actions import MoveAction, AttackAction, DeployAction, EndTurnAction


logger = logging.getLogger(__name__)


class AIPlayer(NetworkClient):
    """
    AI player that connects to server and plays autonomously.

    Uses AIObserver to understand game state and makes decisions
    based on simple heuristics.
    """

    def __init__(self, player_name: str, strategy: str = "random"):
        """
        Initialize AI player.

        Args:
            player_name: Display name for AI
            strategy: AI strategy ("random", "aggressive", "defensive")
        """
        super().__init__(player_name, ClientType.AI)

        self.strategy = strategy
        self.game_active = False
        self.my_turn = False

        # Set message handler
        self.on_message = self._handle_game_message

        logger.info(f"AI Player created: {player_name} (strategy: {strategy})")

    async def _handle_game_message(self, message: NetworkMessage) -> None:
        """
        Handle messages from server.

        Args:
            message: Received message
        """
        if message.type == MessageType.FULL_STATE:
            # Game state update
            await self._handle_state_update(message)

        elif message.type == MessageType.START_GAME:
            # Game started
            logger.info("Game started!")
            self.game_active = True

        elif message.type == MessageType.TURN_CHANGE:
            # Turn changed
            data = message.data or {}
            current_player_id = data.get("current_player_id")
            self.my_turn = (current_player_id == self.player_id)

            if self.my_turn:
                logger.info("My turn!")
                await self._take_turn()

        elif message.type == MessageType.GAME_WON:
            # Game ended
            data = message.data or {}
            winner_name = data.get("winner_name", "Unknown")
            logger.info(f"Game over! Winner: {winner_name}")
            self.game_active = False

        elif message.type == MessageType.INVALID_ACTION:
            # Action was invalid
            data = message.data or {}
            reason = data.get("reason", "Unknown")
            logger.warning(f"Invalid action: {reason}")

        elif message.type == MessageType.ERROR:
            # Server error
            data = message.data or {}
            error = data.get("error", "Unknown error")
            logger.error(f"Server error: {error}")

    async def _handle_state_update(self, message: NetworkMessage) -> None:
        """
        Handle full state update from server.

        Args:
            message: FULL_STATE message
        """
        data = message.data or {}
        state_dict = data.get("game_state")

        if not state_dict:
            return

        # Deserialize game state
        try:
            self.current_game_state = state_dict
            game_state = GameState.from_dict(state_dict)

            # Get perspective player ID
            perspective_player_id = state_dict.get("perspective_player_id")

            # Log situation report (for debugging)
            if logger.isEnabledFor(logging.DEBUG):
                report = AIObserver.get_situation_report(game_state, perspective_player_id)
                logger.debug(f"\n{report}")

            # Check if it's our turn
            self.my_turn = (game_state.current_turn_player_id == perspective_player_id)

            if self.my_turn and self.game_active:
                # Take our turn after a small delay (to simulate thinking)
                await asyncio.sleep(0.5)
                await self._take_turn()

        except Exception as e:
            logger.error(f"Error processing game state: {e}", exc_info=True)

    async def _take_turn(self) -> None:
        """Execute AI turn by choosing and sending an action."""
        if not self.current_game_state:
            logger.warning("No game state available for turn")
            return

        try:
            # Reconstruct game state
            state_dict = self.current_game_state
            game_state = GameState.from_dict(state_dict)
            perspective_player_id = state_dict.get("perspective_player_id")

            # Get available actions
            actions_data = AIObserver.list_available_actions(
                game_state,
                perspective_player_id
            )

            actions = actions_data.get("actions", [])

            if not actions:
                logger.warning("No available actions")
                return

            # Choose an action based on strategy
            chosen_action = self._choose_action(actions, game_state, perspective_player_id)

            if not chosen_action:
                logger.warning("No action chosen")
                return

            # Send action to server
            logger.info(f"Sending action: {chosen_action.action_type}")
            success = await self.send_action(chosen_action)

            if not success:
                logger.error("Failed to send action")

        except Exception as e:
            logger.error(f"Error taking turn: {e}", exc_info=True)

    def _choose_action(self, actions, game_state, player_id):
        """
        Choose an action based on AI strategy.

        Args:
            actions: List of available action dictionaries
            game_state: Current GameState
            player_id: AI's player ID

        Returns:
            Chosen AIAction
        """
        if self.strategy == "random":
            return self._choose_random_action(actions)
        elif self.strategy == "aggressive":
            return self._choose_aggressive_action(actions)
        elif self.strategy == "defensive":
            return self._choose_defensive_action(actions)
        else:
            return self._choose_random_action(actions)

    def _choose_random_action(self, actions):
        """Choose a random action from available actions."""
        if not actions:
            return None

        action_dict = random.choice(actions)
        return self._action_dict_to_ai_action(action_dict)

    def _choose_aggressive_action(self, actions):
        """Choose aggressive action (prioritize attacks)."""
        # Prioritize attacks
        attacks = [a for a in actions if a["type"] == "ATTACK"]
        if attacks:
            # Choose attack that will kill if possible
            killing_attacks = [a for a in attacks if a.get("will_kill", False)]
            if killing_attacks:
                action_dict = random.choice(killing_attacks)
            else:
                action_dict = random.choice(attacks)
            return self._action_dict_to_ai_action(action_dict)

        # Otherwise prioritize moves toward center
        moves = [a for a in actions if a["type"] == "MOVE"]
        if moves:
            # Simple heuristic: move toward center (12, 12)
            action_dict = random.choice(moves)
            return self._action_dict_to_ai_action(action_dict)

        # Deploy or end turn
        return self._choose_random_action(actions)

    def _choose_defensive_action(self, actions):
        """Choose defensive action (prioritize safe moves)."""
        # Prioritize deployment over attacks
        deploys = [a for a in actions if a["type"] == "DEPLOY"]
        if deploys and random.random() > 0.5:
            action_dict = random.choice(deploys)
            return self._action_dict_to_ai_action(action_dict)

        # Then attacks
        attacks = [a for a in actions if a["type"] == "ATTACK"]
        if attacks and random.random() > 0.3:
            action_dict = random.choice(attacks)
            return self._action_dict_to_ai_action(action_dict)

        # Otherwise random action
        return self._choose_random_action(actions)

    def _action_dict_to_ai_action(self, action_dict):
        """
        Convert action dictionary to AIAction object.

        Args:
            action_dict: Action dictionary from AIObserver

        Returns:
            AIAction object
        """
        action_type = action_dict["type"]

        if action_type == "MOVE":
            return MoveAction(
                token_id=action_dict["token_id"],
                destination=tuple(action_dict["valid_destinations"][0])  # Choose first valid dest
            )

        elif action_type == "ATTACK":
            return AttackAction(
                attacker_id=action_dict["attacker_id"],
                defender_id=action_dict["defender_id"]
            )

        elif action_type == "DEPLOY":
            positions = action_dict["positions"]
            return DeployAction(
                health_value=action_dict["health_value"],
                position=tuple(positions[0])  # Choose first valid position
            )

        elif action_type == "END_TURN":
            return EndTurnAction()

        return None


async def main():
    """Main entry point for AI client."""
    parser = argparse.ArgumentParser(
        description="Race to the Crystal - AI Client"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Server hostname (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Server port (default: 8888)"
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="AI player name (default: AI_Player_<random>)"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["random", "aggressive", "defensive"],
        default="random",
        help="AI strategy (default: random)"
    )
    parser.add_argument(
        "--create",
        type=str,
        default=None,
        help="Create a new game with this name"
    )
    parser.add_argument(
        "--join",
        type=str,
        default=None,
        help="Join existing game by ID"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Generate player name if not provided
    if not args.name:
        import random
        args.name = f"AI_Player_{random.randint(1000, 9999)}"

    # Create AI player
    ai_player = AIPlayer(args.name, args.strategy)

    # Connect to server
    logger.info(f"Connecting to {args.host}:{args.port}...")
    connected = await ai_player.connect(args.host, args.port)

    if not connected:
        logger.error("Failed to connect to server")
        return

    # Create or join game
    if args.create:
        logger.info(f"Creating game: {args.create}")
        await ai_player.create_game(args.create)
        await asyncio.sleep(0.5)
        # Auto-ready in created game
        await ai_player.set_ready(True)
        logger.info("Ready and waiting for other players...")

    elif args.join:
        logger.info(f"Joining game: {args.join}")
        await ai_player.join_game(args.join)
        await asyncio.sleep(0.5)
        # Auto-ready
        await ai_player.set_ready(True)
        logger.info("Ready and waiting for game to start...")

    else:
        logger.info("Listing available games...")
        await ai_player.list_games()
        logger.info("Use --create <name> to create a game or --join <id> to join")

    # Keep client running
    try:
        while ai_player.is_connected():
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down AI client...")

    await ai_player.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
