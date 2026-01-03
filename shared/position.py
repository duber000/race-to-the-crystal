"""
Position value object for representing board and screen coordinates.

This module eliminates the primitive obsession code smell by replacing
(x, y) tuples with a type-safe Position class.
"""

from dataclasses import dataclass
from typing import Tuple, Iterator
import math


@dataclass(frozen=True)
class Position:
    """
    Immutable position value object representing a 2D coordinate.

    This replaces the common (x, y) tuple pattern throughout the codebase
    with a more type-safe and feature-rich alternative.

    Attributes:
        x: X coordinate
        y: Y coordinate
    """
    x: int
    y: int

    def __iter__(self) -> Iterator[int]:
        """Allow unpacking: x, y = position"""
        yield self.x
        yield self.y

    def to_tuple(self) -> Tuple[int, int]:
        """
        Convert to legacy tuple format for backwards compatibility.

        Returns:
            (x, y) tuple
        """
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, coords: Tuple[int, int]) -> "Position":
        """
        Create Position from legacy tuple format.

        Args:
            coords: (x, y) tuple

        Returns:
            Position instance
        """
        return cls(coords[0], coords[1])

    def is_valid(self, width: int, height: int) -> bool:
        """
        Check if position is within bounds.

        Args:
            width: Maximum width (exclusive)
            height: Maximum height (exclusive)

        Returns:
            True if position is within [0, width) x [0, height)
        """
        return 0 <= self.x < width and 0 <= self.y < height

    def distance_to(self, other: "Position") -> float:
        """
        Calculate Euclidean distance to another position.

        Args:
            other: Target position

        Returns:
            Euclidean distance as float
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def manhattan_distance_to(self, other: "Position") -> int:
        """
        Calculate Manhattan distance to another position.

        Args:
            other: Target position

        Returns:
            Manhattan distance (sum of absolute differences)
        """
        return abs(self.x - other.x) + abs(self.y - other.y)

    def is_adjacent_to(self, other: "Position") -> bool:
        """
        Check if this position is adjacent to another (including diagonals).

        Args:
            other: Position to check

        Returns:
            True if positions are adjacent (distance <= 1)
        """
        dx = abs(self.x - other.x)
        dy = abs(self.y - other.y)
        return dx <= 1 and dy <= 1 and (dx + dy) > 0

    def is_orthogonally_adjacent_to(self, other: "Position") -> bool:
        """
        Check if this position is orthogonally adjacent (not diagonals).

        Args:
            other: Position to check

        Returns:
            True if positions share an edge (not diagonal)
        """
        dx = abs(self.x - other.x)
        dy = abs(self.y - other.y)
        return (dx == 1 and dy == 0) or (dx == 0 and dy == 1)

    def get_neighbors(self, include_diagonals: bool = True) -> list["Position"]:
        """
        Get all neighboring positions.

        Args:
            include_diagonals: Whether to include diagonal neighbors

        Returns:
            List of neighbor positions (not validated for bounds)
        """
        neighbors = []

        if include_diagonals:
            # All 8 neighbors
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    neighbors.append(Position(self.x + dx, self.y + dy))
        else:
            # Only 4 orthogonal neighbors
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                neighbors.append(Position(self.x + dx, self.y + dy))

        return neighbors

    def offset(self, dx: int, dy: int) -> "Position":
        """
        Create a new position offset from this one.

        Args:
            dx: X offset
            dy: Y offset

        Returns:
            New Position instance
        """
        return Position(self.x + dx, self.y + dy)

    def __add__(self, other: "Position") -> "Position":
        """Add two positions (vector addition)."""
        return Position(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Position") -> "Position":
        """Subtract two positions (vector subtraction)."""
        return Position(self.x - other.x, self.y - other.y)

    def __repr__(self) -> str:
        """String representation."""
        return f"Position({self.x}, {self.y})"

    def __str__(self) -> str:
        """Human-readable string."""
        return f"({self.x}, {self.y})"
