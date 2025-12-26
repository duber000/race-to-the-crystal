"""
Manual test script for AI Observation module.

This script demonstrates the AI observation functionality without requiring pytest.
"""
import sys
sys.path.insert(0, '/home/user/race-to-the-crystal')

from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_observation import AIObserver
from shared.enums import PlayerColor


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

    # Start the game (creates tokens and sets phase to PLAYING)
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


def test_basic_observation():
    """Test basic game state observation."""
    print("=" * 70)
    print("TEST 1: Basic Game State Observation")
    print("=" * 70)

    game_state = create_test_game(2)

    description = AIObserver.describe_game_state(game_state, "player_0")
    print(description)

    assert "YOUR TOKENS" in description
    assert "20 in reserve" in description
    print("\n✓ Test passed: Game state description works\n")


def test_board_map():
    """Test board map generation."""
    print("=" * 70)
    print("TEST 2: Board Map Generation")
    print("=" * 70)

    game_state = create_test_game(2)

    # Deploy some tokens
    game_state.deploy_token("player_0", 10, (5, 5))
    game_state.deploy_token("player_1", 8, (10, 10))

    board_map = AIObserver.get_board_map(game_state, "player_0")
    print(board_map)

    assert "BOARD MAP" in board_map
    assert "LEGEND:" in board_map
    print("\n✓ Test passed: Board map generation works\n")


def test_available_actions():
    """Test listing available actions."""
    print("=" * 70)
    print("TEST 3: Available Actions Listing")
    print("=" * 70)

    game_state = create_test_game(2)
    game_state.current_turn_player_id = "player_0"

    # Deploy a token
    game_state.deploy_token("player_0", 10, (5, 5))

    actions_data = AIObserver.list_available_actions(game_state, "player_0")

    print(f"Phase: {actions_data['phase']}")
    print(f"Number of available actions: {len(actions_data['actions'])}")
    print("\nActions:")
    for i, action in enumerate(actions_data['actions'][:5], 1):  # Show first 5
        print(f"  {i}. {action['description']}")
    if len(actions_data['actions']) > 5:
        print(f"  ... and {len(actions_data['actions']) - 5} more actions")

    assert len(actions_data['actions']) > 0
    print("\n✓ Test passed: Action listing works\n")


def test_victory_conditions():
    """Test victory conditions explanation."""
    print("=" * 70)
    print("TEST 4: Victory Conditions Explanation")
    print("=" * 70)

    game_state = create_test_game(2)

    explanation = AIObserver.explain_victory_conditions(game_state)
    print(explanation)

    assert "VICTORY CONDITIONS:" in explanation
    print("\n✓ Test passed: Victory conditions explanation works\n")


def test_situation_report():
    """Test complete situation report."""
    print("=" * 70)
    print("TEST 5: Complete Situation Report")
    print("=" * 70)

    game_state = create_test_game(2)
    game_state.current_turn_player_id = "player_0"

    # Deploy some tokens for a more interesting scenario
    game_state.deploy_token("player_0", 10, (5, 5))
    game_state.deploy_token("player_0", 8, (6, 6))
    game_state.deploy_token("player_1", 10, (18, 18))

    report = AIObserver.get_situation_report(game_state, "player_0")
    print(report)

    assert "YOUR TOKENS" in report
    assert "BOARD MAP" in report
    assert "AVAILABLE ACTIONS:" in report
    assert "VICTORY CONDITIONS:" in report
    print("\n✓ Test passed: Situation report works\n")


def test_multi_player_game():
    """Test with 4 players."""
    print("=" * 70)
    print("TEST 6: 4-Player Game Observation")
    print("=" * 70)

    game_state = create_test_game(4)

    # Deploy tokens for all players
    game_state.deploy_token("player_0", 10, (2, 2))    # Cyan
    game_state.deploy_token("player_1", 8, (21, 2))    # Magenta
    game_state.deploy_token("player_2", 6, (2, 21))    # Yellow
    game_state.deploy_token("player_3", 4, (21, 21))   # Green

    board_map = AIObserver.get_board_map(game_state, "player_0")
    print(board_map)

    # Check for different player symbols
    assert " C " in board_map  # Cyan (own token, uppercase)
    assert " m " in board_map  # Magenta (enemy, lowercase)
    assert " y " in board_map  # Yellow (enemy, lowercase)
    assert " g " in board_map  # Green (enemy, lowercase)

    print("\n✓ Test passed: Multi-player observation works\n")


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "AI OBSERVATION MODULE - MANUAL TESTS" + " " * 17 + "║")
    print("╚" + "=" * 68 + "╝")
    print("\n")

    tests = [
        test_basic_observation,
        test_board_map,
        test_available_actions,
        test_victory_conditions,
        test_situation_report,
        test_multi_player_game,
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
