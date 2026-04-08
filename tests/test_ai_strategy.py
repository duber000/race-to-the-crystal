"""
Unit tests for AI Strategy module.
"""

import pytest
from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_strategy import AIStrategy, ChosenAction, CRYSTAL_POSITION
from game.ai_observation import AIObserver
from game.ai_actions import AIActionExecutor, EndTurnAction
from shared.enums import PlayerColor, TurnPhase


def create_test_game(num_players: int = 2) -> GameState:
    """Helper function to create a test game state."""
    game_state = GameState()
    num_players = max(2, min(4, num_players))

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

    game_state.start_game()

    generator_positions = game_state.board.get_generator_positions()
    for i, pos in enumerate(generator_positions):
        generator = Generator(id=i, position=pos)
        game_state.generators.append(generator)

    crystal_pos = game_state.board.get_crystal_position()
    game_state.crystal = Crystal(position=crystal_pos)

    return game_state


def get_movement_actions(game_state: GameState, player_id: str) -> list[dict]:
    """Get only MOVE actions from available actions."""
    actions_data = AIObserver.list_available_actions(game_state, player_id)
    return [a for a in actions_data["actions"] if a["type"] == "MOVE"]


class TestChosenAction:
    def test_creation(self):
        action = ChosenAction("MOVE", {"token_id": 5, "destination": [12, 12]})
        assert action.action_type == "MOVE"
        assert action.params["token_id"] == 5

    def test_default_params(self):
        action = ChosenAction("END_TURN")
        assert action.action_type == "END_TURN"
        assert action.params == {}

    def test_repr(self):
        action = ChosenAction("ATTACK", {"attacker_id": 1, "defender_id": 2})
        assert "ATTACK" in repr(action)


class TestAIStrategyCreation:
    def test_random_strategy(self):
        strategy = AIStrategy("random")
        assert strategy.strategy_name == "random"

    def test_aggressive_strategy(self):
        strategy = AIStrategy("aggressive")
        assert strategy.strategy_name == "aggressive"

    def test_defensive_strategy(self):
        strategy = AIStrategy("defensive")
        assert strategy.strategy_name == "defensive"

    def test_unknown_strategy_defaults_to_random(self):
        strategy = AIStrategy("unknown")
        assert strategy.strategy_name == "random"

    def test_empty_strategy_defaults_to_random(self):
        strategy = AIStrategy("")
        assert strategy.strategy_name == "random"


