"""
Crystal effects system for fog of war and phantom enemies.
"""
from dataclasses import dataclass, field
from typing import Self
import random

from shared.enums import CrystalEffect
from shared.constants import (
    CRYSTAL_EFFECT_INITIAL_DURATION,
    CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR,
    PHANTOM_ENEMIES_COUNT,
)
from shared.types import TokenID, PlayerID


@dataclass
class ActiveEffect:
    """
    Represents an active crystal effect on a player.

    Attributes:
        effect_type: Type of effect (FOG_OF_WAR or PHANTOM_ENEMIES)
        turns_remaining: Number of turns until effect expires
        applied_turn: Turn number when effect was applied
    """
    effect_type: CrystalEffect
    turns_remaining: int
    applied_turn: int

    def reduce_duration(self, amount: int = 1) -> None:
        """Reduce effect duration by specified amount."""
        self.turns_remaining = max(0, self.turns_remaining - amount)

    def is_active(self) -> bool:
        """Check if effect is still active."""
        return self.turns_remaining > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "effect_type": self.effect_type.value,
            "turns_remaining": self.turns_remaining,
            "applied_turn": self.applied_turn,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary."""
        return cls(
            effect_type=CrystalEffect(data["effect_type"]),
            turns_remaining=data["turns_remaining"],
            applied_turn=data["applied_turn"],
        )


@dataclass
class PhantomToken:
    """
    Represents a phantom/illusion token shown to a player.

    Attributes:
        phantom_id: Unique ID for this phantom (negative to avoid collision)
        apparent_player_id: Player ID this phantom appears to belong to
        position: Position on the board
        apparent_health: Health value shown
    """
    phantom_id: int
    apparent_player_id: PlayerID
    position: tuple[int, int]
    apparent_health: int

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "phantom_id": self.phantom_id,
            "apparent_player_id": self.apparent_player_id,
            "position": list(self.position),
            "apparent_health": self.apparent_health,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary."""
        return cls(
            phantom_id=data["phantom_id"],
            apparent_player_id=data["apparent_player_id"],
            position=tuple(data["position"]),
            apparent_health=data["apparent_health"],
        )


