# Claude AI Player API - Implementation Plan

## Executive Summary

This plan outlines the implementation of an AI-accessible API layer for "Race to the Crystal" that allows Claude (or any AI) to play the game programmatically without visual rendering, while preserving all existing user gameplay functionality.

## Design Principles

1. **Non-Invasive**: No changes to existing game logic or UI code
2. **Additive**: New API layer sits alongside existing systems
3. **Text-Based**: All game state observable as structured text/JSON
4. **Action-Oriented**: Clear, discrete actions that map to game mechanics
5. **Stateless**: API operates on GameState objects without side effects to rendering
6. **Testable**: Fully unit-testable independent of UI

## Current State Analysis

### Strengths for AI Integration
✅ Game state is fully serializable (to_dict/from_dict/to_json/from_json)
✅ Turn-based mechanics (no real-time requirements)
✅ Well-separated game logic in `/game/` directory
✅ Comprehensive unit tests (140+ tests)
✅ Existing system APIs (MovementSystem, CombatSystem)
✅ Clear action phases (MOVEMENT → ACTION → END_TURN)

### Gaps for AI Players
❌ No unified "get all valid actions" method
❌ No text-based state observation formatted for LLMs
❌ No action validation before execution
❌ No AI-friendly error messages
❌ No game state explanation/narrative generation
❌ No interface for programmatic game control

## Proposed Architecture

```
┌─────────────────────────────────────────┐
│         Human Players (UI)              │
│    client/game_window.py (Arcade)       │
└───────────┬─────────────────────────────┘
            │
            ├─── Mouse/Keyboard Input
            │
            ▼
┌─────────────────────────────────────────┐
│         Game Logic Layer                │
│     game/game_state.py                  │
│     game/movement.py, combat.py, etc.   │
└───────────┬─────────────────────────────┘
            │
            ├─── Direct API Calls
            │
            ▼
┌─────────────────────────────────────────┐
│      NEW: Claude AI API Layer           │
│    game/ai_interface.py (main)          │
│    game/ai_observation.py               │
│    game/ai_actions.py                   │
│    game/ai_validation.py                │
└─────────────────────────────────────────┘
            │
            └─── Text/JSON I/O
                 (for Claude or other AIs)
```

## Implementation Components

### 1. AI Observation Module (`game/ai_observation.py`)

**Purpose**: Convert game state into human-readable, LLM-friendly text descriptions.

**Key Functions**:

```python
def describe_game_state(game_state: GameState, perspective_player_id: str) -> str:
    """
    Generate comprehensive text description of current game state.

    Returns formatted string including:
    - Turn number and current player
    - Your tokens (position, health, status)
    - Enemy tokens (visible information)
    - Generator status (captured, contested, available)
    - Crystal status (requirements, current holders)
    - Board features (mystery squares, deployable corners)
    - Recent events (combat, captures, mystery effects)
    """

def get_board_map(game_state: GameState, perspective_player_id: str) -> str:
    """
    Generate ASCII art map of the board showing:
    - Grid coordinates (0-23 on both axes)
    - Your tokens (with health indicators)
    - Enemy tokens (with player colors)
    - Generators (G1-G4, with capture status)
    - Crystal (C, with holder info)
    - Mystery squares (M)
    - Deployment corners (*)
    - Empty cells (.)
    """

def list_available_actions(game_state: GameState, player_id: str) -> Dict:
    """
    Return structured dict of all valid actions for current turn phase.

    Returns:
    {
        "phase": "MOVEMENT" | "ACTION" | "END_TURN",
        "actions": [
            {
                "type": "MOVE",
                "token_id": 5,
                "token_position": [10, 12],
                "token_health": 8,
                "valid_destinations": [[10, 13], [11, 12], ...],
                "description": "Move token #5 (8hp) from (10,12)"
            },
            {
                "type": "ATTACK",
                "attacker_id": 5,
                "defender_id": 23,
                "damage": 4,
                "will_kill": false,
                "description": "Attack enemy token #23 for 4 damage"
            },
            {
                "type": "DEPLOY",
                "health_value": 10,
                "positions": [[0, 0], [0, 1], ...],
                "description": "Deploy 10hp token from reserve (3 remaining)"
            },
            {
                "type": "END_TURN",
                "description": "End your turn"
            }
        ]
    }
    """

def explain_victory_conditions(game_state: GameState) -> str:
    """
    Explain current win conditions and progress.

    Returns text describing:
    - Current crystal token requirement
    - How many tokens each player has on crystal
    - Turns remaining for each player to win
    - Generator bonuses available (-2 tokens per disabled generator)
    """

def get_strategic_hints(game_state: GameState, player_id: str) -> List[str]:
    """
    OPTIONAL: Generate strategic observations (not decisions).

    Examples:
    - "Generator 1 is uncontested"
    - "Enemy has 8 tokens on crystal (needs 10 for 3 turns)"
    - "You have 5 tokens remaining in reserve"
    - "Token #7 is in attack range of 3 enemy tokens"
    """
```

