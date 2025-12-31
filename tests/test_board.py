"""
Unit tests for Board and Cell classes.
"""
import pytest
from game.board import Board, Cell
from shared.enums import CellType
from shared.constants import BOARD_WIDTH, BOARD_HEIGHT


class TestCell:
    """Test cases for Cell class."""

    def test_cell_creation(self):
        """Test creating a cell."""
        cell = Cell(position=(3, 4), cell_type=CellType.NORMAL, occupants=[])
        assert cell.position == (3, 4)
        assert cell.cell_type == CellType.NORMAL
        assert cell.occupant is None
        assert cell.occupants == []

    def test_cell_is_occupied(self):
        """Test checking if cell is occupied."""
        empty_cell = Cell(position=(0, 0), occupants=[])
        occupied_cell = Cell(position=(1, 1), occupants=[42])

        assert empty_cell.is_occupied() is False
        assert occupied_cell.is_occupied() is True

    def test_cell_is_passable(self):
        """Test checking if cell is passable (always True now - stacking allowed)."""
        empty_cell = Cell(position=(0, 0), occupants=[])
        occupied_cell = Cell(position=(1, 1), occupants=[42])

        # Cells are always passable now - enemy checking is done at movement level
        assert empty_cell.is_passable() is True
        assert occupied_cell.is_passable() is True

    def test_cell_multiple_occupants(self):
        """Test cell with multiple occupants (stacking)."""
        cell = Cell(position=(5, 5), occupants=[1, 2, 3])
        assert cell.is_occupied() is True
        assert cell.occupant == 1  # First occupant for backwards compat
        assert len(cell.occupants) == 3

    def test_cell_serialization(self):
        """Test cell serialization."""
        cell = Cell(position=(5, 6), cell_type=CellType.MYSTERY, occupants=[99])
        data = cell.to_dict()

        assert data["position"] == [5, 6]
        assert data["cell_type"] == "MYSTERY"
        assert data["occupants"] == [99]

        restored = Cell.from_dict(data)
        assert restored.position == (5, 6)
        assert restored.cell_type == CellType.MYSTERY
        assert restored.occupant == 99
        assert restored.occupants == [99]

    def test_cell_serialization_backwards_compat(self):
        """Test cell deserialization with old 'occupant' format."""
        # Old format with single occupant
        old_data = {
            "position": [5, 6],
            "cell_type": "MYSTERY",
            "occupant": 99
        }
        restored = Cell.from_dict(old_data)
        assert restored.occupants == [99]
        assert restored.occupant == 99


