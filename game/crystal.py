"""
Crystal capture and win condition logic.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from shared.constants import (
    CRYSTAL_BASE_TOKENS_REQUIRED,
    CRYSTAL_CAPTURE_TURNS_REQUIRED,
)


@dataclass
class Crystal:
    """
    Represents the power crystal in the center of the board.

    The crystal must be held by a player with enough tokens for enough turns to win.
    The required number of tokens is reduced by disabled generators.

    Attributes:
        position: (x, y) position on the board
        holding_player_id: ID of player currently holding crystal
        holding_token_ids: IDs of tokens currently on crystal
        turns_held: Number of consecutive turns held by current player
        base_tokens_required: Base number of tokens required to hold crystal
    """
    position: Tuple[int, int]
    holding_player_id: Optional[str] = None
    holding_token_ids: List[int] = field(default_factory=list)
    turns_held: int = 0
    base_tokens_required: int = CRYSTAL_BASE_TOKENS_REQUIRED

    @property
    def turns_required(self) -> int:
        """Number of turns required to win."""
        return CRYSTAL_CAPTURE_TURNS_REQUIRED

    def get_tokens_required(self, disabled_generators: int) -> int:
        """
        Calculate number of tokens required based on disabled generators.

        Each disabled generator reduces the requirement by 2, with a minimum of 1 token.

        Args:
            disabled_generators: Number of generators that have been disabled

        Returns:
            Number of tokens required to hold crystal
        """
        reduction = disabled_generators * 2
        required = self.base_tokens_required - reduction
        return max(1, required)

    def _count_tokens_by_player(self, tokens_at_position: List[Tuple[int, str]]) -> dict[str, List[int]]:
        """
        Group tokens by their controlling player.

        Args:
            tokens_at_position: List of (token_id, player_id) tuples

        Returns:
            Dictionary mapping player_id to list of their token_ids
        """
        player_token_counts: dict[str, List[int]] = {}
        for token_id, player_id in tokens_at_position:
            if player_id not in player_token_counts:
                player_token_counts[player_id] = []
            player_token_counts[player_id].append(token_id)
        return player_token_counts

    def _find_dominant_player(self, player_token_counts: dict[str, List[int]]) -> Tuple[Optional[str], int]:
        """
        Determine which player has the most tokens, if any.

        Args:
            player_token_counts: Dictionary mapping player_id to token_ids

        Returns:
            Tuple of (dominant_player_id, token_count). Returns (None, count) if contested.
        """
        dominant_player: Optional[str] = None
        dominant_count = 0

        for player_id, token_ids in player_token_counts.items():
            if len(token_ids) > dominant_count:
                dominant_player = player_id
                dominant_count = len(token_ids)
            elif len(token_ids) == dominant_count and dominant_count > 0:
                dominant_player = None  # Contested

        return (dominant_player, dominant_count)

    def _process_win_logic(
        self,
        dominant_player: Optional[str],
        dominant_count: int,
        required_tokens: int,
        player_token_counts: dict[str, List[int]]
    ) -> Optional[str]:
        """
        Update crystal holding state and check for win condition.

        Args:
            dominant_player: Player with most tokens, or None if contested
            dominant_count: Number of tokens the dominant player has
            required_tokens: Number of tokens required to hold crystal
            player_token_counts: Full token counts by player

        Returns:
            Player ID if win condition met, otherwise None
        """
        if dominant_player and dominant_count >= required_tokens:
            if dominant_player == self.holding_player_id:
                self.turns_held += 1
                self.holding_token_ids = player_token_counts[dominant_player]

                if self.turns_held >= self.turns_required:
                    return dominant_player
            else:
                self.holding_player_id = dominant_player
                self.turns_held = 1
                self.holding_token_ids = player_token_counts[dominant_player]
        else:
            self.holding_player_id = None
            self.turns_held = 0

        return None

    def update_capture_status(
        self,
        tokens_at_position: List[Tuple[int, str]],
        disabled_generators: int
    ) -> Optional[str]:
        """
        Update crystal capture status based on tokens at this position.

        Args:
            tokens_at_position: List of (token_id, player_id) tuples at crystal position
            disabled_generators: Number of disabled generators

        Returns:
            Player ID of winner if win condition met, otherwise None
        """
        self.holding_token_ids.clear()

        player_token_counts = self._count_tokens_by_player(tokens_at_position)
        dominant_player, dominant_count = self._find_dominant_player(player_token_counts)
        required_tokens = self.get_tokens_required(disabled_generators)

        return self._process_win_logic(dominant_player, dominant_count, required_tokens, player_token_counts)

    def reset_capture(self) -> None:
        """Reset capture progress."""
        self.holding_player_id = None
        self.turns_held = 0
        self.holding_token_ids.clear()

    def get_capture_progress(self) -> Tuple[int, int]:
        """
        Get capture progress.

        Returns:
            Tuple of (turns_held, turns_required)
        """
        return (self.turns_held, self.turns_required)

    def get_token_requirement(self, disabled_generators: int) -> Tuple[int, int]:
        """
        Get token requirement.

        Args:
            disabled_generators: Number of disabled generators

        Returns:
            Tuple of (current_tokens, required_tokens)
        """
        return (len(self.holding_token_ids), self.get_tokens_required(disabled_generators))

    def is_contested(self) -> bool:
        """Check if crystal is currently contested."""
        return self.holding_player_id is None and len(self.holding_token_ids) > 0

    def to_dict(self) -> dict:
        """Convert crystal to dictionary for serialization."""
        return {
            "position": list(self.position),
            "holding_player_id": self.holding_player_id,
            "holding_token_ids": self.holding_token_ids,
            "turns_held": self.turns_held,
            "base_tokens_required": self.base_tokens_required,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Crystal":
        """Create crystal from dictionary."""
        return cls(
            position=tuple(data["position"]),
            holding_player_id=data["holding_player_id"],
            holding_token_ids=data["holding_token_ids"],
            turns_held=data["turns_held"],
            base_tokens_required=data["base_tokens_required"],
        )

    def __repr__(self) -> str:
        if self.holding_player_id:
            return f"Crystal(Pos={self.position}, Held by {self.holding_player_id}, {self.turns_held}/{self.turns_required} turns)"
        return f"Crystal(Pos={self.position}, Unclaimed)"


class CrystalManager:
    """Manages crystal capture logic."""

    @staticmethod
    def create_crystal(position: Tuple[int, int]) -> Crystal:
        """
        Create a crystal at specified position.

        Args:
            position: (x, y) position for crystal

        Returns:
            Created Crystal object
        """
        return Crystal(position=position)

    @staticmethod
    def check_win_condition(
        crystal: Crystal,
        tokens_at_position: List[Tuple[int, str]],
        disabled_generators: int
    ) -> Optional[str]:
        """
        Check if win condition is met and update crystal status.

        Args:
            crystal: The crystal object
            tokens_at_position: List of (token_id, player_id) tuples at crystal position
            disabled_generators: Number of disabled generators

        Returns:
            Player ID of winner if win condition met, otherwise None
        """
        return crystal.update_capture_status(tokens_at_position, disabled_generators)

    @staticmethod
    def get_capture_status_message(
        crystal: Crystal,
        disabled_generators: int
    ) -> str:
        """
        Get a human-readable status message for the crystal.

        Args:
            crystal: The crystal object
            disabled_generators: Number of disabled generators

        Returns:
            Status message string
        """
        if not crystal.holding_player_id:
            return "Crystal is unclaimed"

        current_tokens, required_tokens = crystal.get_token_requirement(disabled_generators)
        turns_held, turns_required = crystal.get_capture_progress()

        return (
            f"Player {crystal.holding_player_id} holds crystal with "
            f"{current_tokens}/{required_tokens} tokens for "
            f"{turns_held}/{turns_required} turns"
        )
