"""
Game board and cell representation.
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
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
        occupants: List of token IDs currently occupying this cell
    """
    position: Tuple[int, int]
    cell_type: CellType = CellType.NORMAL
    occupants: List[int] = field(default_factory=list)

    @property
    def occupant(self) -> Optional[int]:
        """Backwards compatibility: return first occupant or None."""
        return self.occupants[0] if self.occupants else None

    def is_occupied(self) -> bool:
        """Check if this cell is occupied by any token."""
        return len(self.occupants) > 0

    def is_passable(self) -> bool:
        """Check if tokens can move through this cell (always True - stacking allowed)."""
        return True

    def has_enemy_tokens(self, player_id: str, tokens_dict: dict) -> bool:
        """Check if this cell has enemy tokens."""
        for token_id in self.occupants:
            if token_id in tokens_dict:
                token = tokens_dict[token_id]
                if token.player_id != player_id:
                    return True
        return False

    def get_occupant_player_id(self, tokens_dict: dict) -> Optional[str]:
        """Get the player ID of the first occupant (for backward compatibility)."""
        if self.occupants and self.occupants[0] in tokens_dict:
            return tokens_dict[self.occupants[0]].player_id
        return None

    def to_dict(self) -> dict:
        """Convert cell to dictionary for serialization."""
        return {
            "position": list(self.position),
            "cell_type": self.cell_type.name,
            "occupants": list(self.occupants),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Cell":
        """Create cell from dictionary."""
        # Handle backwards compatibility with old 'occupant' field
        if "occupants" in data:
            occupants = list(data["occupants"])
        elif "occupant" in data and data["occupant"] is not None:
            occupants = [data["occupant"]]
        else:
            occupants = []
        return cls(
            position=tuple(data["position"]),
            cell_type=CellType[data["cell_type"]],
            occupants=occupants,
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
        # Note: Starting positions no longer marked with CellType.START
        # Deployment areas are determined by get_deployable_positions() instead
        self._place_crystal()
        self._place_generators()
        self._place_mystery_squares()

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

    def add_occupant(self, position: Tuple[int, int], token_id: int) -> None:
        """
        Add a token as an occupant of a cell.

        Args:
            position: (x, y) position
            token_id: ID of token to add
        """
        cell = self.get_cell_at(position)
        if cell and token_id not in cell.occupants:
            cell.occupants.append(token_id)

    def remove_occupant(self, position: Tuple[int, int], token_id: int) -> None:
        """
        Remove a token from a cell's occupants.

        Args:
            position: (x, y) position
            token_id: ID of token to remove
        """
        cell = self.get_cell_at(position)
        if cell and token_id in cell.occupants:
            cell.occupants.remove(token_id)

    def set_occupant(self, position: Tuple[int, int], token_id: Optional[int]) -> None:
        """
        Add a token as occupant of a cell (backwards compatible).

        Args:
            position: (x, y) position
            token_id: ID of token to add, or None to do nothing
        """
        if token_id is not None:
            self.add_occupant(position, token_id)

    def clear_occupant(self, position: Tuple[int, int], token_id: Optional[int] = None) -> None:
        """
        Clear occupant(s) from a cell.

        Args:
            position: (x, y) position
            token_id: Specific token to remove, or None to clear all
        """
        cell = self.get_cell_at(position)
        if cell:
            if token_id is not None:
                self.remove_occupant(position, token_id)
            else:
                cell.occupants.clear()

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

    def get_deployable_positions(self, player_index: int) -> List[Tuple[int, int]]:
        """
        Get valid deployment positions for a player (3x3 area extending from corner into board).

        Args:
            player_index: Player index (0-3)

        Returns:
            List of (x, y) positions where player can deploy tokens
        """
        corner = self.get_starting_position(player_index)
        cx, cy = corner

        # Determine direction into the board from each corner
        # For corners at board edges, extend inward to make a 3x3 grid on the board
        positions = []

        if player_index == 0:  # Top-left (0, 0)
            # Deploy area: (0,0) to (2,2)
            for x in range(3):
                for y in range(3):
                    positions.append((x, y))
        elif player_index == 1:  # Top-right (23, 0)
            # Deploy area: (21,0) to (23,2)
            for x in range(self.width - 3, self.width):
                for y in range(3):
                    positions.append((x, y))
        elif player_index == 2:  # Bottom-left (0, 23)
            # Deploy area: (0,21) to (2,23)
            for x in range(3):
                for y in range(self.height - 3, self.height):
                    positions.append((x, y))
        elif player_index == 3:  # Bottom-right (23, 23)
            # Deploy area: (21,21) to (23,23)
            for x in range(self.width - 3, self.width):
                for y in range(self.height - 3, self.height):
                    positions.append((x, y))

        return positions

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
