# Graphics Testing Skill

Test the Race to the Crystal game rendering in both 2D and 3D modes by taking internal screenshots.

## When to Use

Use this skill when:
- Verifying rendering after code changes
- Debugging graphics issues
- Testing both 2D and 3D rendering modes
- Validating camera configurations
- Checking if visual elements render correctly

## How It Works

This skill creates a test script that:
1. Initializes a full game state with players, tokens, generators, and crystal
2. Runs the game in arcade
3. Takes internal screenshots using `arcade.get_image()`
4. Saves screenshots to `/tmp/` for review
5. Tests both 2D mode and 3D mode

## Important Notes

- **Always use internal screenshots**: Use `arcade.get_image()` from within the game loop, NOT external tools like `maim` or `scrot`
- **External screenshots show black**: The `maim` command captures the window before rendering completes, showing only black screens
- **Frame timing**: Wait ~30 frames before capturing to ensure rendering is stable
- **Display required**: Tests must run with `DISPLAY=:0` set

## Usage Examples

### Test 2D Rendering

Creates a test that captures 2D mode after 30 frames:

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/home/tluker/repos/python/race-to-the-crystal')

import arcade
from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from shared.enums import PlayerColor
from shared.constants import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
from client.game_window import GameWindow

# Create game state
game_state = GameState()
game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
game_state.add_player("p2", "Player 2", PlayerColor.MAGENTA)
game_state.start_game()

# Initialize generators
generator_positions = game_state.board.get_generator_positions()
for i, pos in enumerate(generator_positions):
    generator = Generator(id=i, position=pos)
    game_state.generators.append(generator)

# Initialize crystal
crystal_pos = game_state.board.get_crystal_position()
game_state.crystal = Crystal(position=crystal_pos)

# Create window
window = GameWindow(game_state, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
window.setup()

print(f"Testing 2D mode (camera_mode: {window.camera_mode})")

frame_count = [0]
original_draw = window.on_draw

def new_draw():
    frame_count[0] += 1
    original_draw()

    if frame_count[0] == 30:
        print(f"Frame {frame_count[0]}: Saving 2D screenshot...")
        image = arcade.get_image()
        image.save('/tmp/game_2d_test.png')
        print("Screenshot saved to /tmp/game_2d_test.png")
        arcade.exit()

window.on_draw = new_draw
arcade.run()
```

### Test 3D Rendering

Same structure but switches to 3D mode:

```python
# ... (same setup as above) ...

window = GameWindow(game_state, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
window.setup()

# Switch to 3D mode
window.camera_mode = "3D"

print(f"Testing 3D mode")
print(f"Camera position: {window.camera_3d.position}")
print(f"Camera pitch: {window.camera_3d.pitch}, yaw: {window.camera_3d.yaw}")

# ... (same screenshot code as above, save to /tmp/game_3d_test.png) ...
```

### Test with Custom Camera Position

For 3D debugging, position the camera manually:

```python
import numpy as np
from shared.constants import CELL_SIZE

# ... (setup code) ...

window.camera_mode = "3D"

# Position camera at center of board, high up, looking down
window.camera_3d.position = np.array([12 * CELL_SIZE, 12 * CELL_SIZE, 100.0], dtype=np.float32)
window.camera_3d.pitch = -60.0  # Looking down
window.camera_3d.yaw = 45.0     # Rotated for better view

# ... (take screenshot) ...
```

## Running Tests

Always run with DISPLAY set and use `uv run`:

```bash
DISPLAY=:0 uv run python /tmp/test_graphics.py
```

## What to Check in Screenshots

### 2D Mode Should Show:
- Cyan wireframe grid (24x24 cells)
- Yellow generator squares (4 corners of quadrants)
- Cyan mystery square circles
- Magenta crystal diamond (center)
- Player tokens in starting corners (cyan and magenta hexagons)
- HUD showing "Player 1's Turn", phase, and instructions

### 3D Mode Should Show:
- 3D wireframe grid walls (transparent)
- Generators as wireframe cubes (orange glow)
- Crystal as wireframe diamond
- Mystery squares as wireframe cylinders
- Tokens as 3D hexagonal prisms
- HUD (same as 2D)

## Common Issues

### Black Screenshot from External Tools
**Problem**: Using `maim` or external screenshot tools shows black screen
**Solution**: Always use `arcade.get_image()` from within the game loop

### 3D Mode Shows Nothing
**Check**:
- Camera position is reasonable (not at far clipping plane)
- Camera height is above wall height (>50.0)
- Clipping planes include geometry (near < geometry < far)
- Shader compiled successfully (check for error messages)

### Geometry Outside View Frustum
**Debug**:
- Print camera position, pitch, yaw
- Check projection and view matrices for NaN/Inf
- Verify board dimensions vs clipping planes
- Test with simplified camera position (center, looking down)

## Output

Screenshots saved to:
- `/tmp/game_2d_test.png` - 2D mode rendering
- `/tmp/game_3d_test.png` - 3D mode rendering

Review these images to verify rendering is working correctly.
