"""
Manual test script for AI Actions module.

This script demonstrates the AI action execution functionality.
"""
import sys
sys.path.insert(0, '/home/user/race-to-the-crystal')

from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_actions import (
    AIActionExecutor,
    MoveAction,
    AttackAction,
    DeployAction,
    EndTurnAction,
)
from shared.enums import PlayerColor, TurnPhase


def create_test_game(num_players: int = 2) -> GameState:
    """Helper function to create a test game state."""
    game_state = GameState()
    num_players = max(2, min(4, num_players))

    # Create players
    player_colors = [
        PlayerColor.CYAN,
        PlayerColor.MAGENTA,
        PlayerColor.YELLOW,
        PlayerColor.GREEN,
    ]
    player_names = ["Player 1", "Player 2", "Player 3", "Player 4"]

    for i in range(num_players):
        player_id = f"player_{i}"
        game_state.add_player(player_id, player_names[i], player_colors[i])

    # Start the game
    game_state.start_game()

    # Initialize generators
    generator_positions = game_state.board.get_generator_positions()
    for i, pos in enumerate(generator_positions):
        generator = Generator(id=i, position=pos)
        game_state.generators.append(generator)

    # Initialize crystal
    crystal_pos = game_state.board.get_crystal_position()
    game_state.crystal = Crystal(position=crystal_pos)

    return game_state


def test_deploy_action():
    """Test deploying a token."""
    print("=" * 70)
    print("TEST 1: Deploy Action")
    print("=" * 70)

    game_state = create_test_game()
    executor = AIActionExecutor()
    game_state.turn_phase = TurnPhase.MOVEMENT

    # Create deploy action
    action = DeployAction(health_value=10, position=(0, 0))

    # Validate
    is_valid, msg = executor.validate_action(action, game_state, "player_0")
    print(f"Validation: {is_valid}")
    print(f"Message: {msg}")
    assert is_valid

    # Execute
    success, msg, data = executor.execute_action(action, game_state, "player_0")
    print(f"\nExecution: {success}")
    print(f"Message:\n{msg}")
    print(f"Data: {data}")

    assert success
    assert game_state.turn_phase == TurnPhase.ACTION
    print("\n✓ Test passed: Deploy action works\n")


def test_move_action():
    """Test moving a token."""
    print("=" * 70)
    print("TEST 2: Move Action")
    print("=" * 70)

    game_state = create_test_game()
    executor = AIActionExecutor()

    # Deploy a token first
    token = game_state.deploy_token("player_0", 10, (5, 5))
    game_state.turn_phase = TurnPhase.MOVEMENT

    # Create move action
    action = MoveAction(token_id=token.id, destination=(5, 6))

    # Validate
    is_valid, msg = executor.validate_action(action, game_state, "player_0")
    print(f"Validation: {is_valid}")
    print(f"Message: {msg}")
    assert is_valid

    # Execute
    success, msg, data = executor.execute_action(action, game_state, "player_0")
    print(f"\nExecution: {success}")
    print(f"Message:\n{msg}")
    print(f"Data: {data}")

    assert success
    assert token.position == (5, 6)
    assert game_state.turn_phase == TurnPhase.ACTION
    print("\n✓ Test passed: Move action works\n")


def test_attack_action():
    """Test attacking a token."""
    print("=" * 70)
    print("TEST 3: Attack Action")
    print("=" * 70)

    game_state = create_test_game()
    executor = AIActionExecutor()

    # Deploy two adjacent tokens
    attacker = game_state.deploy_token("player_0", 10, (5, 5))
    defender = game_state.deploy_token("player_1", 8, (5, 6))
    game_state.turn_phase = TurnPhase.ACTION

    print(f"Attacker: Token #{attacker.id} at {attacker.position} with {attacker.health}hp")
    print(f"Defender: Token #{defender.id} at {defender.position} with {defender.health}hp")

    # Create attack action
    action = AttackAction(attacker_id=attacker.id, defender_id=defender.id)

    # Validate
    is_valid, msg = executor.validate_action(action, game_state, "player_0")
    print(f"\nValidation: {is_valid}")
    print(f"Message: {msg}")
    assert is_valid

    # Execute
    success, msg, data = executor.execute_action(action, game_state, "player_0")
    print(f"\nExecution: {success}")
    print(f"Message:\n{msg}")
    print(f"Data: {data}")

    assert success
    assert defender.health == 3  # 8 - 5 = 3
    print("\n✓ Test passed: Attack action works\n")


