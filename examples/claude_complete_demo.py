"""
Complete Demo: Claude AI Player - Observation + Action Execution

This script demonstrates the complete workflow for an AI player:
1. Observe the game state
2. Analyze available actions
3. Choose and execute actions
4. Handle results and continue playing
"""
import sys
sys.path.insert(0, '/home/user/race-to-the-crystal')

from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_observation import AIObserver
from game.ai_actions import (
    AIActionExecutor,
    MoveAction,
    AttackAction,
    DeployAction,
    EndTurnAction,
)
from shared.enums import PlayerColor


def create_game() -> GameState:
    """Create a 2-player game."""
    game_state = GameState()

    # Add players
    game_state.add_player("claude_ai", "Claude (AI)", PlayerColor.CYAN)
    game_state.add_player("human", "Human Player", PlayerColor.MAGENTA)

    # Start game
    game_state.start_game()

    # Initialize generators
    for i, pos in enumerate(game_state.board.get_generator_positions()):
        game_state.generators.append(Generator(id=i, position=pos))

    # Initialize crystal
    game_state.crystal = Crystal(position=game_state.board.get_crystal_position())

    return game_state


def claude_play_turn(game_state: GameState, player_id: str):
    """
    Simulate Claude playing one complete turn.

    This demonstrates:
    1. Getting situation report
    2. Analyzing available actions
    3. Choosing an action (simple strategy for demo)
    4. Executing the action
    5. Handling the result
    """
    executor = AIActionExecutor()

    print("\n" + "=" * 70)
    print("CLAUDE'S TURN - PHASE 1: OBSERVATION")
    print("=" * 70 + "\n")

    # Step 1: Get situation report
    report = AIObserver.get_situation_report(game_state, player_id)
    print(report)

    # Step 2: Get available actions
    actions_data = AIObserver.list_available_actions(game_state, player_id)

    if not actions_data["actions"]:
        print("\nNo actions available!")
        return

    print("\n" + "=" * 70)
    print("CLAUDE'S TURN - PHASE 2: DECISION MAKING")
    print("=" * 70 + "\n")

    # Simple strategy for demo: Deploy if no tokens, otherwise move toward center, then end turn
    chosen_action = None
    strategy_reason = ""

    deployed_tokens = [
        t for t in game_state.tokens.values()
        if t.player_id == player_id and t.is_deployed
    ]

    if not deployed_tokens:
        # No tokens deployed - deploy one
        deploy_actions = [a for a in actions_data["actions"] if a["type"] == "DEPLOY"]
        if deploy_actions:
            # Deploy strongest available token
            for health in [10, 8, 6, 4]:
                deploy = next((a for a in deploy_actions if a["health_value"] == health), None)
                if deploy:
                    chosen_action = DeployAction(
                        health_value=deploy["health_value"],
                        position=tuple(deploy["positions"][0])
                    )
                    strategy_reason = f"Deploy {health}hp token to start advancing"
                    break
    else:
        # Have tokens - try to move toward crystal or attack
        move_actions = [a for a in actions_data["actions"] if a["type"] == "MOVE"]
        attack_actions = [a for a in actions_data["actions"] if a["type"] == "ATTACK"]

        if attack_actions:
            # Prioritize attacks
            attack = attack_actions[0]
            chosen_action = AttackAction(
                attacker_id=attack["attacker_id"],
                defender_id=attack["defender_id"]
            )
            strategy_reason = f"Attack enemy token for {attack['damage']} damage"
        elif move_actions:
            # Move first token toward center
            move = move_actions[0]
            chosen_action = MoveAction(
                token_id=move["token_id"],
                destination=tuple(move["valid_destinations"][0])
            )
            strategy_reason = f"Move token #{move['token_id']} toward objective"
        else:
            # No moves or attacks available, end turn
            chosen_action = EndTurnAction()
            strategy_reason = "No actions available, end turn"

    if not chosen_action:
        chosen_action = EndTurnAction()
        strategy_reason = "Default: end turn"

    print(f"Claude's Strategy: {strategy_reason}")
    print(f"Chosen Action: {chosen_action.action_type}")
    print(f"Action Details: {chosen_action.to_dict()}")

    print("\n" + "=" * 70)
    print("CLAUDE'S TURN - PHASE 3: ACTION EXECUTION")
    print("=" * 70 + "\n")

    # Step 3: Validate action
    is_valid, validation_msg = executor.validate_action(chosen_action, game_state, player_id)
    print(f"Validation: {'✓ VALID' if is_valid else '✗ INVALID'}")
    print(f"Message: {validation_msg}\n")

    if not is_valid:
        print("Action was invalid! Ending turn instead.")
        chosen_action = EndTurnAction()

    # Step 4: Execute action
    success, execution_msg, result_data = executor.execute_action(
        chosen_action, game_state, player_id
    )

    print(f"Execution: {'✓ SUCCESS' if success else '✗ FAILED'}")
    print(f"Result:\n{execution_msg}")

    if result_data:
        print(f"\nResult Data: {result_data}")

    # Step 5: If not end turn, end the turn now
    if not isinstance(chosen_action, EndTurnAction):
        print("\n" + "-" * 70)
        print("Ending turn...")
        print("-" * 70 + "\n")

        end_action = EndTurnAction()
        success, msg, data = executor.execute_action(end_action, game_state, player_id)
        print(msg)


def main():
    """
    Run a complete demo of Claude playing multiple turns.

    This shows the complete integration of observation and action execution.
    """
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 12 + "COMPLETE CLAUDE AI PLAYER DEMO" + " " * 26 + "║")
    print("╚" + "=" * 68 + "╝")
    print("\nThis demo shows Claude observing game state and executing actions.")
    print("Claude will play 3 turns demonstrating the complete API workflow.\n")

    # Create game
    game_state = create_game()
    claude_id = "claude_ai"

    # Play 3 turns as Claude
    for turn_num in range(1, 4):
        print("\n" + "█" * 70)
        print(f"█ TURN {turn_num}")
        print("█" * 70)

        # Make sure it's Claude's turn
        if game_state.current_turn_player_id != claude_id:
            # Skip to Claude's turn
            game_state.current_turn_player_id = claude_id

        # Play Claude's turn
        claude_play_turn(game_state, claude_id)

        # Add some spacing
        print("\n")

    # Final summary
    print("\n" + "=" * 70)
    print("DEMO COMPLETE - API CAPABILITIES DEMONSTRATED")
    print("=" * 70)
    print("\nWhat Claude can do with this API:")
    print("  ✓ Observe complete game state as formatted text")
    print("  ✓ See all available actions with descriptions")
    print("  ✓ Choose actions based on strategy")
    print("  ✓ Validate actions before execution")
    print("  ✓ Execute actions with detailed feedback")
    print("  ✓ Handle results and adapt strategy")
    print("  ✓ Play complete games without visual rendering")
    print("\nPhases 1 & 2 Complete!")
    print("  • Phase 1: Observation Module ✓")
    print("  • Phase 2: Action Execution Module ✓")
    print("\nNext: Phase 3 - Unified ClaudeGameInterface class")
    print()


if __name__ == "__main__":
    main()
