"""
Unit tests for crystal effects system.
"""

from game.crystal_effects import (
    ActiveEffect,
    PhantomToken,
    PlayerEffects,
    CrystalEffectsManager,
)
from game.game_state import GameState
from shared.enums import CrystalEffect
from shared.constants import (
    CRYSTAL_EFFECT_INITIAL_DURATION,
    CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR,
)


class TestActiveEffect:
    """Test ActiveEffect dataclass."""

    def test_create_effect(self):
        """Test creating an active effect."""
        effect = ActiveEffect(
            effect_type=CrystalEffect.FOG_OF_WAR, turns_remaining=4, applied_turn=1
        )
        assert effect.effect_type == CrystalEffect.FOG_OF_WAR
        assert effect.turns_remaining == 4
        assert effect.applied_turn == 1

    def test_reduce_duration(self):
        """Test reducing effect duration."""
        effect = ActiveEffect(CrystalEffect.FOG_OF_WAR, 4, 1)
        effect.reduce_duration(1)
        assert effect.turns_remaining == 3

        effect.reduce_duration(2)
        assert effect.turns_remaining == 1

    def test_reduce_duration_minimum_zero(self):
        """Test that duration doesn't go below zero."""
        effect = ActiveEffect(CrystalEffect.FOG_OF_WAR, 2, 1)
        effect.reduce_duration(5)
        assert effect.turns_remaining == 0

    def test_is_active(self):
        """Test checking if effect is active."""
        effect = ActiveEffect(CrystalEffect.FOG_OF_WAR, 3, 1)
        assert effect.is_active()

        effect.reduce_duration(3)
        assert not effect.is_active()

    def test_serialization(self):
        """Test effect serialization."""
        effect = ActiveEffect(CrystalEffect.PHANTOM_ENEMIES, 4, 2)
        data = effect.to_dict()

        assert data["effect_type"] == CrystalEffect.PHANTOM_ENEMIES.value
        assert data["turns_remaining"] == 4
        assert data["applied_turn"] == 2

        restored = ActiveEffect.from_dict(data)
        assert restored.effect_type == CrystalEffect.PHANTOM_ENEMIES
        assert restored.turns_remaining == 4
        assert restored.applied_turn == 2


class TestPhantomToken:
    """Test PhantomToken dataclass."""

    def test_create_phantom(self):
        """Test creating a phantom token."""
        phantom = PhantomToken(
            phantom_id=-1,
            apparent_player_id="player_0",
            position=(5, 5),
            apparent_health=8,
        )
        assert phantom.phantom_id == -1
        assert phantom.apparent_player_id == "player_0"
        assert phantom.position == (5, 5)
        assert phantom.apparent_health == 8

    def test_serialization(self):
        """Test phantom serialization."""
        phantom = PhantomToken(-2, "player_1", (10, 12), 6)
        data = phantom.to_dict()

        assert data["phantom_id"] == -2
        assert data["apparent_player_id"] == "player_1"
        assert data["position"] == [10, 12]
        assert data["apparent_health"] == 6

        restored = PhantomToken.from_dict(data)
        assert restored.phantom_id == -2
        assert restored.apparent_player_id == "player_1"
        assert restored.position == (10, 12)
        assert restored.apparent_health == 6