class TestBoard:
    """Test cases for Board class."""

    def test_board_creation(self):
        """Test creating a board."""
        board = Board()
        assert board.width == BOARD_WIDTH
        assert board.height == BOARD_HEIGHT
        assert len(board.grid) == BOARD_HEIGHT
        assert len(board.grid[0]) == BOARD_WIDTH

    def test_board_custom_size(self):
        """Test creating board with custom size."""
        board = Board(width=10, height=8)
        assert board.width == 10
        assert board.height == 8
        assert len(board.grid) == 8
        assert len(board.grid[0]) == 10

    def test_starting_positions(self):
        """Test that starting positions are placed in corners."""
        board = Board()

        # Check corners
        top_left = board.get_cell(0, 0)
        top_right = board.get_cell(board.width - 1, 0)
        bottom_left = board.get_cell(0, board.height - 1)
        bottom_right = board.get_cell(board.width - 1, board.height - 1)

        assert top_left.cell_type == CellType.START
        assert top_right.cell_type == CellType.START
        assert bottom_left.cell_type == CellType.START
        assert bottom_right.cell_type == CellType.START

    def test_crystal_position(self):
        """Test that crystal is placed in center."""
        board = Board()
        center_x = board.width // 2
        center_y = board.height // 2

        crystal_cell = board.get_cell(center_x, center_y)
        assert crystal_cell.cell_type == CellType.CRYSTAL

    def test_generators_count(self):
        """Test that 4 generators are placed."""
        board = Board()
        generator_positions = board.get_generator_positions()
        assert len(generator_positions) == 4

    def test_generators_in_quadrants(self):
        """Test that generators are in different quadrants."""
        board = Board()
        mid_x = board.width // 2
        mid_y = board.height // 2

        generator_positions = board.get_generator_positions()

        # Count generators in each quadrant
        quadrants = {
            "top_left": 0,
            "top_right": 0,
            "bottom_left": 0,
            "bottom_right": 0
        }

        for x, y in generator_positions:
            if x < mid_x and y < mid_y:
                quadrants["top_left"] += 1
            elif x >= mid_x and y < mid_y:
                quadrants["top_right"] += 1
            elif x < mid_x and y >= mid_y:
                quadrants["bottom_left"] += 1
            else:
                quadrants["bottom_right"] += 1

        # Each quadrant should have exactly 1 generator
        assert quadrants["top_left"] == 1
        assert quadrants["top_right"] == 1
        assert quadrants["bottom_left"] == 1
        assert quadrants["bottom_right"] == 1

    def test_mystery_squares_exist(self):
        """Test that mystery squares are placed."""
        board = Board()
        mystery_positions = board.get_mystery_positions()
        assert len(mystery_positions) > 0

    def test_is_valid_position(self):
        """Test position validation."""
        board = Board(width=10, height=10)

        # Valid positions
        assert board.is_valid_position(0, 0) is True
        assert board.is_valid_position(5, 5) is True
        assert board.is_valid_position(9, 9) is True

        # Invalid positions
        assert board.is_valid_position(-1, 0) is False
        assert board.is_valid_position(0, -1) is False
        assert board.is_valid_position(10, 5) is False
        assert board.is_valid_position(5, 10) is False

    def test_get_cell(self):
        """Test getting cell at position."""
        board = Board()
        cell = board.get_cell(5, 5)

        assert cell is not None
        assert cell.position == (5, 5)

    def test_get_cell_out_of_bounds(self):
        """Test getting cell at invalid position returns None."""
        board = Board()

        assert board.get_cell(-1, 0) is None
        assert board.get_cell(100, 0) is None

    def test_get_cell_at(self):
        """Test getting cell using tuple position."""
        board = Board()
        cell = board.get_cell_at((3, 4))

        assert cell is not None
        assert cell.position == (3, 4)

    def test_set_occupant(self):
        """Test setting cell occupant."""
        board = Board()
        position = (5, 5)

        board.set_occupant(position, 42)
        cell = board.get_cell_at(position)
        assert cell.occupant == 42

    def test_clear_occupant(self):
        """Test clearing cell occupant."""
        board = Board()
        position = (5, 5)

        board.set_occupant(position, 42)
        board.clear_occupant(position)

        cell = board.get_cell_at(position)
        assert cell.occupant is None

    def test_get_starting_position(self):
        """Test getting starting positions for each player."""
        board = Board()

        pos0 = board.get_starting_position(0)
        pos1 = board.get_starting_position(1)
        pos2 = board.get_starting_position(2)
        pos3 = board.get_starting_position(3)

        # Check they're at corners
        assert pos0 == (0, 0)
        assert pos1 == (board.width - 1, 0)
        assert pos2 == (0, board.height - 1)
        assert pos3 == (board.width - 1, board.height - 1)

    def test_get_starting_position_wraps(self):
        """Test starting position wraps for player index > 3."""
        board = Board()

        # Should wrap around
        assert board.get_starting_position(4) == board.get_starting_position(0)
        assert board.get_starting_position(5) == board.get_starting_position(1)

    def test_get_crystal_position(self):
        """Test getting crystal position."""
        board = Board()
        pos = board.get_crystal_position()

        assert pos == (board.width // 2, board.height // 2)

    def test_board_serialization(self):
        """Test board serialization."""
        board = Board(width=5, height=5)
        board.set_occupant((2, 2), 99)

        data = board.to_dict()

        assert data["width"] == 5
        assert data["height"] == 5
        assert len(data["grid"]) == 5
        assert len(data["grid"][0]) == 5

        # Check that occupant was serialized
        restored = Board.from_dict(data)
        cell = restored.get_cell(2, 2)
        assert cell.occupant == 99

    def test_board_serialization_preserves_special_cells(self):
        """Test that serialization preserves special cell types."""
        board = Board()

        # Serialize and deserialize
        data = board.to_dict()
        restored = Board.from_dict(data)

        # Check crystal position preserved
        crystal_pos = restored.get_crystal_position()
        crystal_cell = restored.get_cell_at(crystal_pos)
        assert crystal_cell.cell_type == CellType.CRYSTAL

        # Check generators preserved
        original_gens = set(board.get_generator_positions())
        restored_gens = set(restored.get_generator_positions())
        assert original_gens == restored_gens

        # Check mystery squares preserved
        original_mystery = set(board.get_mystery_positions())
        restored_mystery = set(restored.get_mystery_positions())
        assert original_mystery == restored_mystery
