"""
Sound effects generation for Race to the Crystal.

This module generates various game sound effects including:
- Movement sliding sounds
- Mystery square "bing" sounds
- Generator explosion sounds
- Crystal shattering sounds
"""

import array
import math
import random
import wave
import os
from typing import Optional


def generate_sliding_sound(duration: float = 0.5, sample_rate: int = 44100) -> array.array:
    """
    Generate a sliding sound effect for token movement.
    
    Creates a whooshing, sliding sound that represents a token moving across the board.
    """
    num_samples = int(sample_rate * duration)
    samples = array.array("h")
    
    for i in range(num_samples):
        t = i / sample_rate
        
        # Create a frequency sweep from high to low (sliding down)
        # Start at 1000Hz, end at 200Hz
        freq = 1000.0 - (800.0 * t)
        
        # Add some randomness for texture
        noise = 0.1 * (random.random() * 2 - 1)
        
        # Create the sliding sound with harmonics
        fundamental = math.sin(2 * math.pi * freq * t)
        harmonic = 0.3 * math.sin(2 * math.pi * freq * 2 * t)
        
        # Add envelope - attack and release
        envelope = min(t * 10, 1.0) * (1.0 - t * 2)  # Quick attack, gradual release
        
        value = int(32767 * 0.7 * (fundamental + harmonic + noise) * envelope)
        value = max(-32768, min(32767, value))
        samples.append(value)
    
    return samples


def generate_mystery_bing_sound(duration: float = 0.3, sample_rate: int = 44100) -> array.array:
    """
    Generate a "bing" sound effect for landing on mystery squares.
    
    Creates a coin-like metallic sound that represents the mystery and chance
    of landing on a mystery square.
    """
    num_samples = int(sample_rate * duration)
    samples = array.array("h")
    
    for i in range(num_samples):
        t = i / sample_rate
        
        # Create a metallic "bing" sound with multiple frequencies
        # Main frequency: 1500Hz (coin-like)
        main_freq = 1500.0
        
        # Add harmonics for metallic quality
        fundamental = math.sin(2 * math.pi * main_freq * t)
        harmonic1 = 0.6 * math.sin(2 * math.pi * main_freq * 1.8 * t)
        harmonic2 = 0.4 * math.sin(2 * math.pi * main_freq * 2.5 * t)
        harmonic3 = 0.2 * math.sin(2 * math.pi * main_freq * 3.2 * t)
        
        # Add some noise for realism
        noise = 0.05 * (random.random() * 2 - 1)
        
        # Create envelope - quick attack and decay (like a coin flip)
        envelope = math.exp(-t * 15) * (1 - math.exp(-t * 50))  # Fast attack, exponential decay
        
        value = int(32767 * 0.8 * (fundamental + harmonic1 + harmonic2 + harmonic3 + noise) * envelope)
        value = max(-32768, min(32767, value))
        samples.append(value)
    
    return samples


def generate_generator_explosion_sound(duration: float = 1.2, sample_rate: int = 44100) -> array.array:
    """
    Generate an explosion sound effect for generators being captured.
    
    Creates a powerful, low-frequency explosion with debris and rumble.
    """
    num_samples = int(sample_rate * duration)
    samples = array.array("h")
    
    for i in range(num_samples):
        t = i / sample_rate
        
        # Main explosion - low frequency boom (50-100Hz)
        boom_freq = 75.0 * (1 - t * 0.5)  # Frequency decreases over time
        boom = 2.0 * math.sin(2 * math.pi * boom_freq * t)
        
        # Add higher frequency components for the explosion "crack"
        crack_freq = 800.0 * math.exp(-t * 3)  # Quickly decaying high frequency
        crack = 0.8 * math.sin(2 * math.pi * crack_freq * t)
        
        # Add noise for debris and rumble
        noise = 1.5 * (random.random() * 2 - 1) * math.exp(-t * 1.5)
        
        # Create envelope - quick attack, long sustain
        envelope = min(t * 5, 1.0) * math.exp(-t * 0.8)
        
        # Add distortion for power
        mixed = (boom + crack + noise) * envelope
        distorted = math.tanh(mixed * 1.5)  # Soft clipping distortion
        
        value = int(32767 * 0.9 * distorted)
        value = max(-32768, min(32767, value))
        samples.append(value)
    
    return samples


def generate_crystal_shatter_sound(duration: float = 1.5, sample_rate: int = 44100) -> array.array:
    """
    Generate a glass shattering sound effect for capturing the crystal.
    
    Creates a high-frequency, sparkling shatter sound with multiple
    breaking fragments and reverberation.
    """
    num_samples = int(sample_rate * duration)
    samples = array.array("h")
    
    for i in range(num_samples):
        t = i / sample_rate
        
        # Create multiple shattering fragments with different frequencies
        shatter_sound = 0.0
        
        # 8-12 different glass fragments
        num_fragments = 10
        for frag in range(num_fragments):
            # Random frequencies in the glass shatter range (2000-8000Hz)
            frag_freq = 2000.0 + random.random() * 6000.0
            frag_decay = 0.5 + random.random() * 2.0  # Different decay rates
            
            # Each fragment has its own envelope
            frag_envelope = math.exp(-t * frag_decay * 5)
            
            shatter_sound += frag_envelope * math.sin(2 * math.pi * frag_freq * t)
        
        # Add high-frequency noise for the initial break
        break_noise = 2.0 * (random.random() * 2 - 1) * math.exp(-t * 20)
        
        # Add reverberation (echo effect)
        reverb = 0.0
        if i > 11025:  # After 0.25 seconds, add reverb
            reverb_t = (i - 11025) / sample_rate
            reverb = 0.3 * samples[i - 11025] * math.exp(-reverb_t * 5)
        
        # Create overall envelope
        envelope = min(t * 10, 1.0) * math.exp(-t * 1.2)
        
        value = int(32767 * 0.6 * (shatter_sound + break_noise + reverb) * envelope)
        value = max(-32768, min(32767, value))
        samples.append(value)
    
    return samples


def save_sound_effect(samples: array.array, filename: str, sample_rate: int = 44100) -> None:
    """Save sound effect samples to a WAV file."""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())


def generate_all_sound_effects() -> None:
    """Generate all sound effects and save them to files."""
    sound_effects_dir = "client/assets/sounds"
    
    print("Generating sound effects...")
    
    # Generate sliding sound
    sliding_samples = generate_sliding_sound(duration=0.5)
    save_sound_effect(sliding_samples, f"{sound_effects_dir}/sliding.wav")
    print("✓ Generated sliding sound")
    
    # Generate mystery bing sound
    bing_samples = generate_mystery_bing_sound(duration=0.3)
    save_sound_effect(bing_samples, f"{sound_effects_dir}/mystery_bing.wav")
    print("✓ Generated mystery bing sound")
    
    # Generate generator explosion sound
    explosion_samples = generate_generator_explosion_sound(duration=1.2)
    save_sound_effect(explosion_samples, f"{sound_effects_dir}/generator_explosion.wav")
    print("✓ Generated generator explosion sound")
    
    # Generate crystal shatter sound
    shatter_samples = generate_crystal_shatter_sound(duration=1.5)
    save_sound_effect(shatter_samples, f"{sound_effects_dir}/crystal_shatter.wav")
    print("✓ Generated crystal shatter sound")
    
    print(f"All sound effects generated and saved to {sound_effects_dir}/")


if __name__ == "__main__":
    generate_all_sound_effects()