### 2. AI Action Module (`game/ai_actions.py`)

**Purpose**: Provide high-level action execution with validation and clear error messages.

**Key Classes**:

```python
@dataclass
class AIAction:
    """Base class for all AI actions."""
    action_type: str

@dataclass
class MoveAction(AIAction):
    token_id: int
    destination: Tuple[int, int]

@dataclass
class AttackAction(AIAction):
    attacker_id: int
    defender_id: int

@dataclass
class DeployAction(AIAction):
    health_value: int
    position: Tuple[int, int]

@dataclass
class EndTurnAction(AIAction):
    pass

class AIActionExecutor:
    """Validates and executes AI actions with detailed feedback."""

    def validate_action(self, action: AIAction, game_state: GameState,
                       player_id: str) -> Tuple[bool, str]:
        """
        Validate action without executing.

        Returns: (is_valid, error_message_or_success)

        Example errors:
        - "Cannot move: Not your turn"
        - "Cannot move: Wrong phase (currently in ACTION phase)"
        - "Cannot move: Token #5 does not belong to you"
        - "Cannot move: Destination (15,20) is occupied"
        - "Cannot attack: Target not adjacent to attacker"
        - "Cannot deploy: No 10hp tokens in reserve"
        """

    def execute_action(self, action: AIAction, game_state: GameState,
                      player_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate and execute action.

        Returns: (success, message, result_data)

        result_data examples:
        - MoveAction: {"mystery_triggered": true, "mystery_effect": "heal"}
        - AttackAction: {"damage_dealt": 5, "defender_killed": true}
        - DeployAction: {"new_token_id": 42, "tokens_remaining": 2}
        """
```

### 3. AI Interface Module (`game/ai_interface.py`)

**Purpose**: Main interface that combines observation and action execution.

**Key Class**:

```python
class ClaudeGameInterface:
    """
    Main interface for AI players to interact with Race to the Crystal.

    This class provides all functionality needed for an AI to:
    1. Observe the current game state in text format
    2. Understand available actions
    3. Execute actions with validation
    4. Receive feedback in natural language
    """

    def __init__(self, game_state: GameState, player_id: str):
        self.game_state = game_state
        self.player_id = player_id
        self.observer = AIObserver()
        self.executor = AIActionExecutor()
        self.action_history: List[str] = []

    def get_situation_report(self) -> str:
        """
        Get complete situation report for AI decision-making.

        Returns formatted string with:
        1. Game state description
        2. Board map
        3. Available actions (as numbered list)
        4. Victory condition status
        5. Recent action history (last 5 actions)
        """

    def take_action(self, action: AIAction) -> str:
        """
        Execute an action and return natural language feedback.

        Handles:
        - Validation
        - Execution
        - Mystery square events
        - Combat results
        - Phase transitions
        - Win condition checks

        Returns detailed narrative of what happened.
        """

    def get_action_from_description(self, description: str) -> Optional[AIAction]:
        """
        OPTIONAL: Parse natural language action into AIAction object.

        Examples:
        - "move token 5 to (12, 15)" → MoveAction(5, (12, 15))
        - "attack token 23 with token 5" → AttackAction(5, 23)
        - "deploy 10hp token at (0, 0)" → DeployAction(10, (0, 0))
        - "end turn" → EndTurnAction()
        """

    def to_json(self) -> str:
        """Export current interface state for saving/loading."""

    @classmethod
    def from_json(cls, json_str: str) -> 'ClaudeGameInterface':
        """Load interface from saved state."""
```

