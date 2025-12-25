"""
Combat system and resolution.
"""
from dataclasses import dataclass
from typing import Optional

from game.token import Token
from shared.enums import CombatResult


@dataclass
class CombatOutcome:
    """
    Result of a combat action.

    Attributes:
        result: Type of combat result
        damage_dealt: Amount of damage dealt to defender
        attacker_id: ID of attacking token
        defender_id: ID of defending token
        defender_killed: Whether defender was killed
    """
    result: CombatResult
    damage_dealt: int
    attacker_id: int
    defender_id: int
    defender_killed: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "result": self.result.name,
            "damage_dealt": self.damage_dealt,
            "attacker_id": self.attacker_id,
            "defender_id": self.defender_id,
            "defender_killed": self.defender_killed,
        }


class CombatSystem:
    """Handles combat resolution."""

    @staticmethod
    def can_attack(attacker: Token, defender: Token) -> bool:
        """
        Check if attacker can attack defender.

        Args:
            attacker: Attacking token
            defender: Defending token

        Returns:
            True if attack is valid
        """
        # Both must be alive
        if not attacker.is_alive or not defender.is_alive:
            return False

        # Must be from different players
        if attacker.player_id == defender.player_id:
            return False

        # Must be adjacent
        if not attacker.is_adjacent_to(defender.position):
            return False

        return True

    @staticmethod
    def resolve_combat(attacker: Token, defender: Token) -> CombatOutcome:
        """
        Resolve combat between two tokens.

        Rules:
        - Attacker deals damage equal to half their health (rounded down)
        - Attacker takes no damage
        - If defender's health reaches 0 or below, they are killed

        Args:
            attacker: Attacking token
            defender: Defending token

        Returns:
            CombatOutcome describing the result
        """
        # Validate attack
        if not CombatSystem.can_attack(attacker, defender):
            return CombatOutcome(
                result=CombatResult.INVALID,
                damage_dealt=0,
                attacker_id=attacker.id,
                defender_id=defender.id,
                defender_killed=False,
            )

        # Calculate damage
        damage = attacker.attack_power

        # Apply damage to defender
        was_killed = defender.take_damage(damage)

        # Determine result
        result = CombatResult.KILLED if was_killed else CombatResult.HIT

        return CombatOutcome(
            result=result,
            damage_dealt=damage,
            attacker_id=attacker.id,
            defender_id=defender.id,
            defender_killed=was_killed,
        )

    @staticmethod
    def get_attackable_targets(
        attacker: Token,
        all_tokens: dict[int, Token]
    ) -> list[Token]:
        """
        Get list of tokens that can be attacked.

        Args:
            attacker: Attacking token
            all_tokens: Dictionary of all tokens in game

        Returns:
            List of tokens that can be attacked
        """
        if not attacker.is_alive:
            return []

        attackable = []
        for token in all_tokens.values():
            if CombatSystem.can_attack(attacker, token):
                attackable.append(token)

        return attackable

    @staticmethod
    def calculate_damage_preview(attacker: Token, defender: Token) -> Optional[int]:
        """
        Calculate how much damage an attack would deal (without executing).

        Args:
            attacker: Attacking token
            defender: Defending token

        Returns:
            Damage amount, or None if attack is invalid
        """
        if not CombatSystem.can_attack(attacker, defender):
            return None

        return attacker.attack_power

    @staticmethod
    def would_kill(attacker: Token, defender: Token) -> bool:
        """
        Check if an attack would kill the defender.

        Args:
            attacker: Attacking token
            defender: Defending token

        Returns:
            True if attack would kill defender
        """
        damage = CombatSystem.calculate_damage_preview(attacker, defender)
        if damage is None:
            return False

        return defender.health <= damage
