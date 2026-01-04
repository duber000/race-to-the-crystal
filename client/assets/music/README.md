This directory contains background music files for the game.

Currently, the game looks for: `techno.mp3` or `techno.wav`

## Auto-Generated Music

The game now automatically generates an enhanced techno track on startup if no music file is found. The generated track includes:

- **Powerful bass drum kicks** with four-on-the-floor patterns
- **Hi-hat patterns** with increasing complexity
- **Synth bassline** with filter sweeps and harmonics
- **Melodic synth arpeggios** that build throughout the track
- **Crystal-inspired arpeggios** representing the crystal's energy
- **Techno synth leads** with distortion and filter effects
- **Generator hums** (separate tracks) that pulse at different rates
- **Crystal resonance** that builds over time

The music is generated using Python's standard library and doesn't require external audio files.

## Music Structure

The track follows a classic techno structure:
- **Intro**: Sparse rhythm, minimal synths
- **Buildup 1**: Building intensity, adding layers
- **Drop**: Full power, all elements active
- **Buildup 2**: More complex patterns, building tension
- **Final Drop**: Maximum intensity, all elements at full power
- **Outro**: Gradual fade-out

## Generator Hums

The game generates separate hum tracks for each of the 4 generators:
- `generator_0_hum.wav` - Generator 1 (A2, slow pulse)
- `generator_1_hum.wav` - Generator 2 (A#2, medium-slow pulse)
- `generator_2_hum.wav` - Generator 3 (B2, medium-fast pulse)
- `generator_3_hum.wav` - Generator 4 (C3, fast pulse)

These hums are played when generators are active in-game and stop when generators are captured.

## Crystal Connection

The music now features crystal-inspired elements:
- **Crystal arpeggios**: High, ethereal notes that shimmer and build
- **Crystal resonance**: A harmonic layer that grows stronger as the game progresses
- **Ethereal harmonics**: Multiple octaves and harmonics for a magical, crystalline sound

## Custom Music

If you want to use your own music:
1. Place your techno music file named `techno.mp3` in this directory
2. Supported formats: MP3, WAV, OGG, FLAC
3. The music will loop automatically during gameplay
4. Recommended: Use royalty-free techno/electronic music with a BPM around 128

Music Controls:
- Press `M` to toggle music on/off

Recommended music sources:
- https://freemusicarchive.org/
- https://www.soundhelix.com/
- https://opengameart.org/

## Technical Details

- **BPM**: 128 (standard techno tempo)
- **Key**: A minor (dark, techno feel)
- **Structure**: 4-measure sections with progressive buildup
- **Processing**: Techno-style distortion, filter sweeps, and soft clipping

