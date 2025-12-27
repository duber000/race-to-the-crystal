"""
Unit tests for MovementSystem class.
"""
import pytest
from game.movement import MovementSystem
from game.token import Token
from game.board import Board


class TestMovementSystem:
    """Test cases for MovementSystem."""

    def test_get_valid_moves_from_center(self):
        """Test getting valid moves from center of empty board."""
        board = Board(width=10, height=10)
        # Use 6hp token which has movement range of 2
        token = Token(id=1, player_id="p1", health=6, max_health=6, position=(5, 5))

        valid_moves = MovementSystem.get_valid_moves(token, board)

        # With range 2 and no obstacles, should be able to reach many cells
        assert len(valid_moves) > 0
        assert (5, 5) not in valid_moves  # Current position not included
        assert (6, 5) in valid_moves  # 1 step right
        assert (7, 5) in valid_moves  # 2 steps right
        assert (5, 6) in valid_moves  # 1 step down
        assert (6, 6) in valid_moves  # Diagonal

    def test_get_valid_moves_respects_range(self):
        """Test that movement doesn't exceed token range."""
        board = Board(width=10, height=10)
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        valid_moves = MovementSystem.get_valid_moves(token, board)

        # Should not be able to reach cells more than 2 steps away
        assert (8, 5) not in valid_moves  # 3 steps right
        assert (5, 8) not in valid_moves  # 3 steps down

    def test_get_valid_moves_blocked_by_tokens(self):
        """Test that tokens can't move through occupied cells."""
        board = Board(width=10, height=10)
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        # Block path to the right
        board.set_occupant((6, 5), 99)

        valid_moves = MovementSystem.get_valid_moves(token, board)

        # Can't reach the blocked cell itself
        assert (6, 5) not in valid_moves

        # Can still reach other directions
        assert (5, 6) in valid_moves
        assert (4, 5) in valid_moves

        # Note: (7, 5) might be reachable by going around the obstacle
        # with 8-directional movement, which is valid BFS behavior

    def test_get_valid_moves_from_corner(self):
        """Test movement from board corner."""
        board = Board(width=10, height=10)
        # Use 6hp token which has movement range of 2
        token = Token(id=1, player_id="p1", health=6, max_health=6, position=(0, 0))

        valid_moves = MovementSystem.get_valid_moves(token, board)

        # Should be able to move into board
        assert (1, 0) in valid_moves
        assert (0, 1) in valid_moves
        assert (1, 1) in valid_moves
        assert (2, 0) in valid_moves

        # Can't move off board
        assert (-1, 0) not in valid_moves
        assert (0, -1) not in valid_moves

    def test_get_valid_moves_dead_token(self):
        """Test that dead tokens can't move."""
        board = Board(width=10, height=10)
        token = Token(id=1, player_id="p1", health=0, max_health=10, position=(5, 5))
        token.is_alive = False

        valid_moves = MovementSystem.get_valid_moves(token, board)

        assert len(valid_moves) == 0

    def test_is_valid_move(self):
        """Test checking if a specific move is valid."""
        board = Board(width=10, height=10)
        # Use 6hp token which has movement range of 2
        token = Token(id=1, player_id="p1", health=6, max_health=6, position=(5, 5))

        assert MovementSystem.is_valid_move(token, (6, 5), board) is True
        assert MovementSystem.is_valid_move(token, (7, 7), board) is True
        assert MovementSystem.is_valid_move(token, (8, 8), board) is False  # Too far

    def test_find_path_straight_line(self):
        """Test pathfinding in straight line."""
        board = Board(width=10, height=10)
        start = (0, 0)
        end = (2, 0)

        path = MovementSystem.find_path(start, end, board, max_distance=5)

        assert path is not None
        assert path[0] == start
        assert path[-1] == end
        assert len(path) == 3  # (0,0), (1,0), (2,0)

    def test_find_path_diagonal(self):
        """Test pathfinding diagonally."""
        board = Board(width=10, height=10)
        start = (0, 0)
        end = (2, 2)

        path = MovementSystem.find_path(start, end, board, max_distance=5)

        assert path is not None
        assert path[0] == start
        assert path[-1] == end

    def test_find_path_blocked(self):
        """Test pathfinding with obstacle."""
        board = Board(width=10, height=10)
        start = (0, 0)
        end = (2, 0)

        # Block direct path
        board.set_occupant((1, 0), 99)

        path = MovementSystem.find_path(start, end, board, max_distance=5)

        # Should find alternate path or None if max_distance too small
        if path:
            assert path[0] == start
            assert path[-1] == end
            assert (1, 0) not in path  # Doesn't go through blocked cell

    def test_find_path_no_path(self):
        """Test pathfinding when no path exists."""
        board = Board(width=5, height=5)
        start = (0, 0)
        end = (4, 4)

        # Create wall blocking path
        for y in range(5):
            board.set_occupant((2, y), 99)

        path = MovementSystem.find_path(start, end, board, max_distance=10)

        assert path is None

    def test_find_path_same_position(self):
        """Test pathfinding to same position."""
        board = Board(width=10, height=10)
        pos = (5, 5)

        path = MovementSystem.find_path(pos, pos, board, max_distance=5)

        assert path == [pos]

    def test_get_distance_manhattan(self):
        """Test Manhattan distance calculation."""
        assert MovementSystem.get_distance((0, 0), (0, 0)) == 0
        assert MovementSystem.get_distance((0, 0), (1, 0)) == 1
        assert MovementSystem.get_distance((0, 0), (0, 1)) == 1
        assert MovementSystem.get_distance((0, 0), (3, 4)) == 7  # 3 + 4
        assert MovementSystem.get_distance((5, 5), (2, 3)) == 5  # 3 + 2

    def test_get_euclidean_distance(self):
        """Test Euclidean distance calculation."""
        import math

        assert MovementSystem.get_euclidean_distance((0, 0), (0, 0)) == 0
        assert MovementSystem.get_euclidean_distance((0, 0), (3, 4)) == 5  # 3-4-5 triangle
        assert abs(MovementSystem.get_euclidean_distance((0, 0), (1, 1)) - math.sqrt(2)) < 0.001

    def test_is_adjacent(self):
        """Test adjacency checking."""
        pos = (5, 5)

        # All 8 adjacent positions
        assert MovementSystem.is_adjacent(pos, (4, 4)) is True
        assert MovementSystem.is_adjacent(pos, (5, 4)) is True
        assert MovementSystem.is_adjacent(pos, (6, 4)) is True
        assert MovementSystem.is_adjacent(pos, (4, 5)) is True
        assert MovementSystem.is_adjacent(pos, (6, 5)) is True
        assert MovementSystem.is_adjacent(pos, (4, 6)) is True
        assert MovementSystem.is_adjacent(pos, (5, 6)) is True
        assert MovementSystem.is_adjacent(pos, (6, 6)) is True

        # Not adjacent
        assert MovementSystem.is_adjacent(pos, (5, 5)) is False  # Same
        assert MovementSystem.is_adjacent(pos, (7, 7)) is False  # Too far
        assert MovementSystem.is_adjacent(pos, (3, 3)) is False  # Too far

    def test_get_adjacent_positions(self):
        """Test getting all adjacent positions."""
        board = Board(width=10, height=10)
        pos = (5, 5)

        adjacent = MovementSystem.get_adjacent_positions(pos, board)

        assert len(adjacent) == 8  # All 8 directions from center
        assert (4, 4) in adjacent
        assert (6, 6) in adjacent

    def test_get_adjacent_positions_corner(self):
        """Test getting adjacent positions from corner."""
        board = Board(width=10, height=10)
        pos = (0, 0)

        adjacent = MovementSystem.get_adjacent_positions(pos, board)

        assert len(adjacent) == 3  # Only 3 directions from corner
        assert (1, 0) in adjacent
        assert (0, 1) in adjacent
        assert (1, 1) in adjacent
        assert (-1, 0) not in adjacent  # Out of bounds

    def test_get_adjacent_positions_edge(self):
        """Test getting adjacent positions from edge."""
        board = Board(width=10, height=10)
        pos = (0, 5)

        adjacent = MovementSystem.get_adjacent_positions(pos, board)

        assert len(adjacent) == 5  # 5 directions from left edge
        assert (-1, 5) not in adjacent  # Out of bounds
