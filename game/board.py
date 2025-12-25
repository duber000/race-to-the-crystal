"""
Game board and cell representation.
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
import random

from shared.enums import CellType
from shared.constants import (
    BOARD_WIDTH,
    BOARD_HEIGHT,
    MYSTERY_SQUARES_PER_QUADRANT,
)


@dataclass
class Cell:
    """
    Represents a single cell on the game board.

    Attributes:
        position: (x, y) position of this cell
        cell_type: Type of cell (normal, generator, crystal, etc.)
        occupant: Token ID currently occupying this cell (None if empty)
    """
    position: Tuple[int, int]
    cell_type: CellType = CellType.NORMAL
    occupant: Optional[int] = None

    def is_occupied(self) -> bool:
        """Check if this cell is occupied by a token."""
        return self.occupant is not None

    def is_passable(self) -> bool:
        """Check if tokens can move through this cell."""
        return not self.is_occupied()

    def to_dict(self) -> dict:
        """Convert cell to dictionary for serialization."""
        return {
            "position": list(self.position),
            "cell_type": self.cell_type.name,
            "occupant": self.occupant,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Cell":
        """Create cell from dictionary."""
        return cls(
            position=tuple(data["position"]),
            cell_type=CellType[data["cell_type"]],
            occupant=data["occupant"],
        )


@dataclass
class Board:
    """
    Represents the game board grid.

    Attributes:
        width: Width of the board
        height: Height of the board
        grid: 2D array of cells
    """
    width: int = BOARD_WIDTH
    height: int = BOARD_HEIGHT
    grid: List[List[Cell]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the board grid if not provided."""
        if not self.grid:
            self._initialize_grid()

    def _initialize_grid(self) -> None:
        """Create the initial grid with all cells."""
        self.grid = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                row.append(Cell(position=(x, y)))
            self.grid.append(row)

        # Place special cells
        self._place_starting_positions()
        self._place_crystal()
        self._place_generators()
        self._place_mystery_squares()

    def _place_starting_positions(self) -> None:
        """Place starting positions in the four corners."""
        corners = [
            (0, 0),                          # Top-left (Player 1 - Cyan)
            (self.width - 1, 0),             # Top-right (Player 2 - Magenta)
            (0, self.height - 1),            # Bottom-left (Player 3 - Yellow)
            (self.width - 1, self.height - 1)  # Bottom-right (Player 4 - Green)
        ]
        for x, y in corners:
            self.grid[y][x].cell_type = CellType.START

    def _place_crystal(self) -> None:
        """Place the power crystal in the center of the board."""
        center_x = self.width // 2
        center_y = self.height // 2
        self.grid[center_y][center_x].cell_type = CellType.CRYSTAL

    def _place_generators(self) -> None:
        """Place 4 generators, one in each quadrant."""
        # Quadrant centers (offset from actual center)
        mid_x = self.width // 2
        mid_y = self.height // 2
        quarter_x = self.width // 4
        quarter_y = self.height // 4

        generators = [
            (quarter_x, quarter_y),                      # Top-left quadrant
            (mid_x + quarter_x, quarter_y),              # Top-right quadrant
            (quarter_x, mid_y + quarter_y),              # Bottom-left quadrant
            (mid_x + quarter_x, mid_y + quarter_y),      # Bottom-right quadrant
        ]

        for x, y in generators:
            self.grid[y][x].cell_type = CellType.GENERATOR

    def _place_mystery_squares(self) -> None:
        """Place mystery squares randomly in each quadrant."""
        # Skip if board is too small for mystery squares
        if self.width < 10 or self.height < 10:
            return

        mid_x = self.width // 2
        mid_y = self.height // 2

        # Define quadrants (excluding edges to avoid overlap with special cells)
        quadrants = [
            (2, mid_x - 2, 2, mid_y - 2),                    # Top-left
            (mid_x + 2, self.width - 2, 2, mid_y - 2),       # Top-right
            (2, mid_x - 2, mid_y + 2, self.height - 2),      # Bottom-left
            (mid_x + 2, self.width - 2, mid_y + 2, self.height - 2),  # Bottom-right
        ]

        for x_min, x_max, y_min, y_max in quadrants:
            # Skip quadrant if range is invalid
            if x_max < x_min or y_max < y_min:
                continue

            placed = 0
            attempts = 0
            max_attempts = 100

            while placed < MYSTERY_SQUARES_PER_QUADRANT and attempts < max_attempts:
                x = random.randint(x_min, x_max)
                y = random.randint(y_min, y_max)

                cell = self.grid[y][x]
                # Only place on normal cells
                if cell.cell_type == CellType.NORMAL:
                    cell.cell_type = CellType.MYSTERY
                    placed += 1

                attempts += 1

    def get_cell(self, x: int, y: int) -> Optional[Cell]:
        """
        Get cell at position (x, y).

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Cell at position, or None if out of bounds
        """
        if not self.is_valid_position(x, y):
            return None
        return self.grid[y][x]

    def get_cell_at(self, position: Tuple[int, int]) -> Optional[Cell]:
        """
        Get cell at position.

        Args:
            position: (x, y) tuple

        Returns:
            Cell at position, or None if out of bounds
        """
        return self.get_cell(position[0], position[1])

    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is within board bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def set_occupant(self, position: Tuple[int, int], token_id: Optional[int]) -> None:
        """
        Set the occupant of a cell.

        Args:
            position: (x, y) position
            token_id: ID of token occupying the cell, or None to clear
        """
        cell = self.get_cell_at(position)
        if cell:
            cell.occupant = token_id

    def clear_occupant(self, position: Tuple[int, int]) -> None:
        """Clear the occupant of a cell."""
        self.set_occupant(position, None)

    def get_starting_position(self, player_index: int) -> Tuple[int, int]:
        """
        Get the starting corner position for a player.

        Args:
            player_index: Player index (0-3)

        Returns:
            (x, y) starting position
        """
        corners = [
            (0, 0),                          # Player 0 - Top-left
            (self.width - 1, 0),             # Player 1 - Top-right
            (0, self.height - 1),            # Player 2 - Bottom-left
            (self.width - 1, self.height - 1)  # Player 3 - Bottom-right
        ]
        return corners[player_index % 4]

    def get_crystal_position(self) -> Tuple[int, int]:
        """Get the position of the power crystal."""
        return (self.width // 2, self.height // 2)

    def get_generator_positions(self) -> List[Tuple[int, int]]:
        """Get positions of all generators."""
        generators = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x].cell_type == CellType.GENERATOR:
                    generators.append((x, y))
        return generators

    def get_mystery_positions(self) -> List[Tuple[int, int]]:
        """Get positions of all mystery squares."""
        mystery = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x].cell_type == CellType.MYSTERY:
                    mystery.append((x, y))
        return mystery

    def to_dict(self) -> dict:
        """Convert board to dictionary for serialization."""
        return {
            "width": self.width,
            "height": self.height,
            "grid": [[cell.to_dict() for cell in row] for row in self.grid],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Board":
        """Create board from dictionary."""
        board = cls(width=data["width"], height=data["height"])
        board.grid = [
            [Cell.from_dict(cell_data) for cell_data in row]
            for row in data["grid"]
        ]
        return board

    def __repr__(self) -> str:
        return f"Board({self.width}x{self.height})"
