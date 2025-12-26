---
name: playtesting
description: Comprehensive game playtesting through automated AI gameplay to verify functionality, find bugs, and test game mechanics. Use when testing Race to the Crystal gameplay, verifying win conditions, testing generators and crystal capture, or debugging game issues.
---

# Playtesting

Automated playtesting for Race to the Crystal game using AI-driven gameplay.

## When to Use
- User asks to "playtest the game"
- User wants to "test gameplay"
- User says "find bugs" or "test for issues"
- User requests "verify game mechanics"
- After implementing new features or bug fixes

## How It Works

### 1. Test Strategy Selection

Choose the appropriate testing approach based on user request:

**Quick Test** (5-10 turns)
- Verify basic functionality
- Check for crashes
- Validate API responses

**Standard Test** (30-50 turns)
- Test core gameplay loop
- Exercise all action types
- Check phase transitions

**Comprehensive Test** (multiple scenarios)
- Test all game mechanics systematically
- Focus on edge cases
- Test win conditions
- Verify resource limits

**Targeted Test** (specific feature)
- Focus on one mechanic (combat, movement, generators, etc.)
- Test edge cases for that feature
- Verify error handling

### 2. Gameplay Execution

Use the AI API to play the game:

```python
from game.game_state import GameState
from game.ai_observation import AIObserver
from game.ai_actions import AIActionExecutor, MoveAction, AttackAction, DeployAction, EndTurnAction
```

**Turn Structure:**
1. Observe game state via `AIObserver.get_game_state()`
2. List available actions via `AIObserver.list_available_actions()`
3. Choose strategic action (prioritize testing target mechanics)
4. Execute via `AIActionExecutor.execute_action()`
5. Check for errors and unexpected behavior
6. Log interesting events

**Strategic Priorities:**
- **Movement Testing**: Move tokens to different board positions, test boundaries
- **Combat Testing**: Engage in battles, verify damage calculations
- **Generator Testing**: Hold generators with 2 tokens for 2+ turns
- **Crystal Testing**: Accumulate tokens at crystal position
- **Deployment Testing**: Deploy all token types, test reserve limits
- **Phase Testing**: Verify MOVEMENT → ACTION transitions

### 3. What to Monitor

**Critical Issues (CRITICAL):**
- Game crashes or exceptions
- Win conditions not triggering
- Game becomes stuck/unplayable
- Core mechanics not working (movement, combat, capture)
- Data corruption or invalid state

**High Priority Issues (HIGH):**
- Incorrect damage calculations
- Phase transitions failing
- Turn management errors
- Tokens not being removed when killed
- Invalid actions being allowed

**Medium Priority Issues (MEDIUM):**
- Unexpected behavior that doesn't break gameplay
- Performance issues
- Unclear error messages
- Minor calculation errors

**Low Priority Issues (LOW):**
- UI/display issues in API responses
- Non-critical edge cases
- Optimization opportunities

### 4. Specific Mechanics to Test

#### Generator Capture
```python
# Test: Deploy 2 tokens at generator, hold for 2 turns
# Expected: Generator becomes disabled
# Watch for: Capture progress, turn counting, multiple players contesting
```

#### Crystal Win Condition
```python
# Test: Hold crystal with required tokens for 3 turns
# Expected: Player wins, game ends
# Watch for: Token counting, turn counting, disabled generator effects
```

#### Combat System
```python
# Test: Attack with various token health values
# Expected: Damage = attacker.health // 2, defender takes damage, attacker takes none
# Watch for: Damage calculation, token destruction, health < 0
```

#### Movement System
```python
# Test: Move tokens with different health values
# Expected: 6hp and 4hp move 2 spaces, others move 1 space
# Watch for: Boundary checking, pathfinding, occupied cells
```

#### Token Deployment
```python
# Test: Deploy all token types, exceed reserve limits
# Expected: Can deploy 5 of each type (10hp, 8hp, 6hp, 4hp)
# Watch for: Reserve counting, position validation, corner restrictions
```

