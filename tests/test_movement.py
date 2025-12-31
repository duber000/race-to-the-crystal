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

    def test_get_valid_moves_blocked_by_enemy_tokens(self):
        """Test that tokens can't move through cells occupied by enemy tokens."""
        board = Board(width=10, height=10)
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        enemy_token = Token(id=99, player_id="p2", health=10, max_health=10, position=(6, 5))

        # Block path to the right with an enemy token
        board.set_occupant((6, 5), 99)
        tokens_dict = {1: token, 99: enemy_token}

        valid_moves = MovementSystem.get_valid_moves(token, board, tokens_dict=tokens_dict)

        # Can't reach the blocked cell itself (enemy token)
        assert (6, 5) not in valid_moves

        # Can still reach other directions
        assert (5, 6) in valid_moves
        assert (4, 5) in valid_moves

    def test_get_valid_moves_friendly_stacking_on_normal_cell(self):
        """Test that tokens CANNOT stack on normal cells with friendly tokens."""
        board = Board(width=10, height=10)
        token = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        friendly_token = Token(id=99, player_id="p1", health=10, max_health=10, position=(6, 5))

        # Friendly token to the right on a normal cell
        board.set_occupant((6, 5), 99)
        tokens_dict = {1: token, 99: friendly_token}

        valid_moves = MovementSystem.get_valid_moves(token, board, tokens_dict=tokens_dict)

        # CANNOT reach the friendly token's cell on normal cell (no stacking on normal cells)
        assert (6, 5) not in valid_moves

        # Can still reach other directions
        assert (5, 6) in valid_moves
        assert (4, 5) in valid_moves

    def test_get_valid_moves_friendly_stacking_on_generator(self):
        """Test that tokens CAN stack on generator cells with friendly tokens."""
        board = Board(width=24, height=24)  # Full size to have generators
        # Generator is at (6, 6)
        generator_pos = board.get_generator_positions()[0]

        token = Token(id=1, player_id="p1", health=6, max_health=6, position=(generator_pos[0]-1, generator_pos[1]))
        friendly_token = Token(id=99, player_id="p1", health=10, max_health=10, position=generator_pos)

        # Friendly token on the generator
        board.set_occupant(generator_pos, 99)
        tokens_dict = {1: token, 99: friendly_token}

        valid_moves = MovementSystem.get_valid_moves(token, board, tokens_dict=tokens_dict)

        # CAN reach the generator cell even with friendly token (stacking allowed on generators)
        assert generator_pos in valid_moves

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

    def test_find_path_with_occupant(self):
        """Test pathfinding goes through occupied cells (stacking is allowed)."""
        board = Board(width=10, height=10)
        start = (0, 0)
        end = (2, 0)

        # Place a token on direct path - but path can still go through
        board.set_occupant((1, 0), 99)

        path = MovementSystem.find_path(start, end, board, max_distance=5)

        # Path should exist and go through (stacking allowed at find_path level)
        assert path is not None
        assert path[0] == start
        assert path[-1] == end

    def test_find_path_max_distance_limit(self):
        """Test pathfinding respects max_distance limit."""
        board = Board(width=10, height=10)
        start = (0, 0)
        end = (5, 5)

        # With max_distance=3, can't reach (5,5) which is 5+ steps away
        path = MovementSystem.find_path(start, end, board, max_distance=3)

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
