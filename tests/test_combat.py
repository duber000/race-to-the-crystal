"""
Unit tests for CombatSystem class.
"""
import pytest
from game.combat import CombatSystem, CombatOutcome
from game.token import Token
from shared.enums import CombatResult


class TestCombatSystem:
    """Test cases for CombatSystem."""

    def test_can_attack_valid(self):
        """Test valid attack conditions."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p2", health=8, max_health=8, position=(6, 5))

        assert CombatSystem.can_attack(attacker, defender) is True

    def test_can_attack_same_player(self):
        """Test that tokens from same player can't attack each other."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p1", health=8, max_health=8, position=(6, 5))

        assert CombatSystem.can_attack(attacker, defender) is False

    def test_can_attack_not_adjacent(self):
        """Test that tokens must be adjacent to attack."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p2", health=8, max_health=8, position=(10, 10))

        assert CombatSystem.can_attack(attacker, defender) is False

    def test_can_attack_attacker_dead(self):
        """Test that dead tokens can't attack."""
        attacker = Token(id=1, player_id="p1", health=0, max_health=10, position=(5, 5))
        attacker.is_alive = False
        defender = Token(id=2, player_id="p2", health=8, max_health=8, position=(6, 5))

        assert CombatSystem.can_attack(attacker, defender) is False

    def test_can_attack_defender_dead(self):
        """Test that dead tokens can't be attacked."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p2", health=0, max_health=8, position=(6, 5))
        defender.is_alive = False

        assert CombatSystem.can_attack(attacker, defender) is False

    def test_can_attack_all_8_directions(self):
        """Test that attack works in all 8 adjacent directions."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        # Test all 8 adjacent positions
        adjacent_positions = [
            (4, 4), (5, 4), (6, 4),
            (4, 5),         (6, 5),
            (4, 6), (5, 6), (6, 6)
        ]

        for pos in adjacent_positions:
            defender = Token(id=2, player_id="p2", health=8, max_health=8, position=pos)
            assert CombatSystem.can_attack(attacker, defender) is True

    def test_resolve_combat_hit(self):
        """Test combat that damages but doesn't kill defender."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p2", health=8, max_health=8, position=(6, 5))

        result = CombatSystem.resolve_combat(attacker, defender)

        # Attacker deals 5 damage (10 // 2)
        assert result.result == CombatResult.HIT
        assert result.damage_dealt == 5
        assert result.attacker_id == 1
        assert result.defender_id == 2
        assert result.defender_killed is False

        # Defender should have 3 health remaining
        assert defender.health == 3
        assert defender.is_alive is True

        # Attacker should be unharmed
        assert attacker.health == 10

    def test_resolve_combat_killed(self):
        """Test combat that kills defender."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p2", health=4, max_health=4, position=(6, 5))

        result = CombatSystem.resolve_combat(attacker, defender)

        # Attacker deals 5 damage, defender has 4 health
        assert result.result == CombatResult.KILLED
        assert result.damage_dealt == 5
        assert result.defender_killed is True

        # Defender should be dead
        assert defender.health == 0
        assert defender.is_alive is False

        # Attacker should be unharmed
        assert attacker.health == 10

    def test_resolve_combat_invalid(self):
        """Test combat with invalid conditions."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p1", health=8, max_health=8, position=(6, 5))  # Same player

        result = CombatSystem.resolve_combat(attacker, defender)

        assert result.result == CombatResult.INVALID
        assert result.damage_dealt == 0
        assert result.defender_killed is False

        # No damage should be dealt
        assert defender.health == 8

    def test_resolve_combat_damage_calculation(self):
        """Test that damage is calculated correctly for different health values."""
        # Test with health 10
        attacker_10 = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p2", health=20, max_health=20, position=(6, 5))
        result = CombatSystem.resolve_combat(attacker_10, defender)
        assert result.damage_dealt == 5  # 10 // 2

        # Test with health 8
        attacker_8 = Token(id=3, player_id="p1", health=8, max_health=8, position=(5, 5))
        defender2 = Token(id=4, player_id="p2", health=20, max_health=20, position=(6, 5))
        result = CombatSystem.resolve_combat(attacker_8, defender2)
        assert result.damage_dealt == 4  # 8 // 2

        # Test with health 6
        attacker_6 = Token(id=5, player_id="p1", health=6, max_health=6, position=(5, 5))
        defender3 = Token(id=6, player_id="p2", health=20, max_health=20, position=(6, 5))
        result = CombatSystem.resolve_combat(attacker_6, defender3)
        assert result.damage_dealt == 3  # 6 // 2

        # Test with health 4
        attacker_4 = Token(id=7, player_id="p1", health=4, max_health=4, position=(5, 5))
        defender4 = Token(id=8, player_id="p2", health=20, max_health=20, position=(6, 5))
        result = CombatSystem.resolve_combat(attacker_4, defender4)
        assert result.damage_dealt == 2  # 4 // 2

    def test_resolve_combat_attacker_damaged(self):
        """Test that damaged attackers deal less damage."""
        attacker = Token(id=1, player_id="p1", health=3, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p2", health=8, max_health=8, position=(6, 5))

        result = CombatSystem.resolve_combat(attacker, defender)

        # Damaged attacker with 3 health deals 1 damage (3 // 2)
        assert result.damage_dealt == 1
        assert defender.health == 7

    def test_get_attackable_targets(self):
        """Test getting list of attackable targets."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        all_tokens = {
            1: attacker,
            2: Token(id=2, player_id="p2", health=8, max_health=8, position=(6, 5)),  # Adjacent, different player
            3: Token(id=3, player_id="p1", health=6, max_health=6, position=(4, 5)),  # Adjacent, same player
            4: Token(id=4, player_id="p2", health=4, max_health=4, position=(10, 10)),  # Far away
            5: Token(id=5, player_id="p2", health=0, max_health=4, position=(5, 6), is_alive=False),  # Dead
        }

        targets = CombatSystem.get_attackable_targets(attacker, all_tokens)

        # Should only be able to attack token 2
        assert len(targets) == 1
        assert targets[0].id == 2

    def test_get_attackable_targets_multiple(self):
        """Test getting multiple attackable targets."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        all_tokens = {
            1: attacker,
            2: Token(id=2, player_id="p2", health=8, max_health=8, position=(6, 5)),
            3: Token(id=3, player_id="p2", health=6, max_health=6, position=(5, 6)),
            4: Token(id=4, player_id="p2", health=4, max_health=4, position=(4, 4)),
        }

        targets = CombatSystem.get_attackable_targets(attacker, all_tokens)

        # Should be able to attack all three enemy tokens
        assert len(targets) == 3
        target_ids = [t.id for t in targets]
        assert 2 in target_ids
        assert 3 in target_ids
        assert 4 in target_ids

    def test_calculate_damage_preview(self):
        """Test calculating damage without executing attack."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p2", health=8, max_health=8, position=(6, 5))

        damage = CombatSystem.calculate_damage_preview(attacker, defender)

        assert damage == 5
        # Defender should be unchanged
        assert defender.health == 8

    def test_calculate_damage_preview_invalid(self):
        """Test damage preview for invalid attack."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))
        defender = Token(id=2, player_id="p1", health=8, max_health=8, position=(6, 5))  # Same player

        damage = CombatSystem.calculate_damage_preview(attacker, defender)

        assert damage is None

    def test_would_kill(self):
        """Test checking if attack would kill defender."""
        attacker = Token(id=1, player_id="p1", health=10, max_health=10, position=(5, 5))

        # Defender with 4 health, attacker deals 5 damage
        defender_weak = Token(id=2, player_id="p2", health=4, max_health=4, position=(6, 5))
        assert CombatSystem.would_kill(attacker, defender_weak) is True

        # Defender with 10 health, attacker deals 5 damage
        defender_strong = Token(id=3, player_id="p2", health=10, max_health=10, position=(6, 5))
        assert CombatSystem.would_kill(attacker, defender_strong) is False

        # Exact damage
        defender_exact = Token(id=4, player_id="p2", health=5, max_health=5, position=(6, 5))
        assert CombatSystem.would_kill(attacker, defender_exact) is True

    def test_combat_outcome_serialization(self):
        """Test serializing combat outcome."""
        outcome = CombatOutcome(
            result=CombatResult.KILLED,
            damage_dealt=5,
            attacker_id=1,
            defender_id=2,
            defender_killed=True
        )

        data = outcome.to_dict()

        assert data["result"] == "KILLED"
        assert data["damage_dealt"] == 5
        assert data["attacker_id"] == 1
        assert data["defender_id"] == 2
        assert data["defender_killed"] is True
