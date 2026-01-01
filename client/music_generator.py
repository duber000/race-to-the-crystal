"""
Generate a simple techno-style background music track using Python's standard library.
"""

import array
import math
import random
import wave
import os
import subprocess
from typing import List


class TechnoMusicGenerator:
    """Generate a dynamic techno beat with multiple layers and variations."""

    def __init__(self, sample_rate: int = 44100, duration: float = 30.0):
        self.sample_rate = sample_rate
        self.duration = duration
        self.num_samples = int(sample_rate * duration)
        self.bpm = 128
        self.beat_duration = 60 / self.bpm
        self.measure_duration = self.beat_duration * 4

    def _generate_sine_wave(
        self, frequency: float, duration: float, amplitude: float = 0.5
    ) -> array.array:
        """Generate a sine wave."""
        num_samples = int(self.sample_rate * duration)
        samples = array.array("h")
        for i in range(num_samples):
            t = i / self.sample_rate
            value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t))
            samples.append(value)
        return samples

    def _generate_square_wave(
        self, frequency: float, duration: float, amplitude: float = 0.3
    ) -> array.array:
        """Generate a square wave (techno-style synth)."""
        num_samples = int(self.sample_rate * duration)
        period = self.sample_rate // frequency
        samples = array.array("h")
        for i in range(num_samples):
            if (i % period) < (period // 2):
                value = int(amplitude * 32767)
            else:
                value = int(-amplitude * 32767)
            samples.append(value)
        return samples

    def _generate_kick(self, duration: float = 0.3) -> array.array:
        """Generate a POWERFUL bass drum kick."""
        num_samples = int(self.sample_rate * duration)
        samples = array.array("h")
        for i in range(num_samples):
            t = i / self.sample_rate
            # Lower frequency for deeper, more powerful kick
            frequency = 120 * math.exp(-t * 12)
            # MUCH more amplitude for serious punch
            amplitude = 0.95 * math.exp(-t * 8)
            # Add some click/attack at the beginning for punch
            click = 0.3 * math.exp(-t * 100) * math.sin(2 * math.pi * 2000 * t)
            value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t) + click * 32767)
            # Clamp to valid range
            value = max(-32768, min(32767, value))
            samples.append(value)
        return samples

    def _generate_hat(self, duration: float = 0.08) -> array.array:
        """Generate a hi-hat (white noise burst)."""
        num_samples = int(self.sample_rate * duration)
        samples = array.array("h")
        for i in range(num_samples):
            t = i / self.sample_rate
            amplitude = 0.5 * math.exp(-t * 40)  # Louder and longer
            value = int(amplitude * 32767 * (random.random() * 2 - 1))
            samples.append(value)
        return samples

    def _generate_synth_bass(
        self, notes: List[float], duration: float = 0.5
    ) -> array.array:
        """Generate a bassline with filter sweep using saw-like waves."""
        total_samples = int(self.sample_rate * duration)
        samples_per_note = total_samples // len(notes)
        samples = array.array("h")
        for note_idx, freq in enumerate(notes):
            note_samples = int(self.sample_rate * (duration / len(notes)))
            for i in range(note_samples):
                t = i / self.sample_rate
                # Add envelope to each note
                envelope = math.exp(-t * 3)
                # Layered synth sound with harmonics for richer tone
                fundamental = math.sin(2 * math.pi * freq * t)
                harmonic = 0.4 * math.sin(2 * math.pi * freq * 2 * t)
                subharmonic = 0.2 * math.sin(2 * math.pi * freq * 0.5 * t)  # Deep sub-bass
                value = int(0.85 * 32767 * (fundamental + harmonic + subharmonic) * envelope)
                value = max(-32768, min(32767, value))
                samples.append(value)
        return samples
    
    def _generate_arpeggio(
        self, notes: List[float], duration: float = 0.5, speed: int = 4
    ) -> array.array:
        """Generate a fast arpeggio pattern."""
        samples = array.array("h")
        total_samples = int(self.sample_rate * duration)
        samples_per_note = total_samples // (len(notes) * speed)

        for _ in range(speed):
            for freq in notes:
                for i in range(samples_per_note):
                    t = i / self.sample_rate
                    # Decay envelope for staccato feel
                    envelope = math.exp(-t * 8)
                    # Add harmonics for richer electronic sound
                    fundamental = math.sin(2 * math.pi * freq * t)
                    harmonic = 0.4 * math.sin(2 * math.pi * freq * 1.5 * t)
                    value = int(0.5 * 32767 * (fundamental + harmonic) * envelope)  # Doubled amplitude
                    samples.append(value)
        return samples

    def _generate_generator_hums(self, duration: float) -> array.array:
        """Generate 4 interleaving electric hums representing the generators."""
        num_samples = int(self.sample_rate * duration)
        samples = array.array("h")

        # 4 generator frequencies - slightly detuned for phasing effect
        gen_freqs = [
            110.0,   # A2 - Generator 1
            116.5,   # A#2 - Generator 2 (slightly sharp)
            123.5,   # B2 - Generator 3
            130.8,   # C3 - Generator 4
        ]

        for i in range(num_samples):
            t = i / self.sample_rate

            # Create pulsing pattern - each generator pulses at different rates
            pulse1 = 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t)  # Slow pulse
            pulse2 = 0.5 + 0.5 * math.sin(2 * math.pi * 0.7 * t)  # Medium-slow pulse
            pulse3 = 0.5 + 0.5 * math.sin(2 * math.pi * 0.9 * t)  # Medium-fast pulse
            pulse4 = 0.5 + 0.5 * math.sin(2 * math.pi * 1.1 * t)  # Fast pulse

            # Generate each generator hum with harmonics
            hum1 = pulse1 * (math.sin(2 * math.pi * gen_freqs[0] * t) +
                            0.3 * math.sin(2 * math.pi * gen_freqs[0] * 2 * t))
            hum2 = pulse2 * (math.sin(2 * math.pi * gen_freqs[1] * t) +
                            0.3 * math.sin(2 * math.pi * gen_freqs[1] * 2 * t))
            hum3 = pulse3 * (math.sin(2 * math.pi * gen_freqs[2] * t) +
                            0.3 * math.sin(2 * math.pi * gen_freqs[2] * 2 * t))
            hum4 = pulse4 * (math.sin(2 * math.pi * gen_freqs[3] * t) +
                            0.3 * math.sin(2 * math.pi * gen_freqs[3] * 2 * t))

            # Mix all 4 generators
            mixed_hum = (hum1 + hum2 + hum3 + hum4) / 4.0

            # Convert to sample value with HIGH volume so it's clearly audible
            value = int(0.6 * 32767 * mixed_hum)  # Much louder!
            value = max(-32768, min(32767, value))
            samples.append(value)

        return samples

    def generate_track(self) -> array.array:
        """Generate a full techno track with intro, buildup, drop, and outro."""
        full_track = array.array("h")
        
        num_measures = int(self.duration / self.measure_duration)
        
        # Define track structure with 4-measure sections
        intro_measures = 4
        buildup1_measures = 4
        drop_measures = 4
        buildup2_measures = 4
        final_drop_measures = 4
        outro_measures = max(1, num_measures - (intro_measures + buildup1_measures + drop_measures + buildup2_measures + final_drop_measures))
        
        section_order = [
            ("intro", intro_measures),
            ("buildup1", buildup1_measures),
            ("drop", drop_measures),
            ("buildup2", buildup2_measures),
            ("final_drop", final_drop_measures),
            ("outro", outro_measures),
        ]
        
        measure_idx = 0
        for section_name, section_measures in section_order:
            for local_measure in range(section_measures):
                self._add_measure(full_track, measure_idx, section_name, measure_idx % 4)
                measure_idx += 1
                if len(full_track) >= self.num_samples:
                    break
            if len(full_track) >= self.num_samples:
                break
        
        # Trim to exact duration
        return full_track[:self.num_samples]
    
    def _add_measure(self, track: array.array, measure_idx: int, section: str, pattern_offset: int) -> None:
        """Add a single measure to the track based on the section type."""
        measure_start = len(track)

        # Initialize measure with bass (NO generator hums - they're separate tracks)
        bass_patterns = [
            [55.0, 55.0, 82.4, 55.0],      # A1, E2, A1
            [55.0, 73.4, 65.4, 55.0],      # A1, D#2, C2, A1
            [49.0, 55.0, 73.4, 55.0],      # B0, A1, D#2, A1
            [55.0, 55.0, 98.0, 55.0],      # A1, G#2, A1
        ]
        bass_pattern = bass_patterns[pattern_offset % len(bass_patterns)]
        bass = self._generate_synth_bass(bass_pattern, self.measure_duration)
        track.extend(bass)
        
        # Layer drums with variation based on section - ALL WITH POWERFUL KICKS
        if section == "intro":
            # Sparse kicks, minimal hats
            self._layer_drum(track, measure_start, "kick", [0, 2], 0.30)  # Every other beat
            self._layer_drum(track, measure_start, "hat", [1, 1.5, 3, 3.5], 0.08)

        elif section == "buildup1":
            # More kicks, building rhythm
            self._layer_drum(track, measure_start, "kick", [0, 1, 2, 3], 0.30)  # Four on the floor!
            self._layer_drum(track, measure_start, "hat", [0.5, 1.5, 2.5, 3.5], 0.08)

        elif section == "drop":
            # POWERFUL four-on-the-floor kick pattern
            self._layer_drum(track, measure_start, "kick", [0, 1, 2, 3], 0.35)  # Strong kicks!
            self._layer_drum(track, measure_start, "hat", [0.5, 1.5, 2.5, 3.5], 0.10)

        elif section == "buildup2":
            # Building intensity
            self._layer_drum(track, measure_start, "kick", [0, 1, 2, 3], 0.32)
            self._layer_drum(track, measure_start, "hat", [0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75], 0.10)

        elif section == "final_drop":
            # MAXIMUM POWER - dense kick pattern
            self._layer_drum(track, measure_start, "kick", [0, 1, 2, 3], 0.38)  # BOOM BOOM BOOM BOOM
            self._layer_drum(track, measure_start, "hat", [0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75], 0.12)

        elif section == "outro":
            # Fade out rhythm
            self._layer_drum(track, measure_start, "kick", [0, 2], 0.25)
            self._layer_drum(track, measure_start, "hat", [1, 3], 0.06)
        
        # Layer synth elements that vary by section
        if section == "intro":
            # Minimal synth intro
            synth_notes = [220.0, 246.9]  # A3, B3
            synth = self._generate_arpeggio(synth_notes, self.measure_duration, speed=2)
            self._blend_layer(track, measure_start, synth, 0.25)

        elif section == "buildup1":
            # Building arpeggio
            synth_notes = [220.0, 246.9, 277.2]  # A3, B3, C#4
            synth = self._generate_arpeggio(synth_notes, self.measure_duration, speed=3)
            self._blend_layer(track, measure_start, synth, 0.35)

        elif section in ["drop", "final_drop"]:
            # Lead synth with more intensity
            synth_notes = [220.0, 246.9, 277.2, 293.7]  # A3, B3, C#4, D4
            synth = self._generate_arpeggio(synth_notes, self.measure_duration, speed=4)
            self._blend_layer(track, measure_start, synth, 0.45)

        elif section == "buildup2":
            # Fast arpeggios
            synth_notes = [220.0, 246.9, 277.2, 293.7, 329.6]  # A3-E4
            synth = self._generate_arpeggio(synth_notes, self.measure_duration, speed=6)
            self._blend_layer(track, measure_start, synth, 0.42)

        elif section == "outro":
            # Fade out synth
            synth_notes = [220.0, 246.9]
            synth = self._generate_arpeggio(synth_notes, self.measure_duration, speed=1)
            self._blend_layer(track, measure_start, synth, 0.15)
    
    def _layer_drum(self, track: array.array, measure_start: int, drum_type: str, beat_offsets: List[float], kick_duration: float) -> None:
        """Add drum hits at specific beat offsets within a measure."""
        for beat_offset in beat_offsets:
            beat_sample = int(beat_offset * self.beat_duration * self.sample_rate)
            start_sample = measure_start + beat_sample

            if drum_type == "kick":
                drum = self._generate_kick(kick_duration)
            else:  # "hat"
                drum = self._generate_hat(0.08)

            for i, sample in enumerate(drum):
                if start_sample + i < len(track):
                    track[start_sample + i] = self._saturate_add(track[start_sample + i], sample, 0.85)
    
    def _blend_layer(self, track: array.array, start: int, layer: array.array, volume: float) -> None:
        """Blend a synth layer into the track with volume control."""
        for i, sample in enumerate(layer):
            idx = start + i
            if idx < len(track):
                track[idx] = self._saturate_add(track[idx], int(sample * volume), 0.85)
    
    def _saturate_add(self, original: int, addition: int, blend: float) -> int:
        """Add with soft clipping to prevent distortion."""
        mixed = int(original * (1 - blend) + addition * blend)
        # Soft clipping using tanh-like behavior
        if mixed > 32767:
            mixed = int(32767 * math.tanh(mixed / 32767))
        elif mixed < -32768:
            mixed = int(-32768 * math.tanh(-mixed / 32768))
        return mixed

    def save_to_wav(self, filename: str):
        """Save the generated track to a WAV file."""
        samples = self.generate_track()
        with wave.open(filename, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(samples.tobytes())
        print(f"Generated techno track: {filename}")


def generate_single_generator_hum(generator_id: int, duration: float, sample_rate: int = 44100) -> array.array:
    """
    Generate a single generator hum track.

    Args:
        generator_id: Which generator (0-3)
        duration: Duration in seconds
        sample_rate: Sample rate

    Returns:
        Audio samples for just this generator's hum
    """
    num_samples = int(sample_rate * duration)
    samples = array.array("h")

    # 4 generator frequencies - slightly detuned for phasing effect
    gen_freqs = [110.0, 116.5, 123.5, 130.8]
    pulse_rates = [0.5, 0.7, 0.9, 1.1]

    freq = gen_freqs[generator_id]
    pulse_rate = pulse_rates[generator_id]

    for i in range(num_samples):
        t = i / sample_rate

        # Pulsing pattern
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * pulse_rate * t)

        # Generate hum with harmonics
        hum = pulse * (math.sin(2 * math.pi * freq * t) +
                      0.3 * math.sin(2 * math.pi * freq * 2 * t))

        # Convert to sample value - LOUD so it's very noticeable when it drops
        value = int(0.85 * 32767 * hum)  # Much louder!
        value = max(-32768, min(32767, value))
        samples.append(value)

    return samples