### 4. Validation Module (`game/ai_validation.py`)

**Purpose**: Centralized validation logic with detailed error messages.

**Key Functions**:

```python
def validate_move_action(token_id: int, destination: Tuple[int, int],
                        game_state: GameState, player_id: str) -> ValidationResult:
    """Validate movement action with specific error messages."""

def validate_attack_action(attacker_id: int, defender_id: int,
                          game_state: GameState, player_id: str) -> ValidationResult:
    """Validate attack action with specific error messages."""

def validate_deploy_action(health_value: int, position: Tuple[int, int],
                          game_state: GameState, player_id: str) -> ValidationResult:
    """Validate deployment action with specific error messages."""

@dataclass
class ValidationResult:
    is_valid: bool
    error_message: Optional[str]
    error_code: Optional[str]  # For programmatic handling
```

## File Structure

```
race-to-the-crystal/
├── game/
│   ├── ai_interface.py          # NEW: Main AI interface
│   ├── ai_observation.py        # NEW: State → Text conversion
│   ├── ai_actions.py            # NEW: Action classes and executor
│   ├── ai_validation.py         # NEW: Validation with error messages
│   ├── game_state.py            # EXISTING: No changes
│   ├── movement.py              # EXISTING: No changes
│   ├── combat.py                # EXISTING: No changes
│   └── ...
├── tests/
│   ├── test_ai_interface.py     # NEW: AI interface tests
│   ├── test_ai_observation.py   # NEW: Observation tests
│   ├── test_ai_actions.py       # NEW: Action execution tests
│   └── ...
├── examples/
│   ├── ai_player_example.py     # NEW: Example AI player
│   └── claude_game_session.py   # NEW: Interactive Claude session
└── client/
    └── ...                       # EXISTING: No changes needed
```

## Example Usage

### Example 1: Basic AI Turn

```python
from game.ai_interface import ClaudeGameInterface
from game.ai_actions import MoveAction, EndTurnAction
from game.game_state import GameState

# Load or create game state
game_state = GameState.from_json(saved_game_json)
ai_player_id = "player_1"

# Create AI interface
ai = ClaudeGameInterface(game_state, ai_player_id)

# Get situation report (this is what Claude would receive)
report = ai.get_situation_report()
print(report)

"""
Output example:
═══════════════════════════════════════════
TURN 15 - YOUR TURN (Player 1 - Red)
═══════════════════════════════════════════

BOARD STATE:
[ASCII map showing 24x24 grid with tokens, generators, crystal]

YOUR TOKENS (8 deployed, 12 in reserve):
  Token #5  @ (10,12) - 8hp  [Can move or attack]
  Token #12 @ (11,12) - 6hp  [Can move or attack]
  ...

ENEMY TOKENS:
  Player 2 (Blue): 6 tokens deployed
  Player 3 (Green): 5 tokens deployed

GENERATORS:
  G1 (0-11, 0-11):   Captured by Player 2
  G2 (12-23, 0-11):  Uncontested
  G3 (0-11, 12-23):  Contested (You: 1, Player 3: 1)
  G4 (12-23, 12-23): Captured by You (2/2 turns)

CRYSTAL @ (12,12):
  Tokens needed: 10 (base 12 - 2 for your disabled generator)
  Current holders: Player 2 has 5 tokens

AVAILABLE ACTIONS (choose one):
  1. MOVE token #5 from (10,12) to: (10,13), (11,12), (11,13), ...
  2. MOVE token #12 from (11,12) to: (11,13), (12,12), (12,13), ...
  ...
  15. ATTACK token #23 with token #5 (will deal 4 damage)
  ...
  20. DEPLOY 10hp token at corner positions: (0,0), (0,1), ...
  21. END TURN
"""

# Claude decides on action
action = MoveAction(token_id=5, destination=(12, 12))

# Execute action
result = ai.take_action(action)
print(result)

"""
Output:
✓ Token #5 moved from (10,12) to (12,12)
→ Token #5 landed on the CRYSTAL!
→ You now have 6 tokens on the crystal (need 10 for 3 turns to win)
→ Phase changed to ACTION (you can attack or end turn)
"""
```

