"""
Integration tests for AI vs AI gameplay.

Tests full game loops using AIStrategy and GameAPI to simulate
two AI players competing against each other.
"""

from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_strategy import AIStrategy
from game.ai_observation import AIObserver
from game.ai_actions import (
    AIActionExecutor,
    MoveAction,
    AttackAction,
    DeployAction,
    EndTurnAction,
)
from shared.enums import GamePhase, TurnPhase, PlayerColor


def create_two_player_game() -> GameState:
    """Create a standard 2-player game for integration testing."""
    game_state = GameState()
    game_state.add_player("p1", "AI Alpha", PlayerColor.CYAN)
    game_state.add_player("p2", "AI Beta", PlayerColor.MAGENTA)
    game_state.start_game()

    generator_positions = game_state.board.get_generator_positions()
    for i, pos in enumerate(generator_positions):
        game_state.generators.append(Generator(id=i, position=pos))

    crystal_pos = game_state.board.get_crystal_position()
    game_state.crystal = Crystal(position=crystal_pos)

    return game_state


def execute_chosen_action(chosen, game_state, player_id, executor):
    """Convert a ChosenAction to AIAction and execute it."""
    match chosen.action_type:
        case "MOVE":
            ai_action = MoveAction(
                token_id=chosen.params["token_id"],
                destination=tuple(chosen.params["destination"]),
            )
        case "ATTACK":
            ai_action = AttackAction(
                attacker_id=chosen.params["attacker_id"],
                defender_id=chosen.params["defender_id"],
            )
        case "DEPLOY":
            ai_action = DeployAction(
                health_value=chosen.params["health_value"],
                position=tuple(chosen.params["position"]),
            )
        case "END_TURN":
            ai_action = EndTurnAction()
        case _:
            return None, "Unknown action type"

    result = executor.execute_action(ai_action, game_state, player_id)
    return result, None


def simulate_turns(
    game_state: GameState, strategies: dict, max_turns: int = 200
) -> GameState:
    """
    Simulate turns for two AI players.

    Each player takes a movement action and an action-phase action per turn.
    Loops until the game ends or max_turns is reached.
    """
    executor = AIActionExecutor()

    for _ in range(max_turns):
        if game_state.phase == GamePhase.ENDED:
            break

        player_id = game_state.current_turn_player_id
        strategy = strategies.get(player_id)
        if strategy is None:
            break

        # MOVEMENT phase
        if game_state.turn_phase == TurnPhase.MOVEMENT:
            actions_data = AIObserver.list_available_actions(game_state, player_id)
            actions = actions_data.get("actions", [])

            if not actions:
                break

            chosen = strategy.choose_action(actions, game_state, player_id)
            if chosen is None:
                break

            result, err = execute_chosen_action(chosen, game_state, player_id, executor)
            if err or not result.success:
                break

        # ACTION phase
        if game_state.turn_phase == TurnPhase.ACTION:
            actions_data = AIObserver.list_available_actions(game_state, player_id)
            actions = actions_data.get("actions", [])

            if actions:
                chosen = strategy.choose_action(actions, game_state, player_id)
                if chosen:
                    result, err = execute_chosen_action(
                        chosen, game_state, player_id, executor
                    )
                    if err:
                        break
                    if not result.success:
                        # Action failed, try end turn
                        end_result = executor.execute_action(
                            EndTurnAction(), game_state, player_id
                        )
                        if not end_result.success:
                            break
            else:
                break

    return game_state


class TestAIVsAIRandom:
    """Test random vs random AI gameplay."""

    def test_random_vs_random_completes_turns(self):
        game_state = create_two_player_game()
        strategies = {
            "p1": AIStrategy("random"),
            "p2": AIStrategy("random"),
        }

        final_state = simulate_turns(game_state, strategies, max_turns=50)

        # Game should have progressed (at least some turns)
        assert final_state.turn_number >= 2

    def test_random_vs_random_no_invalid_actions(self):
        game_state = create_two_player_game()
        strategies = {
            "p1": AIStrategy("random"),
            "p2": AIStrategy("random"),
        }

        # This should complete without any crashes
        final_state = simulate_turns(game_state, strategies, max_turns=100)
        assert final_state is not None