#### Turn Management
```python
# Test: End turn in different phases, pass without action
# Expected: Turn advances to next player, phase resets
# Watch for: Player order, turn number, phase transitions
```

### 5. Reporting Format

After testing, provide a clear report:

```markdown
# Playtesting Report

**Test Type:** [Quick/Standard/Comprehensive/Targeted]
**Duration:** [X turns / Y minutes]
**Date:** [Current date]

## Summary
- ✅ Tests Passed: X
- ❌ Issues Found: Y
- ⚠️ Warnings: Z

## Test Results

### [Mechanic Name]
**Status:** ✅ PASS / ❌ FAIL / ⚠️ WARNING
**Details:** [What was tested and what happened]

### Critical Issues Found
1. **[Issue Title]** (CRITICAL)
   - Location: [file:line]
   - Description: [What's wrong]
   - Reproduction: [How to reproduce]
   - Impact: [Why this matters]

### Recommendations
- [Action items to fix issues]
- [Suggested improvements]
- [Areas needing more testing]
```

### 6. Example Usage Patterns

**Pattern 1: Full Game Playtest**
```python
# Create game, play 50 turns using random valid actions
# Log all errors, track game state health
# Report on: crashes, stuck states, win conditions
```

**Pattern 2: Feature-Specific Test**
```python
# Set up specific scenario (e.g., tokens at generator)
# Execute targeted actions to test one mechanic
# Verify expected behavior occurs
```

**Pattern 3: Edge Case Hunting**
```python
# Try to break the game with unusual actions
# Test boundary conditions (board edges, 0 health, etc.)
# Attempt invalid operations
# Verify error handling
```

**Pattern 4: Win Condition Verification**
```python
# Manually set up near-win scenario
# Execute actions to trigger win
# Verify game ends correctly
```

## Testing Best Practices

1. **Always use try/except** to catch and report exceptions
2. **Log turn-by-turn state** for debugging
3. **Test both valid and invalid actions** to verify validation
4. **Verify state consistency** after each action
5. **Test multiplayer scenarios** with 2+ players
6. **Check edge cases** (empty reserves, board boundaries, etc.)
7. **Validate API responses** match expected format
8. **Track performance** for long games

## Files to Use

- **Main test script**: `test_gameplay_flaws.py`
- **Game state**: `game/game_state.py`
- **AI observer**: `game/ai_observation.py`
- **AI executor**: `game/ai_actions.py`
- **Game mechanics**: `game/generator.py`, `game/crystal.py`, `game/combat.py`, `game/movement.py`

## Common Testing Scenarios

### Scenario: Generator Race
Two players compete to capture the same generator
- Deploy 2 tokens each at same generator
- Verify contested state
- Remove one player's tokens
- Verify capture continues

### Scenario: Crystal Rush
All players try to reach crystal simultaneously
- Move tokens toward center
- Verify combat along the way
- Test holding crystal with different token counts
- Verify win condition with all generators disabled

### Scenario: Combat Chain
Multiple consecutive attacks
- Deploy tokens in a line
- Attack down the line
- Verify damage propagates correctly
- Check token removal when killed

### Scenario: Reserve Depletion
Deploy all tokens of one type
- Try to deploy 6th token of same type
- Verify rejection
- Check error message clarity

### Scenario: Phase Lock
Try actions in wrong phases
- Attack during MOVEMENT
- Move during ACTION
- Deploy during ACTION
- Verify all are rejected with clear errors

## Output

Always conclude playtesting with:
1. **Summary statistics** (turns played, errors found, etc.)
2. **Severity breakdown** (CRITICAL, HIGH, MEDIUM, LOW)
3. **Actionable recommendations**
4. **Sample logs** of interesting events
5. **Next testing steps** if issues found

## Notes

- Use direct `game_state` manipulation for setting up test scenarios (bypass deployment validation)
- The AI API is designed for normal gameplay; tests may need to work around restrictions
- Always run `test_gameplay_flaws.py` as a baseline before manual testing
- Create focused test functions for specific mechanics rather than one large test
- Keep test games deterministic where possible (use fixed seeds)
