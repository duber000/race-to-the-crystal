"""
Test sound effects generation and integration.
"""

import pytest
import array
from client.sound_effects import (
    generate_sliding_sound,
    generate_mystery_bing_sound,
    generate_generator_explosion_sound,
    generate_crystal_shatter_sound,
    generate_flushing_sound,
    save_sound_effect,
    generate_all_sound_effects,
)


class TestSoundEffectsGeneration:
    """Test sound effects generation functions."""

    def test_sliding_sound_generation(self):
        """Test that sliding sound generates valid audio samples."""
        samples = generate_sliding_sound(duration=0.5)
        assert isinstance(samples, array.array)
        assert len(samples) > 0
        assert samples.typecode == "h"  # 16-bit signed short

    def test_mystery_bing_sound_generation(self):
        """Test that mystery bing sound generates valid audio samples."""
        samples = generate_mystery_bing_sound(duration=0.3)
        assert isinstance(samples, array.array)
        assert len(samples) > 0
        assert samples.typecode == "h"

    def test_generator_explosion_sound_generation(self):
        """Test that generator explosion sound generates valid audio samples."""
        samples = generate_generator_explosion_sound(duration=1.2)
        assert isinstance(samples, array.array)
        assert len(samples) > 0
        assert samples.typecode == "h"

    def test_crystal_shatter_sound_generation(self):
        """Test that crystal shatter sound generates valid audio samples."""
        samples = generate_crystal_shatter_sound(duration=1.5)
        assert isinstance(samples, array.array)
        assert len(samples) > 0
        assert samples.typecode == "h"

    def test_flushing_sound_generation(self):
        """Test that flushing sound generates valid audio samples."""
        samples = generate_flushing_sound(duration=2.0)
        assert isinstance(samples, array.array)
        assert len(samples) > 0
        assert samples.typecode == "h"

    def test_sound_effects_file_generation(self, tmp_path):
        """Test that sound effects can be saved to files."""
        sound_effects_dir = tmp_path / "sounds"
        sound_effects_dir.mkdir()

        # Test each sound effect file generation
        sliding_samples = generate_sliding_sound(duration=0.5)
        sliding_path = sound_effects_dir / "sliding.wav"
        save_sound_effect(sliding_samples, str(sliding_path))
        assert sliding_path.exists()

        bing_samples = generate_mystery_bing_sound(duration=0.3)
        bing_path = sound_effects_dir / "mystery_bing.wav"
        save_sound_effect(bing_samples, str(bing_path))
        assert bing_path.exists()

        explosion_samples = generate_generator_explosion_sound(duration=1.2)
        explosion_path = sound_effects_dir / "generator_explosion.wav"
        save_sound_effect(explosion_samples, str(explosion_path))
        assert explosion_path.exists()

        shatter_samples = generate_crystal_shatter_sound(duration=1.5)
        shatter_path = sound_effects_dir / "crystal_shatter.wav"
        save_sound_effect(shatter_samples, str(shatter_path))
        assert shatter_path.exists()

        flushing_samples = generate_flushing_sound(duration=2.0)
        flushing_path = sound_effects_dir / "flushing.wav"
        save_sound_effect(flushing_samples, str(flushing_path))
        assert flushing_path.exists()

    def test_all_sound_effects_generation(self, tmp_path):
        """Test that all sound effects can be generated together."""
        # Generate files in a temporary directory
        sound_effects_dir = tmp_path / "sounds"
        generate_all_sound_effects(output_dir=str(sound_effects_dir))

        # Verify files were created
        assert (sound_effects_dir / "sliding.wav").exists()
        assert (sound_effects_dir / "mystery_bing.wav").exists()
        assert (sound_effects_dir / "generator_explosion.wav").exists()
        assert (sound_effects_dir / "crystal_shatter.wav").exists()
        assert (sound_effects_dir / "flushing.wav").exists()


class TestSoundEffectsIntegration:
    """Test sound effects integration with audio manager."""

    def test_audio_manager_sound_effects_loading(self):
        """Test that audio manager can load sound effects."""
        from client.audio_manager import AudioManager

        # Create audio manager (should load existing sound effects from assets)
        audio_manager = AudioManager()

        # Verify sound effects were loaded
        assert "sliding" in audio_manager.sound_effects
        assert "mystery_bing" in audio_manager.sound_effects
        assert "generator_explosion" in audio_manager.sound_effects
        assert "crystal_shatter" in audio_manager.sound_effects
        assert "flushing" in audio_manager.sound_effects

        # Cleanup
        audio_manager.cleanup()

    def test_audio_manager_sound_effects_playback(self):
        """Test that audio manager can play sound effects (without actual audio)."""
        from client.audio_manager import AudioManager

        # Create audio manager (should load existing sound effects from assets)
        audio_manager = AudioManager()

        # Verify that sound effects have play methods
        assert hasattr(audio_manager.sound_effects["sliding"], "play")
        assert hasattr(audio_manager.sound_effects["mystery_bing"], "play")
        assert hasattr(audio_manager.sound_effects["generator_explosion"], "play")
        assert hasattr(audio_manager.sound_effects["crystal_shatter"], "play")
        assert hasattr(audio_manager.sound_effects["flushing"], "play")

        # Verify that audio manager has playback methods
        assert hasattr(audio_manager, "play_sliding_sound")
        assert hasattr(audio_manager, "play_mystery_bing_sound")
        assert hasattr(audio_manager, "play_generator_explosion_sound")
        assert hasattr(audio_manager, "play_crystal_shatter_sound")
        assert hasattr(audio_manager, "play_flushing_sound")

        # Cleanup
        audio_manager.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
