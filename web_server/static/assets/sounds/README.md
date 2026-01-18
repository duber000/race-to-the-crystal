# Game Sound Effects

This directory contains generated sound effects for Race to the Crystal.

## Available Sound Effects

### 1. `sliding.wav`
- **Purpose**: Token movement sliding sound
- **Description**: A whooshing, sliding sound that represents tokens moving across the board
- **Characteristics**: Frequency sweep from 1000Hz to 200Hz, with harmonics and texture
- **Duration**: 0.5 seconds

### 2. `mystery_bing.wav`
- **Purpose**: Mystery square landing sound
- **Description**: A coin-like metallic "bing" sound for landing on mystery squares
- **Characteristics**: 1500Hz main frequency with multiple harmonics for metallic quality
- **Duration**: 0.3 seconds

### 3. `generator_explosion.wav`
- **Purpose**: Generator capture sound
- **Description**: A powerful explosion sound for when generators are captured
- **Characteristics**: Low-frequency boom (50-100Hz) with high-frequency crack and distortion
- **Duration**: 1.2 seconds

### 4. `crystal_shatter.wav`
- **Purpose**: Crystal capture sound
- **Description**: Glass shattering sound for capturing the crystal
- **Characteristics**: Multiple high-frequency fragments (2000-8000Hz) with reverb
- **Duration**: 1.5 seconds

## Sound Effects Generation

All sound effects are procedurally generated using the `client/sound_effects.py` module.

To regenerate sound effects:
```bash
uv run client/sound_effects.py
```

## Integration with Game

Sound effects are managed by the `AudioManager` class and triggered by game events:

- **Sliding sound**: Played when tokens move
- **Mystery bing**: Played when landing on mystery squares
- **Generator explosion**: Played when generators are captured
- **Crystal shatter**: Played when the crystal is captured

## Volume Control

Sound effects volume is controlled by the `SOUND_EFFECTS_VOLUME` constant in `shared/constants.py`.

## Custom Sound Effects

To use custom sound effects:
1. Replace the WAV files in this directory with your own
2. Keep the same filenames
3. Ensure files are in WAV format, 44100Hz sample rate, 16-bit

## Technical Details

- **Format**: 16-bit PCM WAV files
- **Sample Rate**: 44100Hz
- **Channels**: Mono
- **Volume Range**: 0.0 to 1.0 (controlled by `SOUND_EFFECTS_VOLUME`)

## Sound Design Philosophy

The sound effects are designed to:
- Be distinctive and easily recognizable
- Match the techno/electronic aesthetic of the game
- Provide clear audio feedback for game events
- Not overwhelm the background music
- Have appropriate durations for their events
