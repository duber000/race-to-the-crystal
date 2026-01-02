"""
Mystery square random event handling.
"""
from dataclasses import dataclass
import random
from typing import Tuple, TYPE_CHECKING

from game.token import Token
from shared.enums import MysteryEffect

if TYPE_CHECKING:
    from game.board import Board


@dataclass
class MysteryEventResult:
    """
    Result of triggering a mystery square.

    Attributes:
        effect: Type of effect that occurred
        token_id: ID of token that triggered the event
        old_position: Token's position before event
        new_position: Token's position after event (may be same)
        old_health: Token's health before event
        new_health: Token's health after event
    """
    effect: MysteryEffect
    token_id: int
    old_position: Tuple[int, int]
    new_position: Tuple[int, int]
    old_health: int
    new_health: int

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "effect": self.effect.name,
            "token_id": self.token_id,
            "old_position": list(self.old_position),
            "new_position": list(self.new_position),
            "old_health": self.old_health,
            "new_health": self.new_health,
        }

    def __repr__(self) -> str:
        if self.effect == MysteryEffect.HEAL:
            return f"Token {self.token_id} healed from {self.old_health} to {self.new_health}"
        elif self.effect == MysteryEffect.TELEPORT:
            return f"Token {self.token_id} teleported from {self.old_position} to {self.new_position}"
        return f"Token {self.token_id} triggered {self.effect.name}"


class MysterySquareSystem:
    """Handles mystery square effects."""

    @staticmethod
    def trigger_mystery_event(
        token: Token,
        board: "Board",
        player_index: int
    ) -> MysteryEventResult:
        """
        Trigger mystery square effect for a token.

        The effect is a coin flip:
        - Heads: Heal to full health
        - Tails: Teleport back to deployment area (first empty cell, or corner if all full)

        Args:
            token: Token that landed on mystery square
            board: Game board (for finding deployment area)
            player_index: Player's index (0-3) for determining deployment area

        Returns:
            MysteryEventResult describing what happened
        """
        # Store old values
        old_position = token.position
        old_health = token.health

        # Coin flip (50/50 chance)
        is_heads = random.choice([True, False])

        if is_heads:
            # Heads: Heal to full health
            token.heal_to_full()
            effect = MysteryEffect.HEAL
            new_position = old_position  # Position unchanged
        else:
            # Tails: Teleport back to deployment area
            # Find first empty cell in deployment area
            deployment_positions = board.get_deployable_positions(player_index)
            teleport_position = None

            for pos in deployment_positions:
                cell = board.get_cell_at(pos)
                if cell and not cell.is_occupied():
                    teleport_position = pos
                    break

            # If no empty cell found, use corner position as fallback
            if teleport_position is None:
                teleport_position = board.get_starting_position(player_index)

            token.move_to(teleport_position)
            effect = MysteryEffect.TELEPORT
            new_position = teleport_position

        return MysteryEventResult(
            effect=effect,
            token_id=token.id,
            old_position=old_position,
            new_position=token.position,
            old_health=old_health,
            new_health=token.health,
        )

    @staticmethod
    def can_trigger_mystery_event(token: Token) -> bool:
        """
        Check if token can trigger a mystery event.

        Args:
            token: Token to check

        Returns:
            True if token can trigger mystery event
        """
        return token.is_alive

    @staticmethod
    def get_effect_description(effect: MysteryEffect) -> str:
        """
        Get human-readable description of a mystery effect.

        Args:
            effect: Mystery effect type

        Returns:
            Description string
        """
        if effect == MysteryEffect.HEAL:
            return "Healed to full health!"
        elif effect == MysteryEffect.TELEPORT:
            return "Teleported back to deployment area!"
        return "Unknown effect"

    @staticmethod
    def simulate_effect(effect: MysteryEffect) -> str:
        """
        Simulate what would happen for each effect (for UI preview).

        Args:
            effect: Mystery effect type

        Returns:
            Description of what would happen
        """
        if effect == MysteryEffect.HEAL:
            return "Token will be healed to maximum health"
        elif effect == MysteryEffect.TELEPORT:
            return "Token will be sent back to deployment area"
        return "Unknown"
