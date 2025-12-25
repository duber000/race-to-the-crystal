"""
Unit tests for Generator class and GeneratorManager.
"""
import pytest
from game.generator import Generator, GeneratorManager


class TestGenerator:
    """Test cases for Generator class."""

    def test_generator_creation(self):
        """Test creating a generator."""
        gen = Generator(id=0, position=(5, 5))

        assert gen.id == 0
        assert gen.position == (5, 5)
        assert gen.capturing_player_id is None
        assert gen.capture_token_ids == []
        assert gen.turns_held == 0
        assert gen.is_disabled is False

    def test_generator_requirements(self):
        """Test generator capture requirements."""
        gen = Generator(id=0, position=(5, 5))

        assert gen.required_tokens == 2
        assert gen.required_turns == 2
        assert gen.token_reduction_value == 2

    def test_update_capture_status_no_tokens(self):
        """Test updating with no tokens on generator."""
        gen = Generator(id=0, position=(5, 5))

        was_disabled = gen.update_capture_status([])

        assert was_disabled is False
        assert gen.capturing_player_id is None
        assert gen.turns_held == 0
        assert gen.is_disabled is False

    def test_update_capture_status_insufficient_tokens(self):
        """Test updating with insufficient tokens."""
        gen = Generator(id=0, position=(5, 5))

        # Only 1 token (need 2)
        tokens = [(1, "p1")]
        was_disabled = gen.update_capture_status(tokens)

        assert was_disabled is False
        assert gen.capturing_player_id is None
        assert gen.turns_held == 0

    def test_update_capture_status_start_capture(self):
        """Test starting capture with sufficient tokens."""
        gen = Generator(id=0, position=(5, 5))

        # 2 tokens from same player
        tokens = [(1, "p1"), (2, "p1")]
        was_disabled = gen.update_capture_status(tokens)

        assert was_disabled is False
        assert gen.capturing_player_id == "p1"
        assert gen.turns_held == 1
        assert gen.capture_token_ids == [1, 2]
        assert gen.is_disabled is False

    def test_update_capture_status_continue_capture(self):
        """Test continuing capture over multiple turns."""
        gen = Generator(id=0, position=(5, 5))

        # Turn 1
        tokens = [(1, "p1"), (2, "p1")]
        gen.update_capture_status(tokens)
        assert gen.turns_held == 1

        # Turn 2 - same player continues
        was_disabled = gen.update_capture_status(tokens)

        assert was_disabled is True  # Generator disabled after 2 turns
        assert gen.capturing_player_id == "p1"
        assert gen.turns_held == 2
        assert gen.is_disabled is True

    def test_update_capture_status_contested(self):
        """Test contested generator (multiple players with equal tokens)."""
        gen = Generator(id=0, position=(5, 5))

        # 2 tokens each from different players
        tokens = [(1, "p1"), (2, "p1"), (3, "p2"), (4, "p2")]
        was_disabled = gen.update_capture_status(tokens)

        assert was_disabled is False
        assert gen.capturing_player_id is None  # Contested
        assert gen.turns_held == 0

    def test_update_capture_status_switch_player(self):
        """Test capture switching to different player."""
        gen = Generator(id=0, position=(5, 5))

        # Turn 1 - Player 1 starts
        tokens_p1 = [(1, "p1"), (2, "p1")]
        gen.update_capture_status(tokens_p1)
        assert gen.capturing_player_id == "p1"
        assert gen.turns_held == 1

        # Turn 2 - Player 2 takes over
        tokens_p2 = [(3, "p2"), (4, "p2")]
        was_disabled = gen.update_capture_status(tokens_p2)

        assert was_disabled is False
        assert gen.capturing_player_id == "p2"  # Switched
        assert gen.turns_held == 1  # Reset to 1

    def test_update_capture_status_more_than_required(self):
        """Test capture with more tokens than required."""
        gen = Generator(id=0, position=(5, 5))

        # 3 tokens (need only 2)
        tokens = [(1, "p1"), (2, "p1"), (3, "p1")]
        was_disabled = gen.update_capture_status(tokens)

        assert was_disabled is False
        assert gen.capturing_player_id == "p1"
        assert gen.turns_held == 1
        assert len(gen.capture_token_ids) == 3

    def test_update_capture_status_already_disabled(self):
        """Test that disabled generator can't be updated."""
        gen = Generator(id=0, position=(5, 5))
        gen.is_disabled = True

        tokens = [(1, "p1"), (2, "p1")]
        was_disabled = gen.update_capture_status(tokens)

        assert was_disabled is False  # Already disabled
        assert gen.capture_token_ids == []  # Not updated

    def test_reset_capture(self):
        """Test resetting capture progress."""
        gen = Generator(id=0, position=(5, 5))

        # Set up some capture progress
        tokens = [(1, "p1"), (2, "p1")]
        gen.update_capture_status(tokens)
        assert gen.turns_held == 1

        # Reset
        gen.reset_capture()

        assert gen.capturing_player_id is None
        assert gen.turns_held == 0
        assert gen.capture_token_ids == []

    def test_reset_capture_disabled(self):
        """Test that reset doesn't affect disabled generators."""
        gen = Generator(id=0, position=(5, 5))
        gen.is_disabled = True
        gen.capturing_player_id = "p1"

        gen.reset_capture()

        # Disabled status preserved, but other fields still reset
        assert gen.is_disabled is True

    def test_get_capture_progress(self):
        """Test getting capture progress."""
        gen = Generator(id=0, position=(5, 5))

        progress = gen.get_capture_progress()
        assert progress == (0, 2)

        # Add some progress
        tokens = [(1, "p1"), (2, "p1")]
        gen.update_capture_status(tokens)

        progress = gen.get_capture_progress()
        assert progress == (1, 2)

    def test_generator_serialization(self):
        """Test generator serialization."""
        gen = Generator(
            id=3,
            position=(10, 15),
            capturing_player_id="p1",
            capture_token_ids=[1, 2, 3],
            turns_held=1,
            is_disabled=False
        )

        data = gen.to_dict()

        assert data["id"] == 3
        assert data["position"] == [10, 15]
        assert data["capturing_player_id"] == "p1"
        assert data["capture_token_ids"] == [1, 2, 3]
        assert data["turns_held"] == 1
        assert data["is_disabled"] is False

        restored = Generator.from_dict(data)
        assert restored.id == gen.id
        assert restored.position == gen.position
        assert restored.capturing_player_id == gen.capturing_player_id
        assert restored.turns_held == gen.turns_held
        assert restored.is_disabled == gen.is_disabled


