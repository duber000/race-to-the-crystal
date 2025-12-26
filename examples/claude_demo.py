"""
Demo: How Claude (or any AI) would use the AI Observation API

This script demonstrates the complete workflow for an AI player using the
observation module to play Race to the Crystal.
"""
import sys
sys.path.insert(0, '/home/user/race-to-the-crystal')

from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_observation import AIObserver
from shared.enums import PlayerColor


def create_game() -> GameState:
    """Create a 2-player game."""
    game_state = GameState()

    # Add players
    game_state.add_player("player_0", "Player 1", PlayerColor.CYAN)
    game_state.add_player("player_1", "Player 2", PlayerColor.MAGENTA)

    # Start game
    game_state.start_game()

    # Initialize generators
    for i, pos in enumerate(game_state.board.get_generator_positions()):
        game_state.generators.append(Generator(id=i, position=pos))

    # Initialize crystal
    game_state.crystal = Crystal(position=game_state.board.get_crystal_position())

    return game_state


def main():
    """
    Demonstrate how Claude would interact with the game.

    This shows the complete game state observation that Claude would receive,
    which contains all the information needed to make strategic decisions.
    """
    print("\n" + "=" * 70)
    print("DEMO: Claude AI Player - Turn 1")
    print("=" * 70 + "\n")

    # Create game
    game_state = create_game()
    claude_player_id = "player_0"

    # This is what Claude would see on their turn:
    print("━" * 70)
    print("WHAT CLAUDE RECEIVES:")
    print("━" * 70)

    situation_report = AIObserver.get_situation_report(game_state, claude_player_id)
    print(situation_report)

    print("\n" + "=" * 70)
    print("CLAUDE'S DECISION PROCESS (example)")
    print("=" * 70 + "\n")

    # Claude would analyze the situation and make decisions like:
    print("Claude analyzes the situation:")
    print("1. I have 20 tokens in reserve, none deployed")
    print("2. The crystal requires 12 tokens to capture")
    print("3. I should start deploying tokens to advance toward the crystal")
    print("4. I'll deploy a 10hp token to start moving toward the center")
    print()

    # Execute Claude's chosen action
    print("Claude chooses: Deploy 10hp token at corner position (0,0)")
    deployed = game_state.deploy_token(claude_player_id, 10, (0, 0))

    if deployed:
        print(f"✓ Successfully deployed token #{deployed.id} at (0,0)")
        print()

        # Show updated state
        print("=" * 70)
        print("UPDATED GAME STATE AFTER DEPLOYMENT:")
        print("=" * 70 + "\n")

        new_report = AIObserver.describe_game_state(game_state, claude_player_id)
        print(new_report)

    print("\n" + "=" * 70)
    print("KEY FEATURES FOR AI PLAYERS:")
    print("=" * 70)
    print("✓ Complete text-based game state observation")
    print("✓ ASCII board map showing all pieces")
    print("✓ List of all valid actions with descriptions")
    print("✓ Victory condition progress tracking")
    print("✓ Full visibility of enemy positions")
    print("✓ Strategic information (generators, crystal status)")
    print("✓ No visual rendering required")
    print()
    print("Claude can use this information to:")
    print("• Plan multi-turn strategies")
    print("• Evaluate tactical options")
    print("• Make informed decisions about movement and combat")
    print("• Track progress toward victory")
    print()


if __name__ == "__main__":
    main()
