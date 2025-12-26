"""
Token entity representing a player's game piece.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Token:
    """
    Represents a single token (dice) on the game board.

    Attributes:
        id: Unique identifier for this token
        player_id: ID of the player who owns this token
        health: Current health value
        max_health: Maximum health value (10, 8, 6, or 4)
        position: Current (x, y) position on the board
        is_alive: Whether the token is still in play
        is_deployed: Whether the token has been deployed to the board
    """
    id: int
    player_id: str
    health: int
    max_health: int
    position: Tuple[int, int]
    is_alive: bool = True
    is_deployed: bool = False

    @property
    def movement_range(self) -> int:
        """
        Calculate movement range for this token.
        According to the rules:
        - Tokens with 6 or 4 max health move 2 spaces
        - Tokens with 8 or 10 max health move 1 space
        """
        if self.max_health in (6, 4):
            return 2
        else:  # max_health in (8, 10)
            return 1

    @property
    def attack_power(self) -> int:
        """
        Calculate attack power for this token.
        Attack power is half of current health (rounded down).
        """
        return self.health // 2

    def take_damage(self, damage: int) -> bool:
        """
        Apply damage to this token.

        Args:
            damage: Amount of damage to apply

        Returns:
            True if token is killed, False otherwise
        """
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            return True
        return False

    def heal_to_full(self) -> None:
        """Restore token to full health."""
        self.health = self.max_health

    def move_to(self, new_position: Tuple[int, int]) -> None:
        """
        Move token to a new position.

        Args:
            new_position: Target (x, y) position
        """
        self.position = new_position

    def distance_to(self, other_position: Tuple[int, int]) -> int:
        """
        Calculate Manhattan distance to another position.

        Args:
            other_position: Target (x, y) position

        Returns:
            Manhattan distance (for grid-based movement)
        """
        return abs(self.position[0] - other_position[0]) + abs(self.position[1] - other_position[1])

    def is_adjacent_to(self, other_position: Tuple[int, int]) -> bool:
        """
        Check if this token is adjacent to a position (for combat).
        Adjacent includes 8 directions (orthogonal + diagonal).

        Args:
            other_position: Target (x, y) position

        Returns:
            True if positions are adjacent
        """
        dx = abs(self.position[0] - other_position[0])
        dy = abs(self.position[1] - other_position[1])
        return dx <= 1 and dy <= 1 and (dx + dy) > 0

    def to_dict(self) -> dict:
        """Convert token to dictionary for serialization."""
        return {
            "id": self.id,
            "player_id": self.player_id,
            "health": self.health,
            "max_health": self.max_health,
            "position": list(self.position),
            "is_alive": self.is_alive,
            "is_deployed": self.is_deployed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Token":
        """Create token from dictionary."""
        return cls(
            id=data["id"],
            player_id=data["player_id"],
            health=data["health"],
            max_health=data["max_health"],
            position=tuple(data["position"]),
            is_alive=data["is_alive"],
            is_deployed=data.get("is_deployed", False),
        )

    def __repr__(self) -> str:
        status = "alive" if self.is_alive else "dead"
        return f"Token({self.id}, Player={self.player_id}, HP={self.health}/{self.max_health}, Pos={self.position}, {status})"
