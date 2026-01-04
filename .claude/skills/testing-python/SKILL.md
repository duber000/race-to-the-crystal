---
name: testing-python
description: Run pytest unit tests for the Race to the Crystal project using uv and make commands. Use when running tests, verifying code changes, debugging test failures, checking test coverage, or validating game mechanics implementations.
---

# Testing Python

This project uses pytest for testing with uv for dependency management.

## Quick Commands

### Using Make (Recommended)

```bash
# Run all tests
make test

# Run tests with verbose output
make test-verbose

# Run tests with minimal output (quiet mode)
make test-fast

# Run only previously failed tests
make test-failed

# Run specific test file
make test-specific FILE=tests/test_token.py

# Run tests with coverage report
make test-coverage

# Show all available commands
make help
```

### Direct pytest Commands

```bash
# Using the virtual environment directly
.venv/bin/pytest

# Using uv run (if venv not set up)
uv run --group dev pytest

# Verbose output
.venv/bin/pytest -v

# Quiet mode
.venv/bin/pytest -q

# Run specific test file
.venv/bin/pytest tests/test_combat.py

# Run specific test class
.venv/bin/pytest tests/test_combat.py::TestCombatSystem

# Run specific test method
.venv/bin/pytest tests/test_combat.py::TestCombatSystem::test_can_attack_valid

# Show test output even for passing tests
.venv/bin/pytest -s

# Stop on first failure
.venv/bin/pytest -x

# Run last failed tests
.venv/bin/pytest --lf

# Run tests matching a keyword
.venv/bin/pytest -k "combat"
```

## Test Structure

The project has 268 unit tests organized by component:

- `tests/test_token.py` - Token mechanics and state
- `tests/test_board.py` - Board and cell management
- `tests/test_movement.py` - Pathfinding and movement validation
- `tests/test_combat.py` - Combat system and damage calculations
- `tests/test_generator.py` - Generator capture mechanics
- `tests/test_crystal.py` - Win condition logic
- `tests/test_game_state.py` - State management and turn flow
- `tests/test_ai_observation.py` - AI observation API
- `tests/test_ai_actions.py` - AI action execution
- `tests/test_3d_controls.py` - 3D camera and controls
- `tests/test_network_*.py` - Network multiplayer functionality
- And more...

## Test Configuration

Tests are configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
]
```

## Writing New Tests

Follow the existing pattern:

```python
import pytest
from game.module import ClassName

class TestClassName:
    """Test cases for ClassName."""

    def test_feature_name(self):
        """Test description."""
        # Arrange
        obj = ClassName(param="value")

        # Act
        result = obj.method()

        # Assert
        assert result == expected_value
```

## Continuous Integration

Tests should pass before committing:

```bash
# Run all tests before committing
make test

# Or run fast tests for quick feedback
make test-fast
```

## Debugging Failed Tests

```bash
# Run only failed tests from last run
make test-failed

# Run with verbose output to see more details
make test-verbose

# Run specific test that's failing
make test-specific FILE=tests/test_combat.py

# Use -s flag to see print statements
.venv/bin/pytest -s tests/test_combat.py
```

## Coverage

To see test coverage:

```bash
make test-coverage
```

This will show which lines of code are covered by tests.

## Dependencies

Test dependencies are managed in `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
]
```

Sync dependencies:

```bash
uv sync --group dev
```

## Best Practices

1. **Run tests frequently** - Use `make test-fast` for quick feedback
2. **Test one thing at a time** - Each test should verify one behavior
3. **Use descriptive names** - Test names should describe what they verify
4. **Keep tests independent** - Tests should not depend on each other
5. **Use fixtures for setup** - Reuse common setup code with pytest fixtures
6. **Test edge cases** - Include tests for boundary conditions and errors
