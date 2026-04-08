"""
AI Client for Race to the Crystal.

An autonomous AI player that connects to the server and plays the game
using the AIObserver and AIActionExecutor.
"""

import asyncio
import argparse
import logging

from client.network_client import NetworkClient
from network.messages import MessageType, ClientType
from network.protocol import NetworkMessage
from game.game_state import GameState
from game.ai_observation import AIObserver
from game.ai_actions import MoveAction, AttackAction, DeployAction, EndTurnAction
from game.ai_strategy import AIStrategy
from shared.enums import GamePhase


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

        self.strategy = AIStrategy(strategy)
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
        logger.info(f"AI handling message: {message.type.value}")

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
            self.my_turn = current_player_id == self.player_id

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
        logger.info("Received FULL_STATE message")
        data = message.data or {}
        state_dict = data.get("game_state")

        if not state_dict:
            logger.warning("No game_state in FULL_STATE message")
            return

        # Deserialize game state
        try:
            self.current_game_state = state_dict
            game_state = GameState.from_dict(state_dict)

            # Get perspective player ID
            perspective_player_id = state_dict.get("perspective_player_id")
            logger.info(
                f"State update - perspective_player: {perspective_player_id}, current_turn: {game_state.current_turn_player_id}, game_phase: {game_state.phase.name}, turn_phase: {game_state.turn_phase.name}"
            )

            # Check if game is active (handle case where AI joins game already in progress)
            if game_state.phase == GamePhase.PLAYING:
                logger.info("Game is PLAYING - setting game_active=True")
                self.game_active = True

            # Log situation report (for debugging)
            if logger.isEnabledFor(logging.DEBUG):
                report = AIObserver.get_situation_report(
                    game_state, perspective_player_id
                )
                logger.debug(f"\n{report}")

            # Check if it's our turn
            self.my_turn = game_state.current_turn_player_id == perspective_player_id
            logger.info(f"my_turn={self.my_turn}, game_active={self.game_active}")

            if self.my_turn and self.game_active:
                # Take our turn after a small delay (to simulate thinking)
                # Use create_task to avoid blocking the message loop
                logger.info("It's our turn! Scheduling turn action...")
                asyncio.create_task(self._take_turn_async())
            else:
                if not self.my_turn:
                    logger.info("Not our turn yet")
                if not self.game_active:
                    logger.info("Game not active yet")

        except Exception as e:
            logger.error(f"Error processing game state: {e}", exc_info=True)

    async def _take_turn_async(self) -> None:
        """Async wrapper for taking turn with delay (runs in background)."""
        try:
            # Small delay to simulate thinking
            await asyncio.sleep(0.5)
            await self._take_turn()
        except Exception as e:
            logger.error(f"Error in async turn execution: {e}", exc_info=True)

    async def _take_turn(self) -> None:
        """Execute AI turn by choosing and sending an action."""
        logger.info("_take_turn() called")

        if not self.current_game_state:
            logger.warning("No game state available for turn")
            return

        try:
            # Reconstruct game state
            state_dict = self.current_game_state
            game_state = GameState.from_dict(state_dict)
            perspective_player_id = state_dict.get("perspective_player_id")

            logger.info(
                f"Taking turn for player_id: {perspective_player_id}, current_turn: {game_state.current_turn_player_id}, phase: {game_state.turn_phase.name}"
            )

            # Get available actions
            actions_data = AIObserver.list_available_actions(
                game_state, perspective_player_id
            )

            actions = actions_data.get("actions", [])
            logger.info(f"Found {len(actions)} available actions")

            if not actions:
                logger.warning(
                    f"No available actions. Phase: {actions_data.get('phase')}"
                )
                return

            # Choose an action based on strategy
            chosen = self.strategy.choose_action(
                actions, game_state, perspective_player_id
            )

            if not chosen:
                logger.warning("No action chosen")
                return

            # Convert ChosenAction to AIAction
            ai_action = self._chosen_to_ai_action(chosen)

            if not ai_action:
                logger.warning("Failed to convert chosen action")
                return

            # Send action to server
            logger.info(f"Sending action: {ai_action.action_type}")
            success = await self.send_action(ai_action)

            if not success:
                logger.error("Failed to send action")
            else:
                logger.info("Action sent successfully")

        except Exception as e:
            logger.error(f"Error taking turn: {e}", exc_info=True)

    def _chosen_to_ai_action(self, chosen):
        """
        Convert a ChosenAction to an AIAction object.

        Args:
            chosen: ChosenAction from AIStrategy

        Returns:
            AIAction object, or None
        """
        match chosen.action_type:
            case "MOVE":
                return MoveAction(
                    token_id=chosen.params["token_id"],
                    destination=tuple(chosen.params["destination"]),
                )
            case "ATTACK":
                return AttackAction(
                    attacker_id=chosen.params["attacker_id"],
                    defender_id=chosen.params["defender_id"],
                )
            case "DEPLOY":
                return DeployAction(
                    health_value=chosen.params["health_value"],
                    position=tuple(chosen.params["position"]),
                )
            case "END_TURN":
                return EndTurnAction()
            case _:
                return None


async def main():
    """Main entry point for AI client."""
    parser = argparse.ArgumentParser(description="Race to the Crystal - AI Client")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Server hostname (default: localhost)",
    )
    parser.add_argument(
        "--port", type=int, default=8888, help="Server port (default: 8888)"
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="AI player name (default: AI_Player_<random>)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["random", "aggressive", "defensive"],
        default="random",
        help="AI strategy (default: random)",
    )
    parser.add_argument(
        "--create", type=str, default=None, help="Create a new game with this name"
    )
    parser.add_argument(
        "--join", type=str, default=None, help="Join existing game by ID"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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


def run_ai_client():
    """Synchronous entry point for the AI client script."""
    asyncio.run(main())


if __name__ == "__main__":
    run_ai_client()
