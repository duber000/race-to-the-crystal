"""
Movement system with pathfinding.
"""

from typing import List, Tuple, Set, Optional, Dict
from collections import deque

from game.token import Token
from game.board import Board


class MovementSystem:
    """Handles movement validation and pathfinding."""

    # 8-directional movement (orthogonal + diagonal)
    DIRECTIONS = [
        (-1, -1),
        (-1, 0),
        (-1, 1),  # Top-left, Top, Top-right
        (0, -1),
        (0, 1),  # Left, Right
        (1, -1),
        (1, 0),
        (1, 1),  # Bottom-left, Bottom, Bottom-right
    ]

    @staticmethod
    def get_valid_moves(
        token: Token,
        board: Board,
        max_range: Optional[int] = None,
        tokens_dict: Optional[Dict[int, Token]] = None,
    ) -> Set[Tuple[int, int]]:
        """
        Calculate all valid destination cells for a token using BFS.

        Args:
            token: Token to move
            board: Game board
            max_range: Maximum movement range (uses token's range if None)
            tokens_dict: Dictionary of all tokens (for enemy detection)

        Returns:
            Set of valid (x, y) positions
        """
        if not token.is_alive:
            return set()

        if max_range is None:
            max_range = token.movement_range

        start = token.position
        player_id = token.player_id
        visited: Set[Tuple[int, int]] = {start}
        queue = deque([(start, 0)])
        valid_moves: Set[Tuple[int, int]] = set()

        while queue:
            (x, y), distance = queue.popleft()

            # Don't explore beyond movement range
            if distance >= max_range:
                continue

            # Check all 8 directions
            for dx, dy in MovementSystem.DIRECTIONS:
                nx, ny = x + dx, y + dy

                # Check if already visited
                if (nx, ny) in visited:
                    continue

                # Check bounds
                if not board.is_valid_position(nx, ny):
                    continue

                # Get cell
                cell = board.get_cell(nx, ny)
                if not cell:
                    continue

                # Check if cell is occupied
                if cell.is_occupied() and tokens_dict:
                    # Check if cell has enemy tokens (can't move onto or through enemy cells)
                    if cell.has_enemy_tokens(player_id, tokens_dict):
                        continue
                    # Friendly tokens - only allow stacking on generator and crystal cells
                    from shared.enums import CellType

                    if cell.cell_type not in (CellType.GENERATOR, CellType.CRYSTAL):
                        # Can't stack on regular cells with friendly tokens
                        continue

                # Mark as visited
                visited.add((nx, ny))

                # Add to valid moves (but not starting position)
                if (nx, ny) != start:
                    valid_moves.add((nx, ny))

                # Continue exploring from this cell
                queue.append(((nx, ny), distance + 1))

        return valid_moves

    @staticmethod
    def is_valid_move(
        token: Token,
        destination: Tuple[int, int],
        board: Board,
        tokens_dict: Optional[Dict[int, Token]] = None,
    ) -> bool:
        """
        Check if a move is valid for a token.

        Args:
            token: Token to move
            destination: Target (x, y) position
            board: Game board
            tokens_dict: Dictionary of all tokens (for enemy detection)

        Returns:
            True if move is valid
        """
        if not token.is_alive:
            return False

        # Check if destination is in valid moves
        valid_moves = MovementSystem.get_valid_moves(
            token, board, tokens_dict=tokens_dict
        )
        return destination in valid_moves

    @staticmethod
    def find_path(
        start: Tuple[int, int], end: Tuple[int, int], board: Board, max_distance: int
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Find shortest path from start to end using BFS.

        Args:
            start: Starting (x, y) position
            end: Target (x, y) position
            board: Game board
            max_distance: Maximum path length

        Returns:
            List of positions forming path (including start and end),
            or None if no path exists within max_distance
        """
        if start == end:
            return [start]

        visited: Set[Tuple[int, int]] = {start}
        queue = deque([(start, [start])])

        while queue:
            (x, y), path = queue.popleft()

            # Check if path is too long
            if len(path) > max_distance:
                continue

            # Check all 8 directions
            for dx, dy in MovementSystem.DIRECTIONS:
                nx, ny = x + dx, y + dy

                # Skip if already visited
                if (nx, ny) in visited:
                    continue

                # Check bounds
                if not board.is_valid_position(nx, ny):
                    continue

                # Get cell
                cell = board.get_cell(nx, ny)
                if not cell:
                    continue

                # Check if this is the destination
                if (nx, ny) == end:
                    return path + [(nx, ny)]

                # Check if cell is passable
                if not cell.is_passable():
                    continue

                # Mark as visited and continue search
                visited.add((nx, ny))
                queue.append(((nx, ny), path + [(nx, ny)]))

        # No path found
        return None

    @staticmethod
    def get_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        """
        Calculate Manhattan distance between two positions.

        Args:
            pos1: First (x, y) position
            pos2: Second (x, y) position

        Returns:
            Manhattan distance
        """
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    @staticmethod
    def get_euclidean_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """
        Calculate Euclidean distance between two positions.

        Args:
            pos1: First (x, y) position
            pos2: Second (x, y) position

        Returns:
            Euclidean distance
        """
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    @staticmethod
    def is_adjacent(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        """
        Check if two positions are adjacent (8-directional).

        Args:
            pos1: First (x, y) position
            pos2: Second (x, y) position

        Returns:
            True if positions are adjacent
        """
        dx = abs(pos1[0] - pos2[0])
        dy = abs(pos1[1] - pos2[1])
        return dx <= 1 and dy <= 1 and (dx + dy) > 0

    @staticmethod
    def get_adjacent_positions(
        position: Tuple[int, int], board: Board
    ) -> List[Tuple[int, int]]:
        """
        Get all valid adjacent positions to a given position.

        Args:
            position: Center (x, y) position
            board: Game board

        Returns:
            List of adjacent (x, y) positions within board bounds
        """
        x, y = position
        adjacent = []

        for dx, dy in MovementSystem.DIRECTIONS:
            nx, ny = x + dx, y + dy
            if board.is_valid_position(nx, ny):
                adjacent.append((nx, ny))

        return adjacent
