"""
Mercure publisher for real-time game state updates in unified server.

Mercure is a protocol for pushing data updates to web clients using Server-Sent Events (SSE).
This module handles publishing game state changes to a Mercure hub.
"""

import os
import httpx
import logging
from typing import Any, Dict
from dataclasses import dataclass
import json


logger = logging.getLogger(__name__)


@dataclass
class MercureConfig:
    """Configuration for Mercure hub connection."""

    hub_url: str
    publisher_jwt: str
    topic_prefix: str = "https://api.game.com/game"

    @classmethod
    def from_env(cls) -> "MercureConfig":
        """
        Load Mercure configuration from environment variables.

        Required environment variables:
        - MERCURE_HUB_URL: URL of the Mercure hub (e.g., https://mercure.example.com/.well-known/mercure)
        - MERCURE_PUBLISHER_JWT: JWT token for publisher authentication
        - MERCURE_TOPIC_PREFIX: (optional) Prefix for topic URLs

        Returns:
            MercureConfig instance
        """
        hub_url = os.getenv(
            "MERCURE_HUB_URL", "http://localhost:3000/.well-known/mercure"
        )
        publisher_jwt = os.getenv("MERCURE_PUBLISHER_JWT", "")
        topic_prefix = os.getenv(
            "MERCURE_TOPIC_PREFIX", "https://api.game.com/game"
        )

        if not publisher_jwt:
            logger.warning(
                "MERCURE_PUBLISHER_JWT not set - Mercure publishing disabled"
            )

        return cls(
            hub_url=hub_url, publisher_jwt=publisher_jwt, topic_prefix=topic_prefix
        )


class MercurePublisher:
    """
    Publisher for sending game state updates to Mercure hub.

    This enables real-time updates to all web clients subscribed to a game.
    """

    def __init__(self, config: MercureConfig):
        """
        Initialize Mercure publisher.

        Args:
            config: Mercure configuration
        """
        self.config = config
        self.client: httpx.AsyncClient | None = None
        self.enabled = bool(config.publisher_jwt)
        logger.info(
            f"Mercure publisher initialized (enabled={self.enabled}, hub={config.hub_url})"
        )

    async def ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is created."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=5.0)
        return self.client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def publish_game_state(
        self, game_id: str, state_data: Dict[str, Any], private: bool = False
    ) -> bool:
        """
        Publish game state update to Mercure hub.

        Args:
            game_id: Unique game identifier
            state_data: Game state data to publish
            private: If True, only subscribers with valid JWT can receive

        Returns:
            True if publish succeeded, False otherwise
        """
        if not self.enabled:
            logger.debug("Mercure disabled, skipping publish")
            return False

        topic = f"{self.config.topic_prefix}/{game_id}"

        try:
            client = await self.ensure_client()

            # Prepare form data for Mercure
            # Mercure expects application/x-www-form-urlencoded
            form_data = {
                "topic": topic,
                "data": json.dumps(state_data),  # Mercure expects string data
            }

            if private:
                form_data["private"] = "on"

            # Send POST request to Mercure hub
            response = await client.post(
                self.config.hub_url,
                data=form_data,
                headers={
                    "Authorization": f"Bearer {self.config.publisher_jwt}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            if response.status_code == 200:
                logger.debug(f"Published update to Mercure for game {game_id[:8]}")
                return True
            else:
                logger.error(
                    f"Mercure publish failed: {response.status_code} - {response.text}"
                )
                return False

        except httpx.RequestError as e:
            logger.warning(f"Failed to publish to Mercure hub: {e}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error publishing to Mercure: {e}", exc_info=True
            )
            return False

    async def publish_action_event(
        self, game_id: str, action_type: str, action_data: Dict[str, Any]
    ) -> bool:
        """
        Publish a game action event to Mercure.

        Args:
            game_id: Unique game identifier
            action_type: Type of action (move, attack, deploy, etc.)
            action_data: Action-specific data

        Returns:
            True if publish succeeded, False otherwise
        """
        event_data = {
            "type": "action",
            "action_type": action_type,
            "data": action_data,
        }

        return await self.publish_game_state(game_id, event_data)

    # Individual event publishing methods for SSE-primary mode
    # These enable fine-grained event-driven animations on web clients

    async def publish_turn_change(
        self, game_id: str, current_player_id: str, turn_number: int, turn_phase: str
    ) -> bool:
        """Publish turn change event."""
        event_data = {
            "type": "TURN_CHANGE",
            "current_player_id": current_player_id,
            "turn_number": turn_number,
            "turn_phase": turn_phase,
        }
        return await self.publish_game_state(game_id, event_data)

    async def publish_token_moved(
        self,
        game_id: str,
        token_id: int,
        from_position: tuple[int, int],
        to_position: tuple[int, int],
        player_id: str,
    ) -> bool:
        """Publish token movement event for animations."""
        event_data = {
            "type": "TOKEN_MOVED",
            "token_id": token_id,
            "from": from_position,
            "to": to_position,
            "player_id": player_id,
        }
        return await self.publish_game_state(game_id, event_data)

    async def publish_combat_result(
        self,
        game_id: str,
        attacker_id: int,
        defender_id: int,
        damage: int,
        defender_destroyed: bool,
    ) -> bool:
        """Publish combat result event for animations."""
        event_data = {
            "type": "COMBAT_RESULT",
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "damage": damage,
            "defender_destroyed": defender_destroyed,
        }
        return await self.publish_game_state(game_id, event_data)

    async def publish_generator_update(
        self,
        game_id: str,
        generator_position: tuple[int, int],
        capturing_player_id: str | None,
        turns_held: int,
        is_disabled: bool,
    ) -> bool:
        """Publish generator capture status update."""
        event_data = {
            "type": "GENERATOR_UPDATE",
            "position": generator_position,
            "capturing_player_id": capturing_player_id,
            "turns_held": turns_held,
            "is_disabled": is_disabled,
        }
        return await self.publish_game_state(game_id, event_data)

    async def publish_crystal_update(
        self,
        game_id: str,
        crystal_position: tuple[int, int],
        occupying_player_id: str | None,
        turns_held: int,
        tokens_required: int,
    ) -> bool:
        """Publish crystal occupation status update."""
        event_data = {
            "type": "CRYSTAL_UPDATE",
            "position": crystal_position,
            "occupying_player_id": occupying_player_id,
            "turns_held": turns_held,
            "tokens_required": tokens_required,
        }
        return await self.publish_game_state(game_id, event_data)

    async def publish_mystery_event(
        self, game_id: str, token_id: int, event_type: str, details: Dict[str, Any]
    ) -> bool:
        """Publish mystery square event (heal or teleport)."""
        event_data = {
            "type": "MYSTERY_EVENT",
            "token_id": token_id,
            "event_type": event_type,
            "details": details,
        }
        return await self.publish_game_state(game_id, event_data)

    async def publish_token_deployed(
        self, game_id: str, token_id: int, position: tuple[int, int], player_id: str
    ) -> bool:
        """Publish token deployment event."""
        event_data = {
            "type": "TOKEN_DEPLOYED",
            "token_id": token_id,
            "position": position,
            "player_id": player_id,
        }
        return await self.publish_game_state(game_id, event_data)

    async def publish_game_won(self, game_id: str, winner_id: str) -> bool:
        """Publish game victory event."""
        event_data = {
            "type": "GAME_WON",
            "winner_id": winner_id,
        }
        return await self.publish_game_state(game_id, event_data)
