"""
Unit tests for crystal effects system.
"""
import pytest

from game.crystal_effects import (
    ActiveEffect,
    PhantomToken,
    PlayerEffects,
    CrystalEffectsManager,
)
from game.game_state import GameState
from shared.enums import CrystalEffect, PlayerColor
from shared.constants import (
    CRYSTAL_EFFECT_INITIAL_DURATION,
    CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR,
)


class TestActiveEffect:
    """Test ActiveEffect dataclass."""

    def test_create_effect(self):
        """Test creating an active effect."""
        effect = ActiveEffect(
            effect_type=CrystalEffect.FOG_OF_WAR,
            turns_remaining=4,
            applied_turn=1
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
            apparent_health=8
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
        assert effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == CRYSTAL_EFFECT_INITIAL_DURATION

    def test_apply_effect_custom_duration(self):
        """Test applying effect with custom duration."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1, duration=2)

        effects = manager.get_player_effects("player_0")
        assert effects.get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining == 2

    def test_reduce_effect_durations_for_generator_capture(self):
        """Test reducing effect durations when capturing generator."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1)

        initial_duration = manager.get_player_effects("player_0").get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining

        manager.reduce_effect_durations_for_generator_capture("player_0")

        new_duration = manager.get_player_effects("player_0").get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining
        assert new_duration == initial_duration - CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR

    def test_end_turn_update(self):
        """Test end turn update clears expired effects."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1, duration=1)

        effects = manager.get_player_effects("player_0")
        effects.reduce_all_durations(1)  # Expire it

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
            occupied_positions=set()
        )

        assert len(phantoms) > 0
        effects = manager.get_player_effects("player_0")
        assert len(effects.phantom_tokens) == len(phantoms)

    def test_no_phantoms_without_effect(self):
        """Test that phantoms aren't generated without the effect."""
        manager = CrystalEffectsManager()

        phantoms = manager.generate_phantom_tokens(
            affected_player_id="player_0",
            other_player_ids=["player_1"],
            board_width=24,
            board_height=24,
            occupied_positions=set()
        )

        assert len(phantoms) == 0

    def test_filter_visible_tokens_no_fog(self):
        """Test token visibility without fog of war."""
        manager = CrystalEffectsManager()

        class MockToken:
            def __init__(self, player_id):
                self.player_id = player_id

        all_tokens = [MockToken("player_0"), MockToken("player_1"), MockToken("player_2")]

        visible = manager.filter_visible_tokens(
            "player_0",
            all_tokens,
            lambda t: t.player_id
        )

        assert len(visible) == 3  # All visible

    def test_filter_visible_tokens_with_fog(self):
        """Test token visibility with fog of war."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1)

        class MockToken:
            def __init__(self, player_id):
                self.player_id = player_id

        all_tokens = [MockToken("player_0"), MockToken("player_0"), MockToken("player_1")]

        visible = manager.filter_visible_tokens(
            "player_0",
            all_tokens,
            lambda t: t.player_id
        )

        assert len(visible) == 2  # Only player_0's tokens

    def test_get_tokens_for_player_view(self):
        """Test getting complete token view for player."""
        manager = CrystalEffectsManager()
        manager.apply_effect("player_0", CrystalEffect.FOG_OF_WAR, turn_number=1)
        manager.apply_effect("player_0", CrystalEffect.PHANTOM_ENEMIES, turn_number=1)

        manager.generate_phantom_tokens(
            "player_0",
            ["player_1"],
            24, 24,
            set()
        )

        class MockToken:
            def __init__(self, player_id):
                self.player_id = player_id

        all_tokens = [MockToken("player_0"), MockToken("player_1")]

        visible, phantoms = manager.get_tokens_for_player_view(
            "player_0",
            all_tokens,
            lambda t: t.player_id
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
        assert restored.player_effects["player_1"].has_effect(CrystalEffect.PHANTOM_ENEMIES)


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
        player_1 = player_ids[1]

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

        initial_duration = game_state.crystal_effects.get_player_effects(player_id).get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining

        # Manually reduce (simulating generator capture)
        game_state.crystal_effects.reduce_effect_durations_for_generator_capture(player_id)

        new_duration = game_state.crystal_effects.get_player_effects(player_id).get_effect(CrystalEffect.FOG_OF_WAR).turns_remaining
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