### Example 2: Claude Interactive Session

```python
# examples/claude_game_session.py

def play_game_with_claude():
    """Interactive session where Claude plays the game."""

    game_state = create_new_game(num_players=2)
    claude_player_id = "player_1"
    ai = ClaudeGameInterface(game_state, claude_player_id)

    while game_state.phase == GamePhase.PLAYING:
        if game_state.current_turn_player_id == claude_player_id:
            # Claude's turn
            report = ai.get_situation_report()

            # Send to Claude (via API or print for human to relay)
            print("\n" + "="*60)
            print("CLAUDE'S TURN")
            print("="*60)
            print(report)
            print("\nWhat action should Claude take?")

            # Receive Claude's decision
            action_input = input("> ")

            # Parse action (or use predefined action format)
            action = parse_action(action_input)

            # Execute
            result = ai.take_action(action)
            print(f"\n{result}\n")

        else:
            # Human player turn (use existing UI or command line)
            play_human_turn(game_state)

    print(f"\n🎉 Game Over! Winner: {game_state.winner}")
```

### Example 3: Action Validation Before Execution

```python
from game.ai_actions import AttackAction

# Claude wants to attack
action = AttackAction(attacker_id=5, defender_id=23)

# Validate before executing
is_valid, message = ai.executor.validate_action(action, game_state, player_id)

if not is_valid:
    print(f"❌ Invalid action: {message}")
    # Claude can choose a different action
else:
    print(f"✓ Valid action: {message}")
    # Proceed with execution
    result = ai.take_action(action)
```

## Integration with Existing Code

### NO CHANGES REQUIRED to existing files:
- ✅ `game/game_state.py` - Used as-is
- ✅ `game/movement.py` - Called by AI action executor
- ✅ `game/combat.py` - Called by AI action executor
- ✅ `game/board.py`, `token.py`, etc. - Used through GameState
- ✅ `client/*` - Completely independent, unchanged

### NEW CODE ONLY:
- All AI functionality in new files with `ai_` prefix
- Existing tests continue to pass
- New tests for AI interface
- Example scripts for demonstration

## Implementation Phases

### Phase 1: Core Observation (Week 1)
**Goal**: Claude can "see" the game state in text

1. Create `game/ai_observation.py`
2. Implement `describe_game_state()`
3. Implement `get_board_map()` with ASCII art
4. Implement `list_available_actions()`
5. Write comprehensive unit tests
6. Manual testing with sample game states

**Deliverable**: Text descriptions that fully represent game state

### Phase 2: Action Execution (Week 1-2)
**Goal**: Claude can execute validated actions

1. Create `game/ai_actions.py` with action classes
2. Create `game/ai_validation.py` with validation logic
3. Implement `AIActionExecutor` with error handling
4. Write unit tests for all action types
5. Test edge cases (invalid moves, wrong phase, etc.)

**Deliverable**: Robust action execution system

### Phase 3: Unified Interface (Week 2)
**Goal**: Complete AI player interface

1. Create `game/ai_interface.py`
2. Implement `ClaudeGameInterface` class
3. Implement `get_situation_report()`
4. Implement `take_action()` with narrative feedback
5. Add JSON serialization for saving AI state
6. Comprehensive integration tests

**Deliverable**: Production-ready AI interface

### Phase 4: Examples & Documentation (Week 2-3)
**Goal**: Easy for Claude or other AIs to use

1. Create `examples/ai_player_example.py`
2. Create `examples/claude_game_session.py`
3. Write API documentation
4. Create tutorial for integrating AI players
5. Add example game scenarios
6. Performance testing with full games

**Deliverable**: Complete documentation and examples