class TestPlayerEffects:
    """Test PlayerEffects tracking."""

    def test_create_player_effects(self):
        """Test creating player effects tracker."""
        effects = PlayerEffects(player_id="player_0")
        assert effects.player_id == "player_0"
        assert len(effects.active_effects) == 0
        assert len(effects.phantom_tokens) == 0

    def test_add_effect(self):
        """Test adding an effect."""
        effects = PlayerEffects("player_0")
        effect = effects.add_effect(CrystalEffect.FOG_OF_WAR, 4, 1)

        assert effect.effect_type == CrystalEffect.FOG_OF_WAR
        assert effect.turns_remaining == 4
        assert len(effects.active_effects) == 1

    def test_has_effect(self):
        """Test checking for active effects."""
        effects = PlayerEffects("player_0")
        assert not effects.has_effect(CrystalEffect.FOG_OF_WAR)

        effects.add_effect(CrystalEffect.FOG_OF_WAR, 4, 1)
        assert effects.has_effect(CrystalEffect.FOG_OF_WAR)
        assert not effects.has_effect(CrystalEffect.PHANTOM_ENEMIES)

    def test_get_effect(self):
        """Test getting specific effect."""
        effects = PlayerEffects("player_0")
        effects.add_effect(CrystalEffect.FOG_OF_WAR, 4, 1)

        fog_effect = effects.get_effect(CrystalEffect.FOG_OF_WAR)
        assert fog_effect is not None
        assert fog_effect.turns_remaining == 4

        phantom_effect = effects.get_effect(CrystalEffect.PHANTOM_ENEMIES)
        assert phantom_effect is None

    def test_replace_existing_effect(self):
        """Test that adding same effect replaces the old one."""
        effects = PlayerEffects("player_0")
        effects.add_effect(CrystalEffect.FOG_OF_WAR, 2, 1)
        assert effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == 2

        effects.add_effect(CrystalEffect.FOG_OF_WAR, 4, 3)
        assert effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == 4
        assert len(effects.active_effects) == 1  # Only one effect

    def test_reduce_all_durations(self):
        """Test reducing all effect durations."""
        effects = PlayerEffects("player_0")
        effects.add_effect(CrystalEffect.FOG_OF_WAR, 4, 1)
        effects.add_effect(CrystalEffect.PHANTOM_ENEMIES, 3, 1)

        effects.reduce_all_durations(1)

        assert effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == 3
        assert effects.get_effect(CrystalEffect.PHANTOM_ENEMIES).turns_remaining == 2

    def test_clear_expired_effects(self):
        """Test clearing expired effects."""
        effects = PlayerEffects("player_0")
        effects.add_effect(CrystalEffect.FOG_OF_WAR, 1, 1)
        effects.add_effect(CrystalEffect.PHANTOM_ENEMIES, 3, 1)

        effects.reduce_all_durations(1)
        assert not effects.has_effect(CrystalEffect.FOG_OF_WAR)  # Expired
        assert effects.has_effect(CrystalEffect.PHANTOM_ENEMIES)  # Still active

    def test_phantom_cleared_when_effect_expires(self):
        """Test that phantom tokens are cleared when effect expires."""
        effects = PlayerEffects("player_0")
        effects.add_effect(CrystalEffect.PHANTOM_ENEMIES, 1, 1)
        effects.phantom_tokens.append(PhantomToken(-1, "player_1", (5, 5), 8))

        assert len(effects.phantom_tokens) == 1

        effects.reduce_all_durations(1)
        assert len(effects.phantom_tokens) == 0

    def test_serialization(self):
        """Test player effects serialization."""
        effects = PlayerEffects("player_0")
        effects.add_effect(CrystalEffect.FOG_OF_WAR, 4, 1)
        effects.phantom_tokens.append(PhantomToken(-1, "player_1", (5, 5), 8))

        data = effects.to_dict()
        restored = PlayerEffects.from_dict(data)

        assert restored.player_id == "player_0"
        assert len(restored.active_effects) == 1
        assert restored.has_effect(CrystalEffect.FOG_OF_WAR)
        assert len(restored.phantom_tokens) == 1


