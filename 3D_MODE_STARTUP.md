# 3D Mode Startup

## Overview

Added command-line flag `--3d` to start the game directly in 3D mode without needing to press `V` during gameplay.

## Usage

### Start in 3D Mode (2 players)
```bash
uv run race-to-the-crystal --3d 2
```

### Start in 3D Mode (4 players, default)
```bash
uv run race-to-the-crystal --3d
```

### Start in 2D Mode (traditional way)
```bash
uv run race-to-the-crystal
uv run race-to-the-crystal 2
uv run race-to-the-crystal 4
```

## Command-Line Arguments

The game now supports flexible argument parsing:

| Syntax | Behavior |
|--------|----------|
| `race-to-the-crystal` | 4-player game, 2D mode (default) |
| `race-to-the-crystal 2` | 2-player game, 2D mode |
| `race-to-the-crystal --3d` | 4-player game, 3D mode |
| `race-to-the-crystal --3d 2` | 2-player game, 3D mode |
| `race-to-the-crystal 2 --3d` | 2-player game, 3D mode (order doesn't matter) |
| `race-to-the-crystal -3d` | 4-player game, 3D mode (short form) |

## Implementation

Modified `client/client_main.py`:
- Updated argument parser to support `--3d` / `-3d` flags
- Order of arguments doesn't matter
- Unknown arguments are ignored with a warning

**Key Code:**
```python
for arg in sys.argv[1:]:
    if arg == "--3d" or arg == "-3d":
        start_in_3d = True
    else:
        try:
            num_players = int(arg)
        except ValueError:
            print(f"Warning: Unknown argument '{arg}', ignoring")

# ... later in main() ...
if start_in_3d:
    window.camera_mode = "3D"
```

## Testing

To verify 3D mode starts correctly:

```bash
# Test with output
DISPLAY=:0 uv run race-to-the-crystal --3d 2

# Should see:
# Starting 2-player game...
# (Starting in 3D mode)
# ... 
# 3D mode enabled
```

## Features in 3D Mode

When starting in 3D mode, you get:
- ✓ First-person Battlezone-style wireframe view
- ✓ Flowing orange generator-to-crystal lines (visible in certain camera angles)
- ✓ 3D grid wireframe rendering
- ✓ All normal game controls work
- ✓ Can toggle back to 2D with `V` key

## Notes

- The `--3d` flag is case-sensitive (`--3d` works, `--3D` does not)
- Both `-3d` and `--3d` are accepted
- Arguments can be in any order: `--3d 2` or `2 --3d`
- If invalid player count provided, defaults to 4

## Files Modified

- `client/client_main.py` - Added 3D startup support
