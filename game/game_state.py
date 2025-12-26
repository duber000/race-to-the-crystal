"""
Central game state management.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json

from shared.enums import GamePhase, PlayerColor, TurnPhase
from shared.constants import (
    TOKEN_HEALTH_VALUES,
    TOKENS_PER_HEALTH_VALUE,
)
from game.board import Board
from game.player import Player
from game.token import Token


@dataclass
class GameState:
    """
    Central game state containing all game entities and status.

    Attributes:
        board: The game board
        players: Dictionary of player_id -> Player
        tokens: Dictionary of token_id -> Token
        generators: List of generator objects
        crystal: The power crystal object
        current_turn_player_id: ID of player whose turn it is
        turn_number: Current turn number
        phase: Current game phase
        winner_id: ID of winning player (None if game not won)
    """
    board: Board = field(default_factory=Board)
    players: Dict[str, Player] = field(default_factory=dict)
    tokens: Dict[int, Token] = field(default_factory=dict)
    generators: List = field(default_factory=list)  # Will be List[Generator] when created
    crystal = None  # Will be Crystal object when created
    current_turn_player_id: Optional[str] = None
    turn_number: int = 0
    phase: GamePhase = GamePhase.SETUP
    turn_phase: TurnPhase = TurnPhase.MOVEMENT
    winner_id: Optional[str] = None
    _next_token_id: int = 0

    @property
    def current_player_id(self) -> Optional[str]:
        """Alias for current_turn_player_id."""
        return self.current_turn_player_id

    @property
    def game_phase(self) -> GamePhase:
        """Alias for phase."""
        return self.phase

    def add_player(self, player_id: str, name: str, color: PlayerColor) -> Player:
        """
        Add a new player to the game.

        Args:
            player_id: Unique identifier for the player
            name: Player's display name
            color: Player's color

        Returns:
            The created Player object
        """
        player = Player(id=player_id, name=name, color=color)
        self.players[player_id] = player
        return player

    def remove_player(self, player_id: str) -> None:
        """Remove a player from the game."""
        if player_id in self.players:
            del self.players[player_id]

    def create_tokens_for_player(self, player_id: str) -> List[Token]:
        """
        Create all tokens for a player in reserve (not deployed to board).

        Args:
            player_id: ID of player to create tokens for

        Returns:
            List of created tokens
        """
        if player_id not in self.players:
            raise ValueError(f"Player {player_id} not found")

        player = self.players[player_id]
        tokens = []

        # Get player's starting corner position (used as reference for deployment)
        player_index = player.color.value
        corner_pos = self.board.get_starting_position(player_index)

        # Create tokens with different health values
        # Tokens start in reserve (is_deployed=False) and are not placed on board
        for health_value in TOKEN_HEALTH_VALUES:
            for _ in range(TOKENS_PER_HEALTH_VALUE):
                token = Token(
                    id=self._next_token_id,
                    player_id=player_id,
                    health=health_value,
                    max_health=health_value,
                    position=corner_pos,  # Reference position (not actually on board yet)
                    is_deployed=False,  # Starts in reserve
                )
                self.tokens[token.id] = token
                player.add_token(token.id)
                tokens.append(token)
                self._next_token_id += 1

        return tokens

    def get_token(self, token_id: int) -> Optional[Token]:
        """Get token by ID."""
        return self.tokens.get(token_id)

    def get_reserve_tokens(self, player_id: str) -> List[Token]:
        """
        Get all tokens in reserve (not deployed) for a player.

        Args:
            player_id: Player ID

        Returns:
            List of tokens not yet deployed
        """
        player = self.get_player(player_id)
        if not player:
            return []

        return [
            self.tokens[tid]
            for tid in player.token_ids
            if tid in self.tokens and not self.tokens[tid].is_deployed
        ]

    def get_reserve_token_counts(self, player_id: str) -> dict:
        """
        Get count of reserve tokens by health value.

        Args:
            player_id: Player ID

        Returns:
            Dictionary mapping health value to count
        """
        reserve = self.get_reserve_tokens(player_id)
        counts = {10: 0, 8: 0, 6: 0, 4: 0}
        for token in reserve:
            if token.max_health in counts:
                counts[token.max_health] += 1
        return counts

    def deploy_token(self, player_id: str, health_value: int, position: Tuple[int, int]) -> Optional[Token]:
        """
        Deploy a token from reserve to the board.

        Args:
            player_id: Player ID
            health_value: Health value of token to deploy (10, 8, 6, or 4)
            position: Position to deploy to

        Returns:
            The deployed token, or None if no token available
        """
        # Find first available token of requested type in reserve
        reserve = self.get_reserve_tokens(player_id)
        for token in reserve:
            if token.max_health == health_value:
                # Deploy the token
                token.position = position
                token.is_deployed = True
                self.board.set_occupant(position, token.id)
                return token

        return None

    def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID."""
        return self.players.get(player_id)

    def get_current_player(self) -> Optional[Player]:
        """Get the current player whose turn it is."""
        if self.current_turn_player_id:
            return self.get_player(self.current_turn_player_id)
        elif self.current_player_id:
            return self.get_player(self.current_player_id)
        return None

    def get_tokens_at_position(self, position: tuple) -> List[Token]:
        """
        Get all tokens at a specific position.

        Args:
            position: (x, y) position

        Returns:
            List of tokens at that position
        """
        return [t for t in self.tokens.values() if t.position == position and t.is_alive]

    def get_player_tokens(self, player_id: str) -> List[Token]:
        """
        Get all alive, deployed tokens for a player.

        Args:
            player_id: Player ID

        Returns:
            List of alive, deployed tokens owned by player
        """
        player = self.get_player(player_id)
        if not player:
            return []

        return [
            self.tokens[tid]
            for tid in player.token_ids
            if tid in self.tokens and self.tokens[tid].is_alive and self.tokens[tid].is_deployed
        ]

    def move_token(self, token_id: int, new_position: tuple) -> bool:
        """
        Move a token to a new position.

        Args:
            token_id: ID of token to move
            new_position: Target (x, y) position

        Returns:
            True if move was successful
        """
        token = self.get_token(token_id)
        if not token or not token.is_alive:
            return False

        # Clear old position
        self.board.clear_occupant(token.position)

        # Move token
        token.move_to(new_position)

        # Set new position
        self.board.set_occupant(new_position, token_id)

        return True

    def remove_token(self, token_id: int) -> None:
        """
        Remove a dead token from play.

        Args:
            token_id: ID of token to remove
        """
        token = self.get_token(token_id)
        if not token:
            return

        # Clear from board
        self.board.clear_occupant(token.position)

        # Remove from player
        player = self.get_player(token.player_id)
        if player:
            player.remove_token(token_id)

        # Mark as not alive
        token.is_alive = False

    def start_game(self) -> None:
        """Start the game and set up initial state."""
        if self.phase != GamePhase.SETUP:
            return

        # Create tokens for all players
        for player_id in self.players.keys():
            self.create_tokens_for_player(player_id)

        # Initialize generators and crystal (will implement when those classes exist)
        # self.generators = [...]
        # self.crystal = Crystal(...)

        # Set first player
        if self.players:
            self.current_turn_player_id = list(self.players.keys())[0]

        self.phase = GamePhase.PLAYING
        self.turn_number = 1

    def end_turn(self) -> None:
        """End current turn and advance to next player."""
        if not self.current_turn_player_id:
            return

        # Get list of active players
        active_players = [
            pid for pid, player in self.players.items()
            if player.is_active
        ]

        if not active_players:
            return

        # Find current player index
        try:
            current_index = active_players.index(self.current_turn_player_id)
        except ValueError:
            current_index = -1

        # Move to next active player
        next_index = (current_index + 1) % len(active_players)
        self.current_turn_player_id = active_players[next_index]

        # If we wrapped around to first player, increment turn number
        if next_index == 0:
            self.turn_number += 1

    def check_win_condition(self) -> Optional[str]:
        """
        Check if any player has won the game.

        Returns:
            Player ID of winner, or None if no winner yet
        """
        # Will implement when Crystal class is created
        # For now, return current winner_id
        return self.winner_id

    def set_winner(self, player_id: str) -> None:
        """
        Set the game winner and end the game.

        Args:
            player_id: ID of winning player
        """
        self.winner_id = player_id
        self.phase = GamePhase.ENDED

    def to_dict(self) -> dict:
        """Convert game state to dictionary for serialization."""
        return {
            "board": self.board.to_dict(),
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "tokens": {tid: t.to_dict() for tid, t in self.tokens.items()},
            "generators": [],  # Will implement when Generator class exists
            "crystal": None,  # Will implement when Crystal class exists
            "current_turn_player_id": self.current_turn_player_id,
            "turn_number": self.turn_number,
            "phase": self.phase.name,
            "winner_id": self.winner_id,
        }

    def to_json(self) -> str:
        """Convert game state to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """Create game state from dictionary."""
        state = cls()
        state.board = Board.from_dict(data["board"])
        state.players = {
            pid: Player.from_dict(pdata)
            for pid, pdata in data["players"].items()
        }
        state.tokens = {
            int(tid): Token.from_dict(tdata)
            for tid, tdata in data["tokens"].items()
        }
        # state.generators = ... (will implement when Generator class exists)
        # state.crystal = ... (will implement when Crystal class exists)
        state.current_turn_player_id = data["current_turn_player_id"]
        state.turn_number = data["turn_number"]
        state.phase = GamePhase[data["phase"]]
        state.winner_id = data["winner_id"]
        return state

    @classmethod
    def from_json(cls, json_str: str) -> "GameState":
        """Create game state from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __repr__(self) -> str:
        return f"GameState(Phase={self.phase.name}, Turn={self.turn_number}, Players={len(self.players)})"
