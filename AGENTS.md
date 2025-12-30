# AGENTS.md

This document provides guidance for AI coding agents and developers working on the Race to the Crystal codebase. It covers coding standards, architectural patterns, and best practices.

## Codebase Overview

Race to the Crystal is a Python-based multiplayer strategy game with a clean separation between game logic and rendering. The codebase follows these core principles:

- **Separation of Concerns**: Game logic (`game/`) is completely independent from rendering (`client/`)
- **Test-Driven Development**: 199+ unit tests with 100% pass rate
- **Type Safety**: Strong use of enums and constants
- **AI-First Design**: Built to support AI players and headless gameplay

## Coding Standards

### Python Style

- **Python 3.14+** required
- **Type hints** encouraged for new code
- **Docstrings** for all public functions and classes
- **PEP 8** compliance (use `make lint` to check)
- **f-strings** preferred over `.format()` or `%` formatting
- **List/dict comprehensions** preferred over loops where readable

### File Organization

```python
# Standard imports first
import os
import sys

# Third-party imports
import arcade
import numpy as np

# Local imports (relative)
from . import constants
from ..shared import enums
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `GameState`, `Token`, `AIObserver`)
- **Functions/methods**: `snake_case` (e.g., `validate_action`, `execute_move`)
- **Variables**: `snake_case` (e.g., `current_player_id`, `token_position`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `BOARD_SIZE`, `MAX_TOKENS`)
- **Private members**: `_prefix` (e.g., `_internal_state`, `_validate_move`)

### Error Handling

- Use **custom exceptions** for domain-specific errors
- Include **detailed error messages** for debugging
- Validate inputs early with **guard clauses**

```python
# Good example from ai_actions.py
def validate_action(self, action, game_state, player_id):
    if not isinstance(action, AIAction):
        raise ValueError(f"Invalid action type: {type(action)}")
    
    if game_state.current_turn_player_id != player_id:
        raise GameError(f"Player {player_id} cannot act - it's player {game_state.current_turn_player_id}'s turn")
```

## Architectural Patterns

### Game Logic Layer (`game/`)

**Key Principles:**
- **No rendering dependencies** - pure Python logic
- **State management** through `GameState` class
- **Action-based API** via `ai_actions.py`
- **Observation API** via `ai_observation.py`

**Module Responsibilities:**
- `game_state.py`: Central state management
- `ai_actions.py`: Action validation and execution
- `ai_observation.py`: State observation for AI players
- `board.py`: Grid and cell management
- `token.py`: Token behavior and state
- `movement.py`: Pathfinding and movement rules
- `combat.py`: Combat resolution
- `generator.py`: Generator capture mechanics
- `crystal.py`: Win condition logic

### Rendering Layer (`client/`)

**Key Principles:**
- **Read-only access** to game state
- **No business logic** - only visualization
- **Dual rendering modes** (2D/3D)
- **Event-driven input handling**

**Module Responsibilities:**
- `game_window.py`: Main rendering loop
- `board_3d.py`: 3D board rendering
- `token_3d.py`: 3D token rendering
- `sprites/`: 2D sprite implementations
- `ui/`: User interface components

### Shared Layer (`shared/`)

**Key Principles:**
- **Constants and enums** only
- **No logic or state**
- **Shared between game and client**

## Development Workflow

### Adding New Features

1. **Update constants** in `shared/constants.py` if needed
2. **Implement logic** in `game/` modules
3. **Add unit tests** in `tests/` directory
4. **Update rendering** in `client/` if visual changes needed
5. **Run full test suite**: `make test`
6. **Manual testing**: Run game and verify behavior

### Bug Fixing

1. **Reproduce** the issue
2. **Write failing test** that demonstrates the bug
3. **Fix logic** in appropriate module
4. **Verify fix** with test
5. **Run regression tests**: `make test`

### Testing Strategy

**Unit Tests:**
- Test individual components in isolation
- Use `pytest` framework
- Focus on game logic, not rendering

**Integration Tests:**
- Test interactions between components
- Verify state transitions
- Check turn-based logic

**Playtesting:**
- Manual gameplay testing
- AI vs AI automated testing
- Verify end-to-end gameplay flows

## AI Agent Integration

The game is designed for AI agent integration through two main APIs:

### Observation API (`ai_observation.py`)

```python
from game.ai_observation import AIObserver

# Get complete game state description
report = AIObserver.get_situation_report(game_state, player_id)