class TestCrystalEffectsManager:
    """Test CrystalEffectsManager."""

    def test_create_manager(self):
        """Test creating effects manager."""
        manager = CrystalEffectsManager()
        assert len(manager.player_effects) == 0

    def test_get_player_effects(self):
        """Test getting player effects (auto-creates if needed)."""
        manager = CrystalEffectsManager()
        effects = manager.get_player_effects("player_0")

        assert effects.player_id == "player_0"
        assert "player_0" in manager.player_effects

    def test_apply_effect(self):
        """Test applying an effect to a player."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1)

        effects = manager.get_player_effects("player_0")
        assert effects.has_effect(CrystalEffect.FOG_OF_WAR)
        assert (
            effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining
            == CRYSTAL_EFFECT_INITIAL_DURATION
        )

    def test_apply_effect_custom_duration(self):
        """Test applying effect with custom duration."""
        manager = CrystalEffectsManager()
        manager.apply_effect(
            "player_0", CrystalEffect.FOG_OF_WAR, turn_number=1, duration=2
        )

        effects = manager.get_player_effects("player_0")
        assert effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == 2

    def test_reduce_effect_durations_for_generator_capture(self):
        """Test reducing effect durations when capturing generator."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1)

        initial_duration = (
            manager.get_player_effects("player_0")
            .get_effect(CrystalEffect.FOG_OF_WAR)
            .turns_remaining
        )

        manager.reduce_effect_durations_for_generator_capture("player_0")

        new_duration = (
            manager.get_player_effects("player_0")
            .get_effect(CrystalEffect.FOG_OF_WAR)
            .turns_remaining
        )
        assert new_duration == initial_duration - CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR

    def test_end_turn_update(self):
        """Test end turn update decrements and clears expired effects."""
        manager = CrystalEffectsManager()
        manager.apply_effect(
            "player_0", CrystalEffect.FOG_OF_WAR, turn_number=1, duration=2
        )

        effects = manager.get_player_effects("player_0")
        assert effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == 2

        # First end_turn_update should decrement
        manager.end_turn_update()
        assert effects.has_effect(CrystalEffect.FOG_OF_WAR)
        assert effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == 1

        # Second end_turn_update should expire it
        manager.end_turn_update()
        assert not effects.has_effect(CrystalEffect.FOG_OF_WAR)

    def test_generate_phantom_tokens(self):
        """Test generating phantom tokens."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.PHANTOM_ENEMIES, turn_number=1)

        phantoms = manager.generate_phantom_tokens(
            affected_player_id="player_0",
            other_player_ids=["player_1", "player_2"],
            board_width=24,
            board_height=24,
            occupied_positions=set(),
        )

        assert len(phantoms) > 0
        effects = manager.get_player_effects("player_0")
        assert len(effects.phantom_tokens) == len(phantoms)

        # Verify phantoms appear as OTHER players, not the affected player
        for phantom in phantoms:
            assert phantom.apparent_player_id in ["player_1", "player_2"], (
                f"Phantom should appear as enemy player, not {phantom.apparent_player_id}"
            )
            assert phantom.apparent_player_id != "player_0", (
                "Phantom should not appear as the affected player"
            )

    def test_no_phantoms_without_effect(self):
        """Test that phantoms aren't generated without the effect."""
        manager = CrystalEffectsManager()

        phantoms = manager.generate_phantom_tokens(
            affected_player_id="player_0",
            other_player_ids=["player_1"],
            board_width=24,
            board_height=24,
            occupied_positions=set(),
        )

        assert len(phantoms) == 0

    def test_filter_visible_tokens_no_fog(self):
        """Test token visibility without fog of war."""
        manager = CrystalEffectsManager()

        class MockToken:
            def __init__(self, player_id):
                self.player_id = player_id

        all_tokens = [
            MockToken("player_0"),
            MockToken("player_1"),
            MockToken("player_2"),
        ]

        visible = manager.filter_visible_tokens(
            "player_0", all_tokens, lambda t: t.player_id
        )

        assert len(visible) == 3  # All visible

    def test_filter_visible_tokens_with_fog(self):
        """Test token visibility with fog of war."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1)

        class MockToken:
            def __init__(self, player_id):
                self.player_id = player_id

        all_tokens = [
            MockToken("player_0"),
            MockToken("player_0"),
            MockToken("player_1"),
        ]

        visible = manager.filter_visible_tokens(
            "player_0", all_tokens, lambda t: t.player_id
        )

        assert len(visible) == 2  # Only player_0's tokens

    def test_get_tokens_for_player_view(self):
        """Test getting complete token view for player."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1)
        manager.apply_effect("player_0", CrystalEffect.PHANTOM_ENEMIES, turn_number=1)

        manager.generate_phantom_tokens("player_0", ["player_1"], 24, 24, set())

        class MockToken:
            def __init__(self, player_id):
                self.player_id = player_id

        all_tokens = [MockToken("player_0"), MockToken("player_1")]

        visible, phantoms = manager.get_tokens_for_player_view(
            "player_0", all_tokens, lambda t: t.player_id
        )

        assert len(visible) == 1  # Only own tokens due to fog
        assert len(phantoms) > 0  # Phantom enemies visible

    def test_serialization(self):
        """Test manager serialization."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1)
        manager.apply_effect("player_1", CrystalEffect.PHANTOM_ENEMIES, turn_number=1)

        data = manager.to_dict()
        restored = CrystalEffectsManager.from_dict(data)

        assert "player_0" in restored.player_effects
        assert "player_1" in restored.player_effects
        assert restored.player_effects["player_0"].has_effect(CrystalEffect.FOG_OF_WAR)
        assert restored.player_effects["player_1"].has_effect(
            CrystalEffect.PHANTOM_ENEMIES
        )


class TestGameStateIntegration:
    """Test crystal effects integration with GameState."""

    def test_apply_crystal_effect_to_game_state(self):
        """Test applying crystal effects through game state."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]
        game_state.apply_crystal_effect(player_id, CrystalEffect.FOG_OF_WAR)

        effects = game_state.crystal_effects.get_player_effects(player_id)
        assert effects.has_effect(CrystalEffect.FOG_OF_WAR)

    def test_phantom_tokens_generated_automatically(self):
        """Test that phantom tokens are generated when effect applied."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]
        game_state.apply_crystal_effect(player_id, CrystalEffect.PHANTOM_ENEMIES)

        effects = game_state.crystal_effects.get_player_effects(player_id)
        assert len(effects.phantom_tokens) > 0

    def test_get_visible_tokens_for_player(self):
        """Test getting visible tokens for a player."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_ids = list(game_state.players.keys())
        player_0 = player_ids[0]

        # Apply fog of war to player 0
        game_state.apply_crystal_effect(player_0, CrystalEffect.FOG_OF_WAR)

        # Get visible tokens for player 0
        visible, phantoms = game_state.get_visible_tokens_for_player(player_0)

        # Should only see own tokens
        for token in visible:
            assert token.player_id == player_0

    def test_generator_capture_reduces_effect_duration(self):
        """Test that capturing generator reduces effect durations."""
        # This is tested indirectly through the game state update logic
        # The actual integration happens in _update_generators_and_crystal
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]
        game_state.apply_crystal_effect(player_id, CrystalEffect.FOG_OF_WAR)

        initial_duration = (
            game_state.crystal_effects.get_player_effects(player_id)
            .get_effect(CrystalEffect.FOG_OF_WAR)
            .turns_remaining
        )

        # Manually reduce (simulating generator capture)
        game_state.crystal_effects.reduce_effect_durations_for_generator_capture(
            player_id
        )

        new_duration = (
            game_state.crystal_effects.get_player_effects(player_id)
            .get_effect(CrystalEffect.FOG_OF_WAR)
            .turns_remaining
        )
        assert new_duration == initial_duration - CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR

    def test_game_state_serialization_with_effects(self):
        """Test that game state serialization includes effects."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]
        game_state.apply_crystal_effect(player_id, CrystalEffect.FOG_OF_WAR)

        # Serialize and deserialize
        data = game_state.to_dict()
        restored = GameState.from_dict(data)

        # Check effects were preserved
        effects = restored.crystal_effects.get_player_effects(player_id)
        assert effects.has_effect(CrystalEffect.FOG_OF_WAR)


class TestDamageBoostEffect:
    """Test DAMAGE_BOOST crystal effect."""

    def test_damage_boost_increases_attack_damage(self):
        """Test that damage boost multiplies attack damage correctly."""
        from shared.constants import CRYSTAL_DAMAGE_BOOST_MULTIPLIER

        game_state = GameState.create_game(2)
        game_state.start_game()

        player_ids = list(game_state.players.keys())
        player_0 = player_ids[0]
        player_1 = player_ids[1]

        # Get two tokens from different players
        player_0_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_0 and t.is_deployed
        ]
        player_1_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_1 and t.is_deployed
        ]

        attacker = player_0_tokens[0]
        defender = player_1_tokens[0]

        # Move them adjacent to each other
        attacker_pos = (10, 10)
        defender_pos = (10, 11)
        game_state.move_token(attacker.id, attacker_pos)
        game_state.move_token(defender.id, defender_pos)

        # Record base damage
        base_damage = attacker.attack_power

        # Attack WITHOUT damage boost
        outcome_without_boost = game_state.attack_token(attacker.id, defender.id)
        assert outcome_without_boost is not None
        damage_without_boost = outcome_without_boost.damage_dealt

        # Reset defender to full health
        defender.is_alive = True
        defender.health = defender.max_health
        game_state.board.set_occupant(defender_pos, defender.id)

        # Apply damage boost to attacker's player
        game_state.apply_crystal_effect(player_0, CrystalEffect.DAMAGE_BOOST)

        # Attack WITH damage boost
        outcome_with_boost = game_state.attack_token(attacker.id, defender.id)
        assert outcome_with_boost is not None
        damage_with_boost = outcome_with_boost.damage_dealt

        # Verify boost was applied
        expected_boosted_damage = int(base_damage * CRYSTAL_DAMAGE_BOOST_MULTIPLIER)
        assert damage_with_boost == expected_boosted_damage
        assert damage_with_boost > damage_without_boost

    def test_damage_boost_only_affects_boosted_player(self):
        """Test that damage boost only affects the player who has the effect."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_ids = list(game_state.players.keys())
        player_0 = player_ids[0]
        player_1 = player_ids[1]

        # Apply damage boost to player 0 only
        game_state.apply_crystal_effect(player_0, CrystalEffect.DAMAGE_BOOST)

        # Get tokens - need separate defenders for each player
        player_0_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_0 and t.is_deployed
        ]
        player_1_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_1 and t.is_deployed
        ]

        attacker_p0 = player_0_tokens[0]
        defender_p0 = player_1_tokens[0]  # Player 0 will attack this player 1 token

        attacker_p1 = player_1_tokens[1]
        defender_p1 = player_0_tokens[1]  # Player 1 will attack this player 0 token

        # Position tokens for player 0's attack
        game_state.move_token(attacker_p0.id, (10, 10))
        game_state.move_token(defender_p0.id, (10, 11))

        # Player 0 attacks (has boost)
        p0_base_damage = attacker_p0.attack_power
        outcome_p0 = game_state.attack_token(attacker_p0.id, defender_p0.id)
        assert outcome_p0 is not None
        p0_damage_dealt = outcome_p0.damage_dealt

        # Reset defender to full health
        defender_p0.is_alive = True
        defender_p0.health = defender_p0.max_health
        game_state.board.set_occupant((10, 11), defender_p0.id)

        # Position tokens for player 1's attack
        game_state.move_token(attacker_p1.id, (12, 10))
        game_state.move_token(defender_p1.id, (12, 11))

        # Player 1 attacks (no boost)
        p1_base_damage = attacker_p1.attack_power
        outcome_p1 = game_state.attack_token(attacker_p1.id, defender_p1.id)
        assert outcome_p1 is not None
        p1_damage_dealt = outcome_p1.damage_dealt

        # Player 0's damage should be boosted, player 1's should be normal
        from shared.constants import CRYSTAL_DAMAGE_BOOST_MULTIPLIER

        assert p0_damage_dealt == int(p0_base_damage * CRYSTAL_DAMAGE_BOOST_MULTIPLIER)
        assert p1_damage_dealt == p1_base_damage
        assert p0_damage_dealt > p1_damage_dealt

    def test_damage_boost_expires_after_duration(self):
        """Test that damage boost effect expires after its duration."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]

        # Apply damage boost with short duration
        game_state.apply_crystal_effect(
            player_id, CrystalEffect.DAMAGE_BOOST, duration=2
        )

        effects = game_state.crystal_effects.get_player_effects(player_id)
        assert effects.has_effect(CrystalEffect.DAMAGE_BOOST)
        assert effects.get_effect(CrystalEffect.DAMAGE_BOOST).turns_remaining == 2

        # Reduce duration
        effects.reduce_all_durations(1)
        assert effects.has_effect(CrystalEffect.DAMAGE_BOOST)
        assert effects.get_effect(CrystalEffect.DAMAGE_BOOST).turns_remaining == 1

        # Expire completely
        effects.reduce_all_durations(1)
        assert not effects.has_effect(CrystalEffect.DAMAGE_BOOST)

    def test_damage_boost_reduced_by_generator_capture(self):
        """Test that generator capture reduces damage boost duration."""
        from shared.constants import CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR

        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]

        # Apply damage boost
        game_state.apply_crystal_effect(player_id, CrystalEffect.DAMAGE_BOOST)

        effects = game_state.crystal_effects.get_player_effects(player_id)
        initial_duration = effects.get_effect(
            CrystalEffect.DAMAGE_BOOST
        ).turns_remaining

        # Simulate generator capture
        game_state.crystal_effects.reduce_effect_durations_for_generator_capture(
            player_id
        )

        new_duration = effects.get_effect(CrystalEffect.DAMAGE_BOOST).turns_remaining
        assert new_duration == initial_duration - CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR

    def test_damage_boost_can_kill_defender(self):
        """Test that damage boost can increase damage enough to kill."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_ids = list(game_state.players.keys())
        player_0 = player_ids[0]
        player_1 = player_ids[1]

        # Get tokens
        player_0_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_0 and t.is_deployed
        ]
        player_1_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_1 and t.is_deployed
        ]

        # Find a strong attacker (10hp) and weak defender (4hp)
        attacker = next(
            (t for t in player_0_tokens if t.max_health == 10), player_0_tokens[0]
        )
        defender = next(
            (t for t in player_1_tokens if t.max_health == 4), player_1_tokens[0]
        )

        # Position them
        game_state.move_token(attacker.id, (10, 10))
        game_state.move_token(defender.id, (10, 11))

        # Set defender to low health
        defender.health = 6

        # Base damage from 10hp attacker is 5
        base_damage = attacker.attack_power
        assert base_damage == 5

        # Apply damage boost (5 * 1.5 = 7.5, int = 7)
        game_state.apply_crystal_effect(player_0, CrystalEffect.DAMAGE_BOOST)

        # Attack should kill the 6hp defender
        initial_token_count = len([t for t in game_state.tokens.values() if t.is_alive])
        game_state.attack_token(attacker.id, defender.id)

        # Defender should be dead
        assert not defender.is_alive
        final_token_count = len([t for t in game_state.tokens.values() if t.is_alive])
        assert final_token_count < initial_token_count


