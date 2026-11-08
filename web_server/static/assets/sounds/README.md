# Game Sound Effects

Sound effects for Race to the Crystal, served by the web server at
`/static/assets/sounds/` and loaded by `static/audio_manager.js`.

## Files

- `sliding.wav` — token movement / deploy
- `flushing.wav` — attack (the "flush")
- `mystery_bing.wav` — mystery square landing
- `generator_explosion.wav` — generator capture
- `crystal_shatter.wav` — crystal capture / win
- `fog_horn.wav` — entering the crystal fog event
- `ghost.wav` — ghost/teleport mystery event
- `lightning.wav` — lightning mystery event
- `whoosh.wav` — generic whoosh

## Custom Sound Effects

To use your own effects:

1. Replace the WAV files in this directory, keeping the same filenames
2. Use 16-bit PCM WAV at 44100 Hz, mono
