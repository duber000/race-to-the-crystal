"""
Player state and management.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from shared.enums import PlayerColor


@dataclass
class Player:
    """
    Represents a player in the game.

    Attributes:
        id: Unique identifier for this player
        name: Player's display name
        color: Player's color (determines starting position)
        token_ids: List of token IDs owned by this player
        is_ready: Whether player is ready to start (lobby)
        is_active: Whether player is still in the game
        team: Optional team identifier for team games
    """
    id: str
    name: str
    color: PlayerColor
    token_ids: List[int] = field(default_factory=list)
    is_ready: bool = False
    is_active: bool = True
    team: Optional[int] = None

    @property
    def alive_token_count(self) -> int:
        """
        Get count of alive tokens.
        Note: This should be calculated by the game state,
        this is just a cached value.
        """
        return len(self.token_ids)

    def add_token(self, token_id: int) -> None:
        """
        Add a token to this player's collection.

        Args:
            token_id: ID of token to add
        """
        if token_id not in self.token_ids:
            self.token_ids.append(token_id)

    def remove_token(self, token_id: int) -> None:
        """
        Remove a token from this player's collection.

        Args:
            token_id: ID of token to remove
        """
        if token_id in self.token_ids:
            self.token_ids.remove(token_id)

    def has_token(self, token_id: int) -> bool:
        """
        Check if this player owns a token.

        Args:
            token_id: ID of token to check

        Returns:
            True if player owns this token
        """
        return token_id in self.token_ids

    def set_ready(self, ready: bool = True) -> None:
        """Set player ready status."""
        self.is_ready = ready

    def eliminate(self) -> None:
        """Eliminate this player from the game."""
        self.is_active = False

    def to_dict(self) -> dict:
        """Convert player to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color.name,
            "token_ids": self.token_ids,
            "is_ready": self.is_ready,
            "is_active": self.is_active,
            "team": self.team,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """Create player from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            color=PlayerColor[data["color"]],
            token_ids=data["token_ids"],
            is_ready=data["is_ready"],
            is_active=data["is_active"],
            team=data["team"],
        )

    def __repr__(self) -> str:
        return f"Player({self.name}, {self.color.name}, Tokens={len(self.token_ids)})"
