"""
Generator capture mechanics.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from shared.constants import (
    GENERATOR_CAPTURE_TOKENS_REQUIRED,
    GENERATOR_CAPTURE_TURNS_REQUIRED,
    GENERATOR_TOKEN_REDUCTION,
)


@dataclass
class Generator:
    """
    Represents a power generator on the board.

    Generators can be captured by holding them with enough tokens for enough turns.
    Each captured generator reduces the crystal capture requirements.

    Attributes:
        id: Unique identifier for this generator
        position: (x, y) position on the board
        capturing_player_id: ID of player currently capturing (None if contested)
        capture_token_ids: IDs of tokens currently on this generator
        turns_held: Number of consecutive turns held by current player
        is_disabled: Whether this generator has been disabled
    """
    id: int
    position: Tuple[int, int]
    capturing_player_id: Optional[str] = None
    capture_token_ids: List[int] = field(default_factory=list)
    turns_held: int = 0
    is_disabled: bool = False

    @property
    def required_tokens(self) -> int:
        """Number of tokens required to capture."""
        return GENERATOR_CAPTURE_TOKENS_REQUIRED

    @property
    def required_turns(self) -> int:
        """Number of turns required to capture."""
        return GENERATOR_CAPTURE_TURNS_REQUIRED

    @property
    def token_reduction_value(self) -> int:
        """How much this generator reduces crystal requirements when disabled."""
        return GENERATOR_TOKEN_REDUCTION

    def update_capture_status(self, tokens_at_position: List[Tuple[int, str]]) -> bool:
        """
        Update generator capture status based on tokens at this position.

        Args:
            tokens_at_position: List of (token_id, player_id) tuples at generator position

        Returns:
            True if generator was just disabled this update
        """
        if self.is_disabled:
            return False

        # Clear current capture tokens
        self.capture_token_ids.clear()

        # Count tokens by player
        player_token_counts: dict[str, List[int]] = {}
        for token_id, player_id in tokens_at_position:
            if player_id not in player_token_counts:
                player_token_counts[player_id] = []
            player_token_counts[player_id].append(token_id)

        # Find player with most tokens
        dominant_player: Optional[str] = None
        dominant_count = 0

        for player_id, token_ids in player_token_counts.items():
            if len(token_ids) > dominant_count:
                dominant_player = player_id
                dominant_count = len(token_ids)
            elif len(token_ids) == dominant_count and dominant_count > 0:
                # Contested - multiple players have same number of tokens
                dominant_player = None

        # Check if requirements are met
        if dominant_player and dominant_count >= self.required_tokens:
            # Same player continues capturing
            if dominant_player == self.capturing_player_id:
                self.turns_held += 1
                self.capture_token_ids = player_token_counts[dominant_player]

                # Check if capture is complete
                if self.turns_held >= self.required_turns:
                    self.is_disabled = True
                    return True  # Generator just disabled
            else:
                # New player starts capturing
                self.capturing_player_id = dominant_player
                self.turns_held = 1
                self.capture_token_ids = player_token_counts[dominant_player]
        else:
            # Requirements not met - reset capture
            self.capturing_player_id = None
            self.turns_held = 0

        return False

    def reset_capture(self) -> None:
        """Reset capture progress."""
        if not self.is_disabled:
            self.capturing_player_id = None
            self.turns_held = 0
            self.capture_token_ids.clear()

    def get_capture_progress(self) -> Tuple[int, int]:
        """
        Get capture progress.

        Returns:
            Tuple of (turns_held, turns_required)
        """
        return (self.turns_held, self.required_turns)

    def to_dict(self) -> dict:
        """Convert generator to dictionary for serialization."""
        return {
            "id": self.id,
            "position": list(self.position),
            "capturing_player_id": self.capturing_player_id,
            "capture_token_ids": self.capture_token_ids,
            "turns_held": self.turns_held,
            "is_disabled": self.is_disabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Generator":
        """Create generator from dictionary."""
        return cls(
            id=data["id"],
            position=tuple(data["position"]),
            capturing_player_id=data["capturing_player_id"],
            capture_token_ids=data["capture_token_ids"],
            turns_held=data["turns_held"],
            is_disabled=data["is_disabled"],
        )

    def __repr__(self) -> str:
        status = "DISABLED" if self.is_disabled else f"Held {self.turns_held}/{self.required_turns}"
        return f"Generator({self.id}, Pos={self.position}, {status})"


class GeneratorManager:
    """Manages all generators in the game."""

    @staticmethod
    def create_generators(positions: List[Tuple[int, int]]) -> List[Generator]:
        """
        Create generators at specified positions.

        Args:
            positions: List of (x, y) positions for generators

        Returns:
            List of created Generator objects
        """
        generators = []
        for i, position in enumerate(positions):
            generators.append(Generator(id=i, position=position))
        return generators

    @staticmethod
    def update_all_generators(
        generators: List[Generator],
        tokens_by_position: dict[Tuple[int, int], List[Tuple[int, str]]]
    ) -> List[int]:
        """
        Update all generators based on token positions.

        Args:
            generators: List of generators to update
            tokens_by_position: Dictionary mapping positions to (token_id, player_id) lists

        Returns:
            List of generator IDs that were just disabled
        """
        newly_disabled = []

        for generator in generators:
            tokens_at_gen = tokens_by_position.get(generator.position, [])
            was_disabled = generator.update_capture_status(tokens_at_gen)

            if was_disabled:
                newly_disabled.append(generator.id)

        return newly_disabled

    @staticmethod
    def count_disabled_generators(generators: List[Generator]) -> int:
        """
        Count how many generators are disabled.

        Args:
            generators: List of generators

        Returns:
            Number of disabled generators
        """
        return sum(1 for gen in generators if gen.is_disabled)

    @staticmethod
    def get_generator_at_position(
        generators: List[Generator],
        position: Tuple[int, int]
    ) -> Optional[Generator]:
        """
        Find generator at a specific position.

        Args:
            generators: List of generators
            position: (x, y) position to check

        Returns:
            Generator at position, or None if not found
        """
        for generator in generators:
            if generator.position == position:
                return generator
        return None