class TestSpeedBoostEffect:
    """Test SPEED_BOOST crystal effect."""

    def test_speed_boost_increases_movement_range(self):
        """Test that speed boost increases token movement range."""
        from shared.constants import CRYSTAL_SPEED_BOOST_AMOUNT

        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]
        player_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_id and t.is_deployed
        ]
        token = player_tokens[0]

        # Get base movement range
        base_range = token.movement_range

        # Get effective range without boost
        range_without_boost = game_state.get_token_movement_range(token)
        assert range_without_boost == base_range

        # Apply speed boost
        game_state.apply_crystal_effect(player_id, CrystalEffect.SPEED_BOOST)

        # Get effective range with boost
        range_with_boost = game_state.get_token_movement_range(token)
        assert range_with_boost == base_range + CRYSTAL_SPEED_BOOST_AMOUNT
        assert range_with_boost > range_without_boost

    def test_speed_boost_only_affects_boosted_player(self):
        """Test that speed boost only affects the player who has the effect."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_ids = list(game_state.players.keys())
        player_0 = player_ids[0]
        player_1 = player_ids[1]

        # Apply speed boost to player 0 only
        game_state.apply_crystal_effect(player_0, CrystalEffect.SPEED_BOOST)

        # Get tokens
        player_0_token = next(
            t
            for t in game_state.tokens.values()
            if t.player_id == player_0 and t.is_deployed
        )
        player_1_token = next(
            t
            for t in game_state.tokens.values()
            if t.player_id == player_1 and t.is_deployed
        )

        from shared.constants import CRYSTAL_SPEED_BOOST_AMOUNT

        # Player 0's tokens should have boosted range
        p0_range = game_state.get_token_movement_range(player_0_token)
        assert p0_range == player_0_token.movement_range + CRYSTAL_SPEED_BOOST_AMOUNT

        # Player 1's tokens should have normal range
        p1_range = game_state.get_token_movement_range(player_1_token)
        assert p1_range == player_1_token.movement_range

    def test_speed_boost_applies_to_all_token_types(self):
        """Test that speed boost works for tokens with different health levels."""
        from shared.constants import CRYSTAL_SPEED_BOOST_AMOUNT

        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]

        # Apply speed boost
        game_state.apply_crystal_effect(player_id, CrystalEffect.SPEED_BOOST)

        # Test with different health tokens (movement range varies by health)
        player_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_id and t.is_deployed
        ]

        for token in player_tokens:
            base_range = token.movement_range
            boosted_range = game_state.get_token_movement_range(token)
            assert boosted_range == base_range + CRYSTAL_SPEED_BOOST_AMOUNT, (
                f"Token {token.id} with health {token.health}: expected {base_range + CRYSTAL_SPEED_BOOST_AMOUNT}, got {boosted_range}"
            )

    def test_speed_boost_expires_after_duration(self):
        """Test that speed boost effect expires after its duration."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]

        # Apply speed boost with short duration
        game_state.apply_crystal_effect(
            player_id, CrystalEffect.SPEED_BOOST, duration=2
        )

        effects = game_state.crystal_effects.get_player_effects(player_id)
        assert effects.has_effect(CrystalEffect.SPEED_BOOST)
        assert effects.get_effect(CrystalEffect.SPEED_BOOST).turns_remaining == 2

        # Reduce duration
        effects.reduce_all_durations(1)
        assert effects.has_effect(CrystalEffect.SPEED_BOOST)
        assert effects.get_effect(CrystalEffect.SPEED_BOOST).turns_remaining == 1

        # Expire completely
        effects.reduce_all_durations(1)
        assert not effects.has_effect(CrystalEffect.SPEED_BOOST)

    def test_speed_boost_reduced_by_generator_capture(self):
        """Test that generator capture reduces speed boost duration."""
        from shared.constants import CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR

        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]

        # Apply speed boost
        game_state.apply_crystal_effect(player_id, CrystalEffect.SPEED_BOOST)

        effects = game_state.crystal_effects.get_player_effects(player_id)
        initial_duration = effects.get_effect(CrystalEffect.SPEED_BOOST).turns_remaining

        # Simulate generator capture
        game_state.crystal_effects.reduce_effect_durations_for_generator_capture(
            player_id
        )

        new_duration = effects.get_effect(CrystalEffect.SPEED_BOOST).turns_remaining
        assert new_duration == initial_duration - CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR

    def test_speed_boost_allows_longer_movement(self):
        """Test that speed boost actually allows tokens to move further in gameplay."""
        from game.movement import MovementSystem
        from shared.constants import CRYSTAL_SPEED_BOOST_AMOUNT

        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]
        player_tokens = [
            t
            for t in game_state.tokens.values()
            if t.player_id == player_id and t.is_deployed
        ]
        token = player_tokens[0]

        # Position token in clear area
        start_pos = (12, 12)
        game_state.move_token(token.id, start_pos)

        # Calculate valid moves without boost
        base_range = token.movement_range
        valid_moves_without_boost = MovementSystem.get_valid_moves(
            token, game_state.board, base_range
        )

        # Apply speed boost
        game_state.apply_crystal_effect(player_id, CrystalEffect.SPEED_BOOST)

        # Calculate valid moves with boost
        boosted_range = game_state.get_token_movement_range(token)
        valid_moves_with_boost = MovementSystem.get_valid_moves(
            token, game_state.board, boosted_range
        )

        # Should be able to reach more squares with boost
        assert len(valid_moves_with_boost) > len(valid_moves_without_boost)
        assert boosted_range == base_range + CRYSTAL_SPEED_BOOST_AMOUNT


