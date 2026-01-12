"""
HTTP AI Client for Race to the Crystal.

AI agent that uses HTTP POST for actions and SSE (Mercure) for state updates.
This provides a simpler alternative to WebSocket for AI clients.
"""

import asyncio
import argparse
import logging
import json
import random
from typing import Optional

import httpx
from httpx_sse import aconnect_sse

from game.game_state import GameState
from game.ai_observation import AIObserver
from game.ai_actions import MoveAction, AttackAction, DeployAction, EndTurnAction
from shared.enums import GamePhase, TurnPhase


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HTTPAIPlayer:
    """
    AI player using HTTP POST + SSE architecture.

    Uses HTTP POST for sending actions and Server-Sent Events (SSE/Mercure)
    for receiving state updates. This enables stateless AI clients that work
    anywhere HTTP is supported.
    """

    def __init__(self, base_url: str, player_name: str, strategy: str = "random"):
        """
        Initialize HTTP AI player.

        Args:
            base_url: Server base URL (e.g., http://localhost:8080)
            player_name: Display name for AI
            strategy: AI strategy ("random", "aggressive", "defensive")
        """
        self.base_url = base_url.rstrip("/")
        self.player_name = player_name
        self.strategy = strategy
        self.player_id: Optional[str] = None
        self.token: Optional[str] = None
        self.game_id: Optional[str] = None
        self.sse_url: Optional[str] = None
        self.game_active = False

        logger.info(f"HTTP AI Player created: {player_name} (strategy: {strategy})")

    async def join_game(self, game_id: str) -> bool:
        """
        Join an existing game via HTTP POST.

        Args:
            game_id: Game ID to join

        Returns:
            True if successfully joined

        Raises:
            httpx.HTTPStatusError: If join fails (game not found, full, etc.)
        """
        url = f"{self.base_url}/api/game/{game_id}/join"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, json={"player_name": self.player_name}, timeout=10.0
                )
                response.raise_for_status()

                data = response.json()
                self.player_id = data["player_id"]
                self.token = data["token"]
                self.game_id = data["game_id"]
                self.sse_url = data["sse_url"]

                logger.info(
                    f"Joined game {game_id[:8]} as {self.player_name} (auto-ready)"
                )
                logger.info(f"  Player ID: {self.player_id[:8]}")
                logger.info(f"  SSE URL: {self.sse_url}")

                return True

            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to join game: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error joining game: {e}")
                raise

    async def play(self) -> None:
        """
        Main game loop using SSE for state updates.

        Connects to SSE stream and plays until game ends.
        """
        if not self.sse_url or not self.token:
            raise ValueError("Must join game before playing")

        logger.info(f"Starting game loop, connecting to SSE: {self.sse_url}")

        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with aconnect_sse(client, "GET", self.sse_url, headers=headers) as event_source:
                    logger.info("SSE connection established")

                    async for event in event_source.aiter_sse():
                        if not event.data:
                            continue

                        try:
                            data = json.loads(event.data)
                            await self._handle_sse_event(data)

                            if not self.game_active:
                                logger.info("Game ended, stopping SSE stream")
                                break

                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse SSE event: {e}")
                        except Exception as e:
                            logger.error(f"Error handling SSE event: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"SSE connection error: {e}", exc_info=True)

    async def _handle_sse_event(self, data: dict) -> None:
        """
        Handle SSE event from Mercure.

        Args:
            data: Event data from SSE stream
        """
        event_type = data.get("type")

        if event_type == "FULL_STATE":
            game_state_dict = data.get("game_state")
            if game_state_dict:
                await self._handle_state_update(game_state_dict)

        elif event_type == "GAME_WON":
            winner_name = data.get("winner_name", "Unknown")
            logger.info(f"Game over! Winner: {winner_name}")
            self.game_active = False

        else:
            logger.debug(f"Received SSE event: {event_type}")

    async def _handle_state_update(self, game_state_dict: dict) -> None:
        """
        Process game state update and take action if our turn.

        Args:
            game_state_dict: Serialized game state
        """
        try:
            game_state = GameState.from_dict(game_state_dict)
            perspective_player_id = game_state_dict.get("perspective_player_id")

            # Check if game is active
            if game_state.phase == GamePhase.PLAYING:
                if not self.game_active:
                    logger.info("Game started - activating AI")
                self.game_active = True
            elif game_state.phase == GamePhase.ENDED:
                self.game_active = False
                return

            # Check if it's our turn
            is_our_turn = game_state.current_turn_player_id == perspective_player_id

            if not is_our_turn:
                logger.debug("Not our turn, waiting...")
                return

            logger.info(
                f"Our turn! Phase: {game_state.turn_phase.name}, "
                f"Turn: {game_state.turn_number}"
            )

            # Get available actions
            actions = AIObserver.list_available_actions(game_state, perspective_player_id)

            if not actions.get("actions"):
                logger.warning("No actions available")
                return

            # Choose and execute action
            action = self._choose_action(actions["actions"], game_state, perspective_player_id)
            if action:
                await self._send_action(action)
            else:
                logger.warning("No action chosen")

        except Exception as e:
            logger.error(f"Error processing state update: {e}", exc_info=True)

    def _choose_action(
        self, available_actions: list, game_state: GameState, player_id: str
    ) -> Optional[dict]:
        """
        Choose an action based on AI strategy.

        Args:
            available_actions: List of available action dicts
            game_state: Current game state
            player_id: Our player ID

        Returns:
            Action dict to execute, or None
        """
        if not available_actions:
            return None

        if self.strategy == "random":
            return random.choice(available_actions)

        elif self.strategy == "aggressive":
            # Prefer attacks, then moves, then deploy, then end turn
            attacks = [a for a in available_actions if a["type"] == "ATTACK"]
            if attacks:
                # Choose attack that deals most damage or kills
                attacks.sort(key=lambda a: (-int(a.get("will_kill", False)), -a.get("damage", 0)))
                return attacks[0]

            moves = [a for a in available_actions if a["type"] == "MOVE"]
            if moves:
                return random.choice(moves)

            deploys = [a for a in available_actions if a["type"] == "DEPLOY"]
            if deploys:
                # Prefer highest health
                deploys.sort(key=lambda a: -a.get("health_value", 0))
                return deploys[0]

            return available_actions[0]

        elif self.strategy == "defensive":
            # Prefer deploy, then end turn, then move, then attack
            deploys = [a for a in available_actions if a["type"] == "DEPLOY"]
            if deploys:
                return random.choice(deploys)

            end_turns = [a for a in available_actions if a["type"] == "END_TURN"]
            if end_turns:
                return end_turns[0]

            moves = [a for a in available_actions if a["type"] == "MOVE"]
            if moves:
                return random.choice(moves)

            return available_actions[0]

        else:
            # Unknown strategy, use random
            return random.choice(available_actions)

    async def _send_action(self, action: dict) -> None:
        """
        Send action to server via HTTP POST.

        Args:
            action: Action dict from AIObserver
        """
        if not self.token or not self.game_id:
            logger.error("Cannot send action: not authenticated")
            return

        url = f"{self.base_url}/api/game/{self.game_id}/action"
        headers = {"Authorization": f"Bearer {self.token}"}

        # Convert action format to match API expectations
        action_data = {
            "type": action["type"],
        }

        # Add type-specific fields
        if action["type"] == "MOVE":
            action_data["token_id"] = action["token_id"]
            action_data["destination"] = action["valid_destinations"][0]  # Pick first valid destination

        elif action["type"] == "ATTACK":
            action_data["attacker_id"] = action["attacker_id"]
            action_data["defender_id"] = action["defender_id"]

        elif action["type"] == "DEPLOY":
            action_data["health_value"] = action["health_value"]
            action_data["position"] = action["positions"][0]  # Pick first valid position

        elif action["type"] == "END_TURN":
            pass  # No additional fields needed

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=action_data, headers=headers)
                response.raise_for_status()

                result = response.json()
                if result.get("success"):
                    logger.info(f"Action executed: {action['type']}")
                else:
                    logger.warning(f"Action failed: {result.get('message')}")

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Action rejected: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error sending action: {e}")


async def run_http_ai_client():
    """Main entry point for HTTP AI client."""
    parser = argparse.ArgumentParser(
        description="HTTP AI Client for Race to the Crystal"
    )
    parser.add_argument(
        "--join",
        type=str,
        required=True,
        help="Game ID to join (get from lobby)",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="HTTP_Bot",
        help="Player name (default: HTTP_Bot)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8080",
        help="Server base URL (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["random", "aggressive", "defensive"],
        default="random",
        help="AI strategy (default: random)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create AI player
    ai = HTTPAIPlayer(args.base_url, args.name, args.strategy)

    try:
        # Join game
        await ai.join_game(args.join)

        # Play game
        await ai.play()

        logger.info("AI client finished")

    except KeyboardInterrupt:
        logger.info("AI client stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


def main():
    """Synchronous entry point."""
    asyncio.run(run_http_ai_client())


if __name__ == "__main__":
    main()