def generate_techno_music(
    output_path: str = "client/assets/music/techno.mp3", duration: float = 30.0
):
    """
    Generate a techno music file with separate generator hum tracks.

    Args:
        output_path: Path where the music file should be saved
        duration: Duration of the track in seconds
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Generate main track (with all generator hums)
    wav_path = output_path.replace(".mp3", ".wav")
    generator = TechnoMusicGenerator(sample_rate=44100, duration=duration)
    generator.save_to_wav(wav_path)

    # Try to convert to MP3 if ffmpeg is available
    try:
        subprocess.run(
            ["ffmpeg", "-i", wav_path, "-y", output_path],
            check=True,
            capture_output=True,
        )
        print(f"Converted to MP3: {output_path}")
        print(f"Kept WAV file as fallback: {wav_path}")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("FFmpeg not found or conversion failed, using WAV format")
        if output_path.endswith(".mp3"):
            print(f"Music saved as: {wav_path}")

    # Generate individual generator hum tracks
    for gen_id in range(4):
        hum_samples = generate_single_generator_hum(gen_id, duration)
        hum_wav_path = f"client/assets/music/generator_{gen_id}_hum.wav"

        with wave.open(hum_wav_path, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(44100)
            wav_file.writeframes(hum_samples.tobytes())

        print(f"Generated generator {gen_id} hum: {hum_wav_path}")


if __name__ == "__main__":
    generate_techno_music(duration=30.0)