class TestMultipleEffectsInteraction:
    """Test interactions between multiple crystal effects."""

    def test_damage_and_speed_boost_together(self):
        """Test that a player can have both DAMAGE_BOOST and SPEED_BOOST active."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]

        # Apply both effects
        game_state.apply_crystal_effect(player_id, CrystalEffect.DAMAGE_BOOST)
        game_state.apply_crystal_effect(player_id, CrystalEffect.SPEED_BOOST)

        effects = game_state.crystal_effects.get_player_effects(player_id)
        assert effects.has_effect(CrystalEffect.DAMAGE_BOOST)
        assert effects.has_effect(CrystalEffect.SPEED_BOOST)
        assert len(effects.active_effects) == 2

    def test_all_four_effects_can_coexist(self):
        """Test that all four crystal effects can be active on a player simultaneously."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]

        # Apply all four effects
        game_state.apply_crystal_effect(player_id, CrystalEffect.FOG_OF_WAR)
        game_state.apply_crystal_effect(player_id, CrystalEffect.PHANTOM_ENEMIES)
        game_state.apply_crystal_effect(player_id, CrystalEffect.DAMAGE_BOOST)
        game_state.apply_crystal_effect(player_id, CrystalEffect.SPEED_BOOST)

        effects = game_state.crystal_effects.get_player_effects(player_id)
        assert effects.has_effect(CrystalEffect.FOG_OF_WAR)
        assert effects.has_effect(CrystalEffect.PHANTOM_ENEMIES)
        assert effects.has_effect(CrystalEffect.DAMAGE_BOOST)
        assert effects.has_effect(CrystalEffect.SPEED_BOOST)
        assert len(effects.active_effects) == 4

    def test_random_effect_can_trigger_any_effect(self):
        """Test that random effect triggering can select any of the four effects."""
        import random

        random.seed(42)  # Set seed for reproducibility

        game_state = GameState.create_game(2)
        game_state.start_game()

        # Trigger multiple random effects to see variety
        triggered_effects = set()
        for _ in range(20):
            result = game_state.trigger_random_crystal_effect()
            if result:
                _, effect_type = result
                triggered_effects.add(effect_type)

        # We should see at least 2 different effect types in 20 tries
        # (statistically very likely with 4 options)
        assert len(triggered_effects) >= 2

    def test_effect_serialization_with_all_types(self):
        """Test that all effect types serialize/deserialize correctly."""
        game_state = GameState.create_game(2)
        game_state.start_game()

        player_id = list(game_state.players.keys())[0]

        # Apply all effects
        game_state.apply_crystal_effect(player_id, CrystalEffect.FOG_OF_WAR, duration=3)
        game_state.apply_crystal_effect(
            player_id, CrystalEffect.PHANTOM_ENEMIES, duration=4
        )
        game_state.apply_crystal_effect(
            player_id, CrystalEffect.DAMAGE_BOOST, duration=2
        )
        game_state.apply_crystal_effect(
            player_id, CrystalEffect.SPEED_BOOST, duration=5
        )

        # Serialize
        data = game_state.to_dict()

        # Deserialize
        restored = GameState.from_dict(data)

        # Verify all effects preserved
        restored_effects = restored.crystal_effects.get_player_effects(player_id)
        assert restored_effects.has_effect(CrystalEffect.FOG_OF_WAR)
        assert restored_effects.has_effect(CrystalEffect.PHANTOM_ENEMIES)
        assert restored_effects.has_effect(CrystalEffect.DAMAGE_BOOST)
        assert restored_effects.has_effect(CrystalEffect.SPEED_BOOST)

        # Verify durations
        assert (
            restored_effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == 3
        )
        assert (
            restored_effects.get_effect(CrystalEffect.PHANTOM_ENEMIES).turns_remaining
            == 4
        )
        assert (
            restored_effects.get_effect(CrystalEffect.DAMAGE_BOOST).turns_remaining == 2
        )
        assert (
            restored_effects.get_effect(CrystalEffect.SPEED_BOOST).turns_remaining == 5
        )