class TestGeneratorManager:
    """Test cases for GeneratorManager."""

    def test_create_generators(self):
        """Test creating generators at positions."""
        positions = [(5, 5), (10, 10), (15, 15), (20, 20)]
        generators = GeneratorManager.create_generators(positions)

        assert len(generators) == 4
        assert generators[0].position == (5, 5)
        assert generators[1].position == (10, 10)
        assert generators[2].position == (15, 15)
        assert generators[3].position == (20, 20)

        # Check IDs are sequential
        assert generators[0].id == 0
        assert generators[1].id == 1
        assert generators[2].id == 2
        assert generators[3].id == 3

    def test_update_all_generators(self):
        """Test updating all generators."""
        positions = [(5, 5), (10, 10)]
        generators = GeneratorManager.create_generators(positions)

        # Set up token positions
        tokens_by_position = {
            (5, 5): [(1, "p1"), (2, "p1")],  # Gen 0 - sufficient for capture
            (10, 10): [(3, "p2")],           # Gen 1 - insufficient
        }

        newly_disabled = GeneratorManager.update_all_generators(generators, tokens_by_position)

        assert len(newly_disabled) == 0  # None disabled yet (first turn)
        assert generators[0].capturing_player_id == "p1"
        assert generators[0].turns_held == 1
        assert generators[1].capturing_player_id is None

    def test_update_all_generators_disable(self):
        """Test disabling generators through updates."""
        positions = [(5, 5)]
        generators = GeneratorManager.create_generators(positions)

        tokens = [(1, "p1"), (2, "p1")]
        tokens_by_position = {(5, 5): tokens}

        # Turn 1
        newly_disabled = GeneratorManager.update_all_generators(generators, tokens_by_position)
        assert len(newly_disabled) == 0

        # Turn 2
        newly_disabled = GeneratorManager.update_all_generators(generators, tokens_by_position)
        assert len(newly_disabled) == 1
        assert 0 in newly_disabled
        assert generators[0].is_disabled is True

    def test_count_disabled_generators(self):
        """Test counting disabled generators."""
        positions = [(5, 5), (10, 10), (15, 15)]
        generators = GeneratorManager.create_generators(positions)

        # Initially none disabled
        assert GeneratorManager.count_disabled_generators(generators) == 0

        # Disable one
        generators[0].is_disabled = True
        assert GeneratorManager.count_disabled_generators(generators) == 1

        # Disable another
        generators[2].is_disabled = True
        assert GeneratorManager.count_disabled_generators(generators) == 2

    def test_get_generator_at_position(self):
        """Test finding generator at position."""
        positions = [(5, 5), (10, 10)]
        generators = GeneratorManager.create_generators(positions)

        gen = GeneratorManager.get_generator_at_position(generators, (5, 5))
        assert gen is not None
        assert gen.id == 0

        gen = GeneratorManager.get_generator_at_position(generators, (10, 10))
        assert gen is not None
        assert gen.id == 1

        gen = GeneratorManager.get_generator_at_position(generators, (99, 99))
        assert gen is None