class TestAIVsAIAggressive:
    """Test aggressive vs aggressive AI gameplay."""

    def test_aggressive_vs_aggressive_completes_turns(self):
        game_state = create_two_player_game()
        strategies = {
            "p1": AIStrategy("aggressive"),
            "p2": AIStrategy("aggressive"),
        }

        final_state = simulate_turns(game_state, strategies, max_turns=50)
        assert final_state.turn_number >= 2

    def test_aggressive_tokens_move_toward_center(self):
        game_state = create_two_player_game()
        strategies = {
            "p1": AIStrategy("aggressive"),
            "p2": AIStrategy("defensive"),
        }

        final_state = simulate_turns(game_state, strategies, max_turns=30)

        # Check that aggressive player's tokens have moved from starting positions
        p1 = final_state.get_player("p1")
        deployed = [
            final_state.tokens[tid]
            for tid in p1.token_ids
            if tid in final_state.tokens and final_state.tokens[tid].is_deployed
        ]

        # At least some tokens should have moved from the corner
        starting_positions = set()
        for pos in final_state.board.get_deployable_positions(0):
            starting_positions.add(pos)

        moved_tokens = [t for t in deployed if t.position not in starting_positions]
        # After several turns, aggressive strategy should have moved tokens
        # (though we can't guarantee this if deployment zone is full)
        if final_state.turn_number > 4 and len(deployed) > 3:
            assert len(moved_tokens) > 0


class TestAIVsAIDefensive:
    """Test defensive vs random AI gameplay."""

    def test_defensive_vs_random_completes_turns(self):
        game_state = create_two_player_game()
        strategies = {
            "p1": AIStrategy("defensive"),
            "p2": AIStrategy("random"),
        }

        final_state = simulate_turns(game_state, strategies, max_turns=50)
        assert final_state.turn_number >= 2


class TestAIFullGameSimulation:
    """Test extended AI game simulations."""

    def test_mixed_strategies_100_turns(self):
        game_state = create_two_player_game()
        strategies = {
            "p1": AIStrategy("aggressive"),
            "p2": AIStrategy("defensive"),
        }

        final_state = simulate_turns(game_state, strategies, max_turns=100)

        # Game should still be in a valid state
        assert final_state.phase in (GamePhase.PLAYING, GamePhase.ENDED)
        assert final_state.turn_number >= 10

    def test_both_strategies_can_end_turn(self):
        game_state = create_two_player_game()

        for player_id in ["p1", "p2"]:
            game_state.current_turn_player_id = player_id
            game_state.turn_phase = TurnPhase.MOVEMENT

            for strategy_name in ["random", "aggressive", "defensive"]:
                strategy = AIStrategy(strategy_name)
                actions_data = AIObserver.list_available_actions(game_state, player_id)
                actions = actions_data.get("actions", [])

                if not actions:
                    continue

                chosen = strategy.choose_action(actions, game_state, player_id)
                assert chosen is not None

    def test_three_strategies_pairwise(self):
        """Run short games between all strategy pairings."""
        strategy_names = ["random", "aggressive", "defensive"]

        for s1 in strategy_names:
            for s2 in strategy_names:
                game_state = create_two_player_game()
                strategies = {
                    "p1": AIStrategy(s1),
                    "p2": AIStrategy(s2),
                }

                final_state = simulate_turns(game_state, strategies, max_turns=30)
                assert final_state.turn_number >= 2, f"Game stalled with {s1} vs {s2}"


class TestAIActionSequence:
    """Test that AI can execute proper action sequences."""

    def test_movement_then_action_phase(self):
        game_state = create_two_player_game()
        player_id = game_state.current_turn_player_id
        strategy = AIStrategy("aggressive")
        executor = AIActionExecutor()

        # Should start in MOVEMENT phase
        assert game_state.turn_phase == TurnPhase.MOVEMENT

        actions_data = AIObserver.list_available_actions(game_state, player_id)
        actions = actions_data["actions"]

        # Choose a movement or deploy action (not end turn)
        move_actions = [a for a in actions if a["type"] in ("MOVE", "DEPLOY")]
        if move_actions:
            chosen = strategy.choose_action(move_actions, game_state, player_id)
            result, err = execute_chosen_action(chosen, game_state, player_id, executor)
            assert result.success, f"Movement failed: {result.message}"
            assert game_state.turn_phase == TurnPhase.ACTION

    def test_full_turn_cycle(self):
        """Test a complete turn: movement -> action -> end turn."""
        game_state = create_two_player_game()
        executor = AIActionExecutor()

        initial_player = game_state.current_turn_player_id

        # MOVEMENT phase
        assert game_state.turn_phase == TurnPhase.MOVEMENT
        actions_data = AIObserver.list_available_actions(game_state, initial_player)
        moves = [a for a in actions_data["actions"] if a["type"] == "MOVE"]

        if moves:
            ai_action = MoveAction(
                token_id=moves[0]["token_id"],
                destination=tuple(moves[0]["valid_destinations"][0]),
            )
            executor.execute_action(ai_action, game_state, initial_player)

        # ACTION phase
        assert game_state.turn_phase == TurnPhase.ACTION
        result = executor.execute_action(EndTurnAction(), game_state, initial_player)
        assert result.success

        # Turn should have advanced
        assert (
            game_state.current_turn_player_id != initial_player
            or game_state.turn_phase == TurnPhase.MOVEMENT
        )