def test_end_turn_action():
    """Test ending a turn."""
    print("=" * 70)
    print("TEST 4: End Turn Action")
    print("=" * 70)

    game_state = create_test_game()
    executor = AIActionExecutor()
    game_state.turn_phase = TurnPhase.ACTION

    print(f"Current turn: {game_state.turn_number}")
    print(f"Current player: {game_state.current_turn_player_id}")

    # Create end turn action
    action = EndTurnAction()

    # Validate
    is_valid, msg = executor.validate_action(action, game_state, "player_0")
    print(f"\nValidation: {is_valid}")
    print(f"Message: {msg}")
    assert is_valid

    # Execute
    success, msg, data = executor.execute_action(action, game_state, "player_0")
    print(f"\nExecution: {success}")
    print(f"Message:\n{msg}")
    print(f"Data: {data}")

    assert success
    print("\n✓ Test passed: End turn action works\n")


def test_invalid_action():
    """Test that invalid actions are rejected."""
    print("=" * 70)
    print("TEST 5: Invalid Action Rejection")
    print("=" * 70)

    game_state = create_test_game()
    executor = AIActionExecutor()

    # Try to move in wrong phase
    token = game_state.deploy_token("player_0", 10, (5, 5))
    game_state.turn_phase = TurnPhase.ACTION  # Wrong phase for movement

    action = MoveAction(token_id=token.id, destination=(5, 6))

    is_valid, msg = executor.validate_action(action, game_state, "player_0")
    print(f"Validation: {is_valid}")
    print(f"Message: {msg}")

    assert not is_valid
    assert "wrong phase" in msg.lower()

    print("\n✓ Test passed: Invalid actions are properly rejected\n")


def test_not_your_turn():
    """Test that actions fail when it's not your turn."""
    print("=" * 70)
    print("TEST 6: Not Your Turn Rejection")
    print("=" * 70)

    game_state = create_test_game()
    executor = AIActionExecutor()
    game_state.turn_phase = TurnPhase.MOVEMENT
    game_state.current_turn_player_id = "player_1"  # Set to player_1

    # Try to deploy as player_0
    action = DeployAction(health_value=10, position=(0, 0))

    is_valid, msg = executor.validate_action(action, game_state, "player_0")
    print(f"Validation: {is_valid}")
    print(f"Message: {msg}")

    assert not is_valid
    assert "not your turn" in msg.lower()

    print("\n✓ Test passed: Non-current player actions are rejected\n")


def test_full_turn_sequence():
    """Test a complete turn sequence."""
    print("=" * 70)
    print("TEST 7: Complete Turn Sequence")
    print("=" * 70)

    game_state = create_test_game()
    executor = AIActionExecutor()

    print("Turn Sequence for player_0:")
    print("1. Deploy a token")
    print("2. End turn without attacking")
    print()

    # Phase 1: Deploy
    game_state.turn_phase = TurnPhase.MOVEMENT
    deploy_action = DeployAction(health_value=10, position=(0, 0))
    success, msg, data = executor.execute_action(deploy_action, game_state, "player_0")
    print(f"Deploy result: {success}")
    print(f"Message: {msg}\n")
    assert success
    assert game_state.turn_phase == TurnPhase.ACTION

    # Phase 2: End turn
    end_action = EndTurnAction()
    success, msg, data = executor.execute_action(end_action, game_state, "player_0")
    print(f"End turn result: {success}")
    print(f"Message: {msg}\n")
    assert success

    print("✓ Test passed: Complete turn sequence works\n")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 17 + "AI ACTIONS MODULE - MANUAL TESTS" + " " * 19 + "║")
    print("╚" + "=" * 68 + "╝")
    print("\n")

    tests = [
        test_deploy_action,
        test_move_action,
        test_attack_action,
        test_end_turn_action,
        test_invalid_action,
        test_not_your_turn,
        test_full_turn_sequence,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}\n")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n")
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)
    print("\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