@dataclass
class PlayerEffects:
    """
    Tracks all active effects on a specific player.

    Attributes:
        player_id: ID of affected player
        active_effects: List of currently active effects
        phantom_tokens: List of phantom tokens this player sees
    """
    player_id: PlayerID
    active_effects: list[ActiveEffect] = field(default_factory=list)
    phantom_tokens: list[PhantomToken] = field(default_factory=list)

    def has_effect(self, effect_type: CrystalEffect) -> bool:
        """Check if player has a specific effect active."""
        return any(e.effect_type == effect_type and e.is_active() for e in self.active_effects)

    def get_effect(self, effect_type: CrystalEffect) -> ActiveEffect | None:
        """Get specific active effect if it exists."""
        for effect in self.active_effects:
            if effect.effect_type == effect_type and effect.is_active():
                return effect
        return None

    def add_effect(self, effect_type: CrystalEffect, duration: int, turn_number: int) -> ActiveEffect:
        """Add or refresh an effect."""
        # Remove existing effect of same type
        self.active_effects = [e for e in self.active_effects if e.effect_type != effect_type]

        # Add new effect
        effect = ActiveEffect(
            effect_type=effect_type,
            turns_remaining=duration,
            applied_turn=turn_number
        )
        self.active_effects.append(effect)
        return effect

    def reduce_all_durations(self, amount: int = 1) -> None:
        """Reduce duration of all active effects."""
        for effect in self.active_effects:
            effect.reduce_duration(amount)

        # Remove expired effects
        self.active_effects = [e for e in self.active_effects if e.is_active()]

        # Clear phantom tokens if phantom effect expired
        if not self.has_effect(CrystalEffect.PHANTOM_ENEMIES):
            self.phantom_tokens.clear()

    def clear_expired_effects(self) -> None:
        """Remove all expired effects."""
        self.active_effects = [e for e in self.active_effects if e.is_active()]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "player_id": self.player_id,
            "active_effects": [e.to_dict() for e in self.active_effects],
            "phantom_tokens": [p.to_dict() for p in self.phantom_tokens],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary."""
        return cls(
            player_id=data["player_id"],
            active_effects=[ActiveEffect.from_dict(e) for e in data["active_effects"]],
            phantom_tokens=[PhantomToken.from_dict(p) for p in data["phantom_tokens"]],
        )


class CrystalEffectsManager:
    """Manages crystal effects on all players."""

    def __init__(self):
        self.player_effects: dict[PlayerID, PlayerEffects] = {}
        self._next_phantom_id = -1  # Negative IDs for phantoms

    def get_player_effects(self, player_id: PlayerID) -> PlayerEffects:
        """Get or create effects tracking for a player."""
        if player_id not in self.player_effects:
            self.player_effects[player_id] = PlayerEffects(player_id=player_id)
        return self.player_effects[player_id]

    def apply_effect(
        self,
        player_id: PlayerID,
        effect_type: CrystalEffect,
        turn_number: int,
        duration: int | None = None
    ) -> None:
        """
        Apply a crystal effect to a player.

        Args:
            player_id: Player to affect
            effect_type: Type of effect to apply
            turn_number: Current turn number
            duration: Effect duration (uses default if None)
        """
        if duration is None:
            duration = CRYSTAL_EFFECT_INITIAL_DURATION

        effects = self.get_player_effects(player_id)
        effects.add_effect(effect_type, duration, turn_number)

    def reduce_effect_durations_for_generator_capture(
        self,
        capturing_player_id: PlayerID
    ) -> None:
        """
        Reduce effect durations for a player who captured a generator.

        Args:
            capturing_player_id: Player who captured the generator
        """
        effects = self.get_player_effects(capturing_player_id)
        effects.reduce_all_durations(CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR)

    def end_turn_update(self) -> None:
        """Update all effects at end of turn (natural decay)."""
        for effects in self.player_effects.values():
            effects.clear_expired_effects()

    def generate_phantom_tokens(
        self,
        affected_player_id: PlayerID,
        other_player_ids: list[PlayerID],
        board_width: int,
        board_height: int,
        occupied_positions: set[tuple[int, int]]
    ) -> list[PhantomToken]:
        """
        Generate phantom enemy tokens for a player affected by phantom enemies effect.

        Args:
            affected_player_id: Player who will see these phantoms
            other_player_ids: Other players in the game
            board_width: Width of game board
            board_height: Height of game board
            occupied_positions: Positions currently occupied by real tokens

        Returns:
            List of generated phantom tokens
        """
        effects = self.get_player_effects(affected_player_id)

        # Clear old phantoms
        effects.phantom_tokens.clear()

        # Only generate if effect is active
        if not effects.has_effect(CrystalEffect.PHANTOM_ENEMIES):
            return []

        # Generate phantom tokens
        for _ in range(PHANTOM_ENEMIES_COUNT):
            # Random position not occupied
            max_attempts = 50
            for _ in range(max_attempts):
                x = random.randint(0, board_width - 1)
                y = random.randint(0, board_height - 1)
                pos = (x, y)

                if pos not in occupied_positions:
                    # Random enemy player
                    apparent_player = random.choice(other_player_ids) if other_player_ids else affected_player_id

                    # Random health
                    apparent_health = random.choice([4, 6, 8, 10])

                    phantom = PhantomToken(
                        phantom_id=self._next_phantom_id,
                        apparent_player_id=apparent_player,
                        position=pos,
                        apparent_health=apparent_health
                    )

                    effects.phantom_tokens.append(phantom)
                    self._next_phantom_id -= 1
                    break

        return effects.phantom_tokens

    def filter_visible_tokens(
        self,
        viewing_player_id: PlayerID,
        all_tokens: list,
        get_token_player_id
    ) -> list:
        """
        Filter tokens based on fog of war effect.

        Args:
            viewing_player_id: Player viewing the board
            all_tokens: All tokens in the game
            get_token_player_id: Function to get player_id from token

        Returns:
            List of visible tokens
        """
        effects = self.get_player_effects(viewing_player_id)

        # If no fog of war, show all tokens
        if not effects.has_effect(CrystalEffect.FOG_OF_WAR):
            return all_tokens

        # With fog of war, only show own tokens
        return [t for t in all_tokens if get_token_player_id(t) == viewing_player_id]

    def get_tokens_for_player_view(
        self,
        viewing_player_id: PlayerID,
        real_tokens: list,
        get_token_player_id
    ) -> tuple[list, list[PhantomToken]]:
        """
        Get all tokens a player should see (real + phantom).

        Args:
            viewing_player_id: Player viewing the board
            real_tokens: All real tokens
            get_token_player_id: Function to get player_id from token

        Returns:
            Tuple of (visible_real_tokens, phantom_tokens)
        """
        # Filter real tokens by fog of war
        visible_tokens = self.filter_visible_tokens(
            viewing_player_id,
            real_tokens,
            get_token_player_id
        )

        # Get phantom tokens if effect active
        effects = self.get_player_effects(viewing_player_id)
        phantoms = effects.phantom_tokens if effects.has_effect(CrystalEffect.PHANTOM_ENEMIES) else []

        return visible_tokens, phantoms

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "player_effects": {pid: effects.to_dict() for pid, effects in self.player_effects.items()},
            "next_phantom_id": self._next_phantom_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dictionary."""
        manager = cls()
        manager.player_effects = {
            pid: PlayerEffects.from_dict(effects_data)
            for pid, effects_data in data.get("player_effects", {}).items()
        }
        manager._next_phantom_id = data.get("next_phantom_id", -1)
        return manager