class TestRandomStrategy:
    def test_chooses_from_available_actions(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        strategy = AIStrategy("random")

        actions_data = AIObserver.list_available_actions(game_state, player_id)
        actions = actions_data["actions"]

        chosen = strategy.choose_action(actions, game_state, player_id)
        assert chosen is not None
        assert chosen.action_type in ("MOVE", "DEPLOY", "END_TURN")

    def test_returns_none_on_empty_actions(self):
        strategy = AIStrategy("random")
        result = strategy.choose_action([], None, None)
        assert result is None

    def test_resolves_move_destination(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        moves = get_movement_actions(game_state, player_id)

        if not moves:
            pytest.skip("No move actions available")

        strategy = AIStrategy("random")
        chosen = strategy.choose_action(moves, game_state, player_id)

        assert chosen.action_type == "MOVE"
        assert "destination" in chosen.params
        assert "token_id" in chosen.params
        dest = chosen.params["destination"]
        assert len(dest) == 2

    def test_resolves_deploy_position(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        actions_data = AIObserver.list_available_actions(game_state, player_id)
        deploys = [a for a in actions_data["actions"] if a["type"] == "DEPLOY"]

        if not deploys:
            pytest.skip("No deploy actions available")

        strategy = AIStrategy("random")
        chosen = strategy.choose_action(deploys, game_state, player_id)

        assert chosen.action_type == "DEPLOY"
        assert "health_value" in chosen.params
        assert "position" in chosen.params
        pos = chosen.params["position"]
        assert len(pos) == 2


class TestAggressiveStrategy:
    def test_prefers_attack_over_move(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        strategy = AIStrategy("aggressive")

        # Move a token adjacent to an enemy
        my_tokens = [
            game_state.tokens[tid]
            for tid in game_state.get_player(player_id).token_ids
            if game_state.tokens[tid].is_deployed
        ]
        enemy_player_id = [pid for pid in game_state.players if pid != player_id][0]
        enemy_tokens = [
            game_state.tokens[tid]
            for tid in game_state.get_player(enemy_player_id).token_ids
            if game_state.tokens[tid].is_deployed
        ]

        if not my_tokens or not enemy_tokens:
            pytest.skip("No deployed tokens")

        my_token = my_tokens[0]
        enemy_token = enemy_tokens[0]

        # Teleport my token adjacent to enemy
        adj_pos = (enemy_token.position[0] + 1, enemy_token.position[1])
        game_state.board.clear_occupant(my_token.position, my_token.id)
        my_token.move_to(adj_pos)
        game_state.board.set_occupant(adj_pos, my_token.id)

        # Should be in MOVEMENT phase, move first then check attacks
        actions_data = AIObserver.list_available_actions(game_state, player_id)
        move_actions = [a for a in actions_data["actions"] if a["type"] == "MOVE"]

        if move_actions:
            chosen = strategy.choose_action(
                actions_data["actions"], game_state, player_id
            )
            # In movement phase, aggressive will pick MOVE (no attacks available yet)
            assert chosen.action_type in ("MOVE", "DEPLOY")

        # Now transition to ACTION phase and check attack preference
        if game_state.turn_phase == TurnPhase.MOVEMENT:
            executor = AIActionExecutor()
            first_move = move_actions[0]
            from game.ai_actions import MoveAction

            move_action = MoveAction(
                token_id=first_move["token_id"],
                destination=tuple(first_move["valid_destinations"][0]),
            )
            executor.execute_action(move_action, game_state, player_id)

        # Now in ACTION phase
        actions_data = AIObserver.list_available_actions(game_state, player_id)
        attacks = [a for a in actions_data["actions"] if a["type"] == "ATTACK"]

        if attacks:
            chosen = strategy.choose_action(
                actions_data["actions"], game_state, player_id
            )
            assert chosen.action_type == "ATTACK"

    def test_moves_toward_crystal(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        strategy = AIStrategy("aggressive")

        moves = get_movement_actions(game_state, player_id)
        if not moves:
            pytest.skip("No move actions")

        chosen = strategy.choose_action(moves, game_state, player_id)
        assert chosen.action_type == "MOVE"
        assert chosen.params["destination"] is not None

    def test_prefers_killing_attack(self):
        strategy = AIStrategy("aggressive")

        # The logic: attacks with will_kill=True should be preferred
        attacks = [
            {
                "type": "ATTACK",
                "attacker_id": 1,
                "defender_id": 10,
                "damage": 3,
                "will_kill": False,
            },
            {
                "type": "ATTACK",
                "attacker_id": 2,
                "defender_id": 20,
                "damage": 2,
                "will_kill": True,
            },
            {
                "type": "ATTACK",
                "attacker_id": 3,
                "defender_id": 30,
                "damage": 5,
                "will_kill": False,
            },
        ]

        chosen = strategy._best_attack(attacks)
        assert chosen.action_type == "ATTACK"
        assert chosen.params["defender_id"] == 20

    def test_prefers_highest_damage_when_no_kill(self):
        strategy = AIStrategy("aggressive")

        attacks = [
            {
                "type": "ATTACK",
                "attacker_id": 1,
                "defender_id": 10,
                "damage": 2,
                "will_kill": False,
            },
            {
                "type": "ATTACK",
                "attacker_id": 2,
                "defender_id": 20,
                "damage": 5,
                "will_kill": False,
            },
            {
                "type": "ATTACK",
                "attacker_id": 3,
                "defender_id": 30,
                "damage": 3,
                "will_kill": False,
            },
        ]

        chosen = strategy._best_attack(attacks)
        assert chosen.params["defender_id"] == 20

    def test_deploys_highest_health(self):
        strategy = AIStrategy("aggressive")

        deploys = [
            {"type": "DEPLOY", "health_value": 6, "positions": [(0, 0)]},
            {"type": "DEPLOY", "health_value": 10, "positions": [(0, 1)]},
            {"type": "DEPLOY", "health_value": 4, "positions": [(0, 2)]},
        ]

        chosen = strategy._best_deploy(deploys)
        assert chosen.params["health_value"] == 10


class TestDefensiveStrategy:
    def test_prefers_deploy(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        strategy = AIStrategy("defensive")

        actions_data = AIObserver.list_available_actions(game_state, player_id)
        deploys = [a for a in actions_data["actions"] if a["type"] == "DEPLOY"]

        if not deploys:
            pytest.skip("No deploy actions")

        # Run many times to check the 50% deploy preference
        deploy_count = 0
        trials = 100
        for _ in range(trials):
            chosen = strategy.choose_action(
                actions_data["actions"], game_state, player_id
            )
            if chosen.action_type == "DEPLOY":
                deploy_count += 1

        # With 50% chance, we expect roughly 40-60 deploys out of 100
        # Use generous bounds to avoid flaky tests
        assert deploy_count > 10
        assert deploy_count < 90

    def test_moves_toward_crystal_when_no_deploy(self):
        strategy = AIStrategy("defensive")

        moves = [
            {
                "type": "MOVE",
                "token_id": 1,
                "valid_destinations": [[0, 0], [12, 12]],
            },
        ]

        game_state = create_test_game()
        player_id = game_state.current_turn_player_id

        chosen = strategy._best_move(
            moves, game_state, player_id, prioritize_crystal=True
        )
        assert chosen.action_type == "MOVE"
        # Should pick the destination closer to crystal (12,12)
        assert chosen.params["destination"] == [12, 12]


class TestGeneratorAwareness:
    def test_generators_included_in_objectives(self):
        strategy = AIStrategy("aggressive")
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id

        objectives = strategy._get_objectives(game_state, player_id)
        # Crystal is always in objectives
        assert CRYSTAL_POSITION in objectives
        # Generators should also be in objectives (4 generators)
        assert len(objectives) >= 5

    def test_capturing_generator_prioritized(self):
        strategy = AIStrategy("aggressive")
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id

        # Mark a generator as being captured by this player
        game_state.generators[0].capturing_player_id = player_id
        game_state.generators[0].turns_held = 1

        objectives = strategy._get_objectives(game_state, player_id)
        # The generator being captured should be first (before crystal)
        assert objectives[0] == game_state.generators[0].position

    def test_disabled_generators_excluded(self):
        strategy = AIStrategy("aggressive")
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id

        # Disable a generator
        game_state.generators[0].is_disabled = True

        objectives = strategy._get_objectives(game_state, player_id)
        assert game_state.generators[0].position not in objectives

    def test_crystal_only_mode(self):
        strategy = AIStrategy("defensive")
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id

        objectives = strategy._get_objectives(game_state, player_id, crystal_only=True)
        assert objectives == [CRYSTAL_POSITION]

    def test_move_toward_generator(self):
        strategy = AIStrategy("aggressive")
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id

        # Create a scenario where a token has destinations near a generator
        gen = game_state.generators[0]
        moves = [
            {
                "type": "MOVE",
                "token_id": 1,
                "valid_destinations": [[0, 0], list(gen.position)],
            },
        ]

        chosen = strategy._best_move(moves, game_state, player_id)
        # Should prefer the generator position over (0,0) since gen is
        # in objectives and (0,0) is far from everything
        assert chosen.params["destination"] == list(gen.position)


class TestMovementScoring:
    def test_destination_near_crystal_scores_better(self):
        strategy = AIStrategy("aggressive")

        objectives = [CRYSTAL_POSITION]
        near_crystal = strategy._score_destination((11, 11), objectives, None)
        far_from_crystal = strategy._score_destination((0, 0), objectives, None)

        assert near_crystal < far_from_crystal

    def test_damaged_token_gets_slight_bonus(self):
        strategy = AIStrategy("aggressive")
        from game.token import Token

        objectives = [CRYSTAL_POSITION]

        healthy_token = Token(
            id=1, player_id="p1", health=10, max_health=10, position=(5, 5)
        )
        damaged_token = Token(
            id=2, player_id="p1", health=4, max_health=8, position=(5, 5)
        )

        healthy_score = strategy._score_destination((6, 6), objectives, healthy_token)
        damaged_score = strategy._score_destination((6, 6), objectives, damaged_token)

        # Damaged token should have slightly better (lower) score
        assert damaged_score < healthy_score

    def test_nearest_objective_used(self):
        strategy = AIStrategy("aggressive")

        # Two objectives: one far, one near
        objectives = [(0, 0), (20, 20)]

        near_score = strategy._score_destination((19, 19), objectives, None)
        far_score = strategy._score_destination((5, 5), objectives, None)

        # (19,19) is closer to (20,20) than (5,5) is to (0,0)
        assert near_score < far_score


class TestEndToEndStrategyActions:
    def test_aggressive_action_is_valid(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        strategy = AIStrategy("aggressive")
        executor = AIActionExecutor()

        actions_data = AIObserver.list_available_actions(game_state, player_id)
        chosen = strategy.choose_action(actions_data["actions"], game_state, player_id)

        assert chosen is not None

        # Convert ChosenAction to AIAction
        from game.ai_actions import MoveAction, DeployAction

        match chosen.action_type:
            case "MOVE":
                ai_action = MoveAction(
                    token_id=chosen.params["token_id"],
                    destination=tuple(chosen.params["destination"]),
                )
            case "DEPLOY":
                ai_action = DeployAction(
                    health_value=chosen.params["health_value"],
                    position=tuple(chosen.params["position"]),
                )
            case "END_TURN":
                ai_action = EndTurnAction()
            case _:
                pytest.fail(f"Unexpected action type: {chosen.action_type}")

        result = executor.execute_action(ai_action, game_state, player_id)
        assert result.success, f"Action failed: {result.message}"

    def test_random_action_is_valid(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        strategy = AIStrategy("random")
        executor = AIActionExecutor()

        actions_data = AIObserver.list_available_actions(game_state, player_id)
        chosen = strategy.choose_action(actions_data["actions"], game_state, player_id)

        assert chosen is not None

        from game.ai_actions import MoveAction, DeployAction

        match chosen.action_type:
            case "MOVE":
                ai_action = MoveAction(
                    token_id=chosen.params["token_id"],
                    destination=tuple(chosen.params["destination"]),
                )
            case "DEPLOY":
                ai_action = DeployAction(
                    health_value=chosen.params["health_value"],
                    position=tuple(chosen.params["position"]),
                )
            case "END_TURN":
                ai_action = EndTurnAction()
            case _:
                pytest.fail(f"Unexpected action type: {chosen.action_type}")

        result = executor.execute_action(ai_action, game_state, player_id)
        assert result.success, f"Action failed: {result.message}"

    def test_defensive_action_is_valid(self):
        game_state = create_test_game()
        player_id = game_state.current_turn_player_id
        strategy = AIStrategy("defensive")
        executor = AIActionExecutor()

        actions_data = AIObserver.list_available_actions(game_state, player_id)
        chosen = strategy.choose_action(actions_data["actions"], game_state, player_id)

        assert chosen is not None

        from game.ai_actions import MoveAction, DeployAction

        match chosen.action_type:
            case "MOVE":
                ai_action = MoveAction(
                    token_id=chosen.params["token_id"],
                    destination=tuple(chosen.params["destination"]),
                )
            case "DEPLOY":
                ai_action = DeployAction(
                    health_value=chosen.params["health_value"],
                    position=tuple(chosen.params["position"]),
                )
            case "END_TURN":
                ai_action = EndTurnAction()
            case _:
                pytest.fail(f"Unexpected action type: {chosen.action_type}")

        result = executor.execute_action(ai_action, game_state, player_id)
        assert result.success, f"Action failed: {result.message}"