### Phase 5: Optional Enhancements (Week 3+)
**Goal**: Advanced features

1. Natural language action parsing
2. Strategic hints generation
3. Action history and replay
4. Multiple AI players in same game
5. AI vs AI tournament mode
6. Integration with Claude API directly

**Deliverable**: Enhanced AI capabilities

## Testing Strategy

### Unit Tests
```python
# tests/test_ai_observation.py
def test_board_map_shows_all_entities():
    """Verify ASCII map includes all tokens, generators, crystal."""

def test_available_actions_during_movement_phase():
    """Verify correct actions listed during movement."""

def test_available_actions_during_action_phase():
    """Verify only attack/end_turn available after movement."""

# tests/test_ai_actions.py
def test_move_action_validation():
    """Verify movement validation catches all error cases."""

def test_attack_action_execution():
    """Verify combat is correctly resolved."""

def test_deploy_action_with_no_reserve():
    """Verify error when trying to deploy without tokens."""

# tests/test_ai_interface.py
def test_full_turn_sequence():
    """Test complete turn: observe → move → attack → end."""

def test_ai_wins_by_crystal_capture():
    """Test game completion detection."""
```

### Integration Tests
```python
def test_ai_plays_full_game():
    """Simulate complete game with AI making random valid moves."""

def test_ai_vs_ai_game():
    """Two AI interfaces playing against each other."""

def test_all_special_cases():
    """Mystery squares, generator capture, crystal capture."""
```

### Manual Testing Checklist
- [ ] AI can observe empty board
- [ ] AI can deploy tokens
- [ ] AI can move tokens (all ranges)
- [ ] AI can attack and kill enemies
- [ ] AI receives mystery square events
- [ ] AI can capture generators
- [ ] AI can win by crystal capture
- [ ] All error messages are clear and actionable
- [ ] Board map is readable and accurate
- [ ] Action descriptions match actual game rules

## Success Criteria

### Must Have
✅ Claude can receive complete game state as text
✅ Claude can see all valid actions with descriptions
✅ Claude can execute any valid game action
✅ All invalid actions are rejected with clear errors
✅ Zero changes to existing game logic or UI code
✅ All existing tests still pass
✅ New functionality has >90% test coverage
✅ Documentation with usage examples

### Should Have
✅ ASCII board map is visually clear
✅ Action feedback is narrative and informative
✅ Strategic hints available (optional for Claude to use)
✅ Serialization for saving/loading AI game state
✅ Example scripts demonstrating usage

### Nice to Have
⭐ Natural language action parsing
⭐ Direct Claude API integration
⭐ AI tournament/benchmark system
⭐ Replay system for AI games
⭐ Performance metrics for AI players

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing UI | HIGH | No changes to existing files; all new code in separate modules |
| Incomplete action coverage | MEDIUM | Comprehensive unit tests; manual verification against UI |
| Unclear text descriptions | MEDIUM | User testing with actual Claude sessions; iteration on format |
| Performance overhead | LOW | AI interface is optional; no impact on regular gameplay |
| Maintenance burden | LOW | Well-tested, follows existing patterns, minimal dependencies |

## Next Steps

1. **Review & Approval**: Get stakeholder feedback on this plan
2. **Prototype**: Create minimal `ai_observation.py` with one game state example
3. **Validate Format**: Test text output with Claude to ensure it's usable
4. **Iterate**: Adjust format based on Claude's feedback
5. **Full Implementation**: Execute phases 1-4 as outlined
6. **Production**: Deploy and monitor first real Claude vs Human games

## Questions for Stakeholders

1. Should AI players be able to see all enemy token positions, or limited visibility?
2. Should we include optional "strategic hints" or keep it pure observation?
3. What's the priority: Claude playing vs humans, or Claude vs Claude?
4. Should we integrate directly with Claude API, or keep it generic for any AI?
5. Do we want AI player logging/analytics for research purposes?

---

**Document Version**: 1.0
**Last Updated**: 2025-12-26
**Author**: Claude (AI Planning Assistant)
**Status**: DRAFT - Awaiting Review
