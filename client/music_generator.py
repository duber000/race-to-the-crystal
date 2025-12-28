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
    """Generate a simple techno beat programmatically."""

    def __init__(self, sample_rate: int = 44100, duration: float = 30.0):
        self.sample_rate = sample_rate
        self.duration = duration
        self.num_samples = int(sample_rate * duration)

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

    def _generate_kick(self, duration: float = 0.2) -> array.array:
        """Generate a bass drum kick."""
        num_samples = int(self.sample_rate * duration)
        samples = array.array("h")
        for i in range(num_samples):
            t = i / self.sample_rate
            frequency = 150 * math.exp(-t * 15)
            amplitude = 0.8 * math.exp(-t * 10)
            value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * t))
            samples.append(value)
        return samples

    def _generate_hat(self, duration: float = 0.05) -> array.array:
        """Generate a hi-hat (white noise burst)."""
        num_samples = int(self.sample_rate * duration)
        samples = array.array("h")
        for i in range(num_samples):
            t = i / self.sample_rate
            amplitude = 0.2 * math.exp(-t * 50)
            value = int(amplitude * 32767 * (random.random() * 2 - 1))
            samples.append(value)
        return samples

    def _generate_synth_bass(
        self, notes: List[float], duration: float = 0.5
    ) -> array.array:
        """Generate a simple bassline using saw-like waves."""
        total_samples = int(self.sample_rate * duration)
        samples_per_note = total_samples // len(notes)
        samples = array.array("h")
        for freq in notes:
            note_samples = int(self.sample_rate * (duration / len(notes)))
            for i in range(note_samples):
                t = i / self.sample_rate
                value = int(0.4 * 32767 * math.sin(2 * math.pi * freq * t))
                samples.append(value)
        return samples

    def generate_track(self) -> array.array:
        """Generate a full techno track."""
        full_track = array.array("h")

        bpm = 128
        beat_duration = 60 / bpm
        measure = beat_duration * 4

        num_measures = int(self.duration / measure)

        for measure_idx in range(num_measures):
            measure_start = measure_idx * measure

            # Bassline pattern (simple repeating notes)
            bass_notes = [55.0, 55.0, 65.4, 55.0]  # A1, C2, A1
            bass = self._generate_synth_bass(bass_notes, measure)
            full_track.extend(bass)

            # Kick drum on 1 and 3
            for beat in [0, 2]:
                kick = self._generate_kick(0.1)
                start_sample = int(
                    (measure_start + beat * beat_duration) * self.sample_rate
                )
                for i, sample in enumerate(kick):
                    if start_sample + i < len(full_track):
                        full_track[start_sample + i] = int(
                            full_track[start_sample + i] * 0.5 + sample * 0.5
                        )

            # Hi-hat on offbeats
            for beat in [1, 2, 3]:
                hat = self._generate_hat(0.03)
                start_sample = int(
                    (measure_start + beat * beat_duration) * self.sample_rate
                )
                for i, sample in enumerate(hat):
                    if start_sample + i < len(full_track):
                        full_track[start_sample + i] = int(
                            full_track[start_sample + i] * 0.8 + sample * 0.2
                        )

            # Add subtle synth melody in second half of track
            if measure_idx > num_measures // 2:
                synth_notes = [220.0, 246.9, 277.2, 220.0]  # A3, B3, C#3, A3
                synth = self._generate_square_wave(
                    synth_notes[measure_idx % 4], beat_duration, 0.15
                )
                start_sample = int(measure_start * self.sample_rate)
                for i, sample in enumerate(synth):
                    if start_sample + i < len(full_track):
                        full_track[start_sample + i] = int(
                            full_track[start_sample + i] * 0.9 + sample * 0.1
                        )

        return full_track

    def save_to_wav(self, filename: str):
        """Save the generated track to a WAV file."""
        samples = self.generate_track()
        with wave.open(filename, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(samples.tobytes())
        print(f"Generated techno track: {filename}")


def generate_techno_music(
    output_path: str = "client/assets/music/techno.mp3", duration: float = 30.0
):
    """
    Generate a techno music file.

    Args:
        output_path: Path where the music file should be saved
        duration: Duration of the track in seconds
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Generate WAV file
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
        # Remove WAV file
        os.remove(wav_path)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("FFmpeg not found or conversion failed, using WAV format")
        # Rename WAV to expected filename
        if output_path.endswith(".mp3"):
            os.rename(wav_path, wav_path.replace(".mp3", ".wav"))
            print(f"Music saved as: {wav_path.replace('.mp3', '.wav')}")


if __name__ == "__main__":
    generate_techno_music(duration=30.0)