# Get ASCII board map
board_map = AIObserver.get_board_map(game_state)

# List available actions
actions = AIObserver.list_available_actions(game_state, player_id)
```

### Action API (`ai_actions.py`)

```python
from game.ai_actions import AIActionExecutor, MoveAction

executor = AIActionExecutor()
action = MoveAction(token_id=5, destination=(12, 12))
success, message, data = executor.execute_action(action, game_state, player_id)
```

### AI Agent Example

```python
class SimpleAI:
    def __init__(self, player_id):
        self.player_id = player_id
    
    def get_action(self, game_state):
        observer = AIObserver()
        actions = observer.list_available_actions(game_state, self.player_id)
        
        # Simple strategy: move first token toward center
        for action in actions:
            if isinstance(action, MoveAction):
                return action
        
        # Fallback: end turn
        return EndTurnAction()
```

## Performance Considerations

### Game Logic
- **Pathfinding**: BFS algorithm in `movement.py`
- **State updates**: Minimize copying of game state
- **Validation**: Early validation to avoid expensive operations

### Rendering
- **GPU acceleration**: Use Arcade's built-in GPU features
- **Batch rendering**: Group similar objects for rendering
- **Caching**: Cache computed values where possible

## Common Pitfalls

### Game State Management
- **Always use GameState methods** for state changes
- **Never modify state directly** - use action API
- **Keep board occupancy in sync** with token positions

### Token Management
- **is_deployed vs is_alive**: Understand the difference
- **Movement ranges**: 6hp and 4hp tokens move 2 spaces, others move 1
- **Reserve tokens**: Must be deployed before use

### Turn Phases
- **MOVEMENT phase**: Can move or deploy
- **ACTION phase**: Can attack or end turn
- **Phase transitions**: Automatic after certain actions

## Documentation Standards

### Code Comments
- **Inline comments**: Explain why, not what
- **Complex algorithms**: Add step-by-step comments
- **TODO markers**: Use `# TODO:` for future work

### Docstrings
```python
"""
Describe what the function does, not how it does it.

Args:
    param1: Description of parameter
    param2: Description of parameter

Returns:
    Description of return value

Raises:
    ExceptionType: Description of when raised
"""
```

### Commit Messages
- **Imperative mood**: "Add feature" not "Added feature"
- **Scope**: Include module name if relevant
- **Body**: Explain why, not what (for significant changes)

## Version Control

### Branching Strategy
- **main**: Production-ready code
- **feature/*`: New features
- **bugfix/*`: Bug fixes
- **docs/*`: Documentation updates

### Commit Hygiene
- **Small, focused commits**
- **Clear, descriptive messages**
- **Reference issues** when applicable
- **Sign commits** if possible

## Continuous Integration

The project uses GitHub Actions for CI/CD:

- **Test suite**: Runs on every push
- **Linting**: Checks code style
- **Type checking**: Verifies type hints
- **Build verification**: Ensures project builds

## Getting Help

### Debugging Tips
- **Use logging**: Add debug logs for complex flows
- **Isolate components**: Test logic without rendering
- **Check state**: Verify game state at each step
- **Review tests**: Look at existing tests for patterns

### Resources
- **Arcade documentation**: For rendering questions
- **Python docs**: For language features
- **PEP 8**: For style guidelines
- **Existing code**: Follow established patterns

## Contributing

### Pull Request Process
1. **Fork repository**
2. **Create feature branch**
3. **Implement changes**
4. **Add tests**
5. **Update documentation**
6. **Submit PR** with clear description

### Code Review
- **Be constructive** in feedback
- **Explain reasoning** for suggestions
- **Focus on quality** over personal preferences
- **Respect decisions** of maintainers

## Maintenance

### Dependency Management
- **uv** for package management
- **Regular updates**: Keep dependencies current
- **Security patches**: Apply promptly

### Technical Debt
- **Track in issues** with `tech-debt` label
- **Address in dedicated PRs**
- **Balance with new features**

## Future Directions

### Planned Features
- **Network multiplayer**
- **AI opponents** with different strategies
- **Game replays** and save/load
- **Custom maps** and scenarios

### Architectural Improvements
- **Performance optimization** for large games
- **Better AI API** for external agents
- **Enhanced testing** coverage
- **Improved documentation**

This document serves as a living guide for AI agents and developers working on the Race to the Crystal codebase. Update it as patterns evolve and new conventions emerge.
