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
