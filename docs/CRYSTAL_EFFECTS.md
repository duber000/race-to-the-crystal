# Crystal Effects System

The crystal effects system adds strategic debuff mechanics to Race to the Crystal. Players can be afflicted with crystal-based effects that alter their perception of the game board.

## Overview

Two types of crystal effects can be applied to players:

1. **Fog of War** - Players cannot see enemy tokens
2. **Phantom Enemies** - Players see illusory enemy tokens that don't actually exist

Effects last for 4 turns by default and can be reduced by capturing generators (1 turn reduction per generator captured).

## Architecture

The crystal effects system is built with the following components:

### Core Classes

- **`CrystalEffect`** (enum) - Defines effect types (FOG_OF_WAR, PHANTOM_ENEMIES)
- **`ActiveEffect`** - Represents a single active effect on a player
- **`PhantomToken`** - Represents an illusory token shown to a player
- **`PlayerEffects`** - Tracks all active effects for a specific player
- **`CrystalEffectsManager`** - Central manager for all crystal effects

### Integration Points

The system integrates with:
- **`GameState`** - Main game state container includes `crystal_effects` manager
- **`GeneratorManager`** - Captures reduce effect durations
- **Serialization** - Effects persist across save/load

## Usage

### Applying Effects

```python
from shared.enums import CrystalEffect

# Apply fog of war to a player
game_state.apply_crystal_effect(player_id, CrystalEffect.FOG_OF_WAR)

# Apply phantom enemies with custom duration
game_state.apply_crystal_effect(
    player_id,
    CrystalEffect.PHANTOM_ENEMIES,
    duration=3  # Lasts 3 turns
)
```

### Getting Visible Tokens for a Player

```python
# Get tokens visible to a specific player
visible_tokens, phantom_tokens = game_state.get_visible_tokens_for_player(player_id)

# visible_tokens: List of real Token objects the player can see
# phantom_tokens: List of PhantomToken objects (illusions)
```

### Checking Active Effects

```python
# Check if player has an active effect
effects = game_state.crystal_effects.get_player_effects(player_id)
has_fog = effects.has_effect(CrystalEffect.FOG_OF_WAR)
has_phantoms = effects.has_effect(CrystalEffect.PHANTOM_ENEMIES)

# Get effect details
fog_effect = effects.get_effect(CrystalEffect.FOG_OF_WAR)
if fog_effect:
    turns_remaining = fog_effect.turns_remaining
    print(f"Fog of war active for {turns_remaining} more turns")
```

### Effect Duration Reduction

Effect durations are automatically reduced when a player captures a generator:

```python
# This happens automatically in GameState._update_generators_and_crystal()
# When a generator is captured:
newly_disabled, capturing_players = GeneratorManager.update_all_generators(...)
for gen_id, player_id in capturing_players.items():
    game_state.crystal_effects.reduce_effect_durations_for_generator_capture(player_id)
```

## Effect Behavior

### Fog of War

When a player has Fog of War active:
- They can only see their own tokens
- Enemy tokens are completely hidden
- Generator and crystal positions are still visible
- Phantom tokens (if also active) are visible

### Phantom Enemies

When a player has Phantom Enemies active:
- They see illusory enemy tokens at random positions
- Phantoms appear to belong to other players
- Phantoms have random health values (4, 6, 8, or 10)
- Phantoms regenerate when the effect is reapplied
- Phantoms disappear when the effect expires

## Configuration Constants

```python
# In shared/constants.py
CRYSTAL_EFFECT_INITIAL_DURATION = 4  # Effects last 4 turns
CRYSTAL_EFFECT_REDUCTION_PER_GENERATOR = 1  # -1 turn per generator
PHANTOM_ENEMIES_COUNT = 3  # Number of phantom tokens per player
```

## Client Integration

To integrate crystal effects into the game client/UI:

### Rendering Tokens

```python
# In your rendering code
player_id = current_viewing_player_id
visible_tokens, phantoms = game_state.get_visible_tokens_for_player(player_id)

# Render real visible tokens
for token in visible_tokens:
    render_token(token)

# Render phantom tokens (could use different visual style)
for phantom in phantoms:
    render_phantom_token(phantom)
```

### UI Indicators

```python
# Show active effects in UI
effects = game_state.crystal_effects.get_player_effects(player_id)

if effects.has_effect(CrystalEffect.FOG_OF_WAR):
    fog = effects.get_effect(CrystalEffect.FOG_OF_WAR)
    show_ui_indicator("Fog of War", fog.turns_remaining)

if effects.has_effect(CrystalEffect.PHANTOM_ENEMIES):
    phantom = effects.get_effect(CrystalEffect.PHANTOM_ENEMIES)
    show_ui_indicator("Phantom Enemies", phantom.turns_remaining)
```

## Example Game Flow

```python
# Game setup
game_state = GameState.create_game(2)
game_state.start_game()

# Apply crystal effects to player 0
player_0 = list(game_state.players.keys())[0]
game_state.apply_crystal_effect(player_0, CrystalEffect.FOG_OF_WAR)
game_state.apply_crystal_effect(player_0, CrystalEffect.PHANTOM_ENEMIES)

# Player 0's view is now restricted
visible, phantoms = game_state.get_visible_tokens_for_player(player_0)
print(f"Player 0 sees {len(visible)} real tokens and {len(phantoms)} phantoms")

# Player 0 captures a generator
# (This happens through normal game flow)
# Effect durations are automatically reduced by 1 turn

# Check remaining duration
effects = game_state.crystal_effects.get_player_effects(player_0)
fog = effects.get_effect(CrystalEffect.FOG_OF_WAR)
print(f"Fog of war now has {fog.turns_remaining} turns remaining")
```

## Serialization

Crystal effects are automatically serialized with game state:

```python
# Save game
data = game_state.to_dict()
json_str = game_state.to_json()

# Load game
restored = GameState.from_dict(data)
# or
restored = GameState.from_json(json_str)

# Effects are preserved
effects = restored.crystal_effects.get_player_effects(player_id)
assert effects.has_effect(CrystalEffect.FOG_OF_WAR)
```

## Testing

Comprehensive unit tests are available in `tests/test_crystal_effects.py`:

```bash
# Run crystal effects tests
uv run pytest tests/test_crystal_effects.py -v

# Or using make
make test-specific FILE=tests/test_crystal_effects.py
```

The test suite covers:
- Effect creation and lifecycle
- Duration reduction mechanics
- Fog of war visibility filtering
- Phantom token generation
- Serialization/deserialization
- GameState integration

## Design Decisions

### Why separate PhantomToken from Token?

Phantom tokens are separate from real tokens because:
- They don't exist in the game state
- They can't be interacted with
- They're player-specific (different players may see different phantoms)
- They use negative IDs to avoid collision with real tokens

### Why reduce effects on generator capture?

This creates strategic depth:
- Capturing generators has multiple benefits (crystal requirement reduction + effect removal)
- Players under effects are incentivized to fight for generators
- Creates interesting risk/reward decisions

### Why 4 turns initial duration?

With 4 turns initial duration and 1 turn reduction per generator:
- 4 generators = complete removal of effects
- Provides meaningful but not overwhelming debuff
- Allows counterplay without making effects useless
