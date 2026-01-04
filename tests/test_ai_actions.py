"""
Unit tests for AI Action execution module.
"""
import pytest
from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_actions import (
    AIActionExecutor,
    MoveAction,
    AttackAction,
    DeployAction,
    EndTurnAction,
    ValidationResult,
    ActionResult,
)
from shared.enums import PlayerColor, GamePhase, TurnPhase


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


class TestActionClasses:
    """Test action class creation and serialization."""

    def test_move_action_creation(self):
        """Test creating a MoveAction."""
        action = MoveAction(token_id=5, destination=(10, 12))

        assert action.action_type == "MOVE"
        assert action.token_id == 5
        assert action.destination == (10, 12)

    def test_attack_action_creation(self):
        """Test creating an AttackAction."""
        action = AttackAction(attacker_id=5, defender_id=23)

        assert action.action_type == "ATTACK"
        assert action.attacker_id == 5
        assert action.defender_id == 23

    def test_deploy_action_creation(self):
        """Test creating a DeployAction."""
        action = DeployAction(health_value=10, position=(0, 0))

        assert action.action_type == "DEPLOY"
        assert action.health_value == 10
        assert action.position == (0, 0)

    def test_end_turn_action_creation(self):
        """Test creating an EndTurnAction."""
        action = EndTurnAction()

        assert action.action_type == "END_TURN"

    def test_action_serialization(self):
        """Test action to_dict() methods."""
        move = MoveAction(token_id=5, destination=(10, 12))
        move_dict = move.to_dict()
        assert move_dict["action_type"] == "MOVE"
        assert move_dict["token_id"] == 5
        assert move_dict["destination"] == [10, 12]

        attack = AttackAction(attacker_id=5, defender_id=23)
        attack_dict = attack.to_dict()
        assert attack_dict["action_type"] == "ATTACK"


class TestMoveActionValidation:
    """Test move action validation."""

    def test_valid_move(self):
        """Test validating a valid move."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        # Deploy a token
        token = game_state.deploy_token("player_0", 10, (5, 5))
        game_state.turn_phase = TurnPhase.MOVEMENT

        # Try to move it
        action = MoveAction(token_id=token.id, destination=(5, 6))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert is_valid
        assert "valid" in msg.lower()

    def test_move_wrong_phase(self):
        """Test move fails in wrong phase."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        token = game_state.deploy_token("player_0", 10, (5, 5))
        game_state.turn_phase = TurnPhase.ACTION  # Wrong phase

        action = MoveAction(token_id=token.id, destination=(5, 6))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "wrong phase" in msg.lower()

    def test_move_not_your_token(self):
        """Test move fails when token doesn't belong to player."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        # Deploy token for player_1
        token = game_state.deploy_token("player_1", 10, (23, 23))
        game_state.turn_phase = TurnPhase.MOVEMENT
        game_state.current_turn_player_id = "player_0"

        # Try to move it as player_0
        action = MoveAction(token_id=token.id, destination=(23, 22))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "does not belong to you" in msg.lower()

    def test_move_invalid_destination(self):
        """Test move fails with invalid destination."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        token = game_state.deploy_token("player_0", 10, (5, 5))
        game_state.turn_phase = TurnPhase.MOVEMENT

        # Try to move too far (10hp token has range 1)
        action = MoveAction(token_id=token.id, destination=(10, 10))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "not reachable" in msg.lower()

    def test_move_not_your_turn(self):
        """Test move fails when it's not your turn."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        token = game_state.deploy_token("player_0", 10, (5, 5))
        game_state.turn_phase = TurnPhase.MOVEMENT
        game_state.current_turn_player_id = "player_1"  # Not player_0's turn

        action = MoveAction(token_id=token.id, destination=(5, 6))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "not your turn" in msg.lower()


class TestMoveActionExecution:
    """Test move action execution."""

    def test_execute_valid_move(self):
        """Test executing a valid move."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        token = game_state.deploy_token("player_0", 10, (5, 5))
        game_state.turn_phase = TurnPhase.MOVEMENT

        action = MoveAction(token_id=token.id, destination=(5, 6))
        success, msg, data = executor.execute_action(action, game_state, "player_0")

        assert success
        assert token.position == (5, 6)
        assert data["old_position"] == (5, 5)
        assert data["new_position"] == (5, 6)
        assert game_state.turn_phase == TurnPhase.ACTION

    def test_execute_move_phase_transition(self):
        """Test that move transitions to ACTION phase."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        token = game_state.deploy_token("player_0", 10, (5, 5))
        game_state.turn_phase = TurnPhase.MOVEMENT

        action = MoveAction(token_id=token.id, destination=(5, 6))
        success, msg, data = executor.execute_action(action, game_state, "player_0")

        assert success
        assert game_state.turn_phase == TurnPhase.ACTION


class TestAttackActionValidation:
    """Test attack action validation."""

    def test_valid_attack(self):
        """Test validating a valid attack."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        # Deploy two adjacent tokens
        attacker = game_state.deploy_token("player_0", 10, (5, 5))
        defender = game_state.deploy_token("player_1", 8, (5, 6))
        game_state.turn_phase = TurnPhase.ACTION

        action = AttackAction(attacker_id=attacker.id, defender_id=defender.id)
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert is_valid

    def test_attack_wrong_phase(self):
        """Test attack fails in wrong phase."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        attacker = game_state.deploy_token("player_0", 10, (5, 5))
        defender = game_state.deploy_token("player_1", 8, (5, 6))
        game_state.turn_phase = TurnPhase.MOVEMENT  # Wrong phase

        action = AttackAction(attacker_id=attacker.id, defender_id=defender.id)
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "wrong phase" in msg.lower()

    def test_attack_own_token(self):
        """Test attack fails when targeting own token."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        token1 = game_state.deploy_token("player_0", 10, (5, 5))
        token2 = game_state.deploy_token("player_0", 8, (5, 6))
        game_state.turn_phase = TurnPhase.ACTION

        action = AttackAction(attacker_id=token1.id, defender_id=token2.id)
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "cannot attack your own" in msg.lower()

    def test_attack_not_adjacent(self):
        """Test attack fails when tokens are not adjacent."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        attacker = game_state.deploy_token("player_0", 10, (5, 5))
        defender = game_state.deploy_token("player_1", 8, (10, 10))
        game_state.turn_phase = TurnPhase.ACTION

        action = AttackAction(attacker_id=attacker.id, defender_id=defender.id)
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "not adjacent" in msg.lower()


class TestAttackActionExecution:
    """Test attack action execution."""

    def test_execute_attack_damage(self):
        """Test executing an attack deals correct damage."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        attacker = game_state.deploy_token("player_0", 10, (5, 5))  # 10hp = 5 damage
        defender = game_state.deploy_token("player_1", 8, (5, 6))   # 8hp
        game_state.turn_phase = TurnPhase.ACTION

        action = AttackAction(attacker_id=attacker.id, defender_id=defender.id)
        success, msg, data = executor.execute_action(action, game_state, "player_0")

        assert success
        assert data["damage_dealt"] == 5
        assert defender.health == 3  # 8 - 5 = 3

    def test_execute_attack_kill(self):
        """Test executing an attack that kills the defender."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        attacker = game_state.deploy_token("player_0", 10, (5, 5))  # 10hp = 5 damage
        defender = game_state.deploy_token("player_1", 4, (5, 6))   # 4hp (will be killed)
        game_state.turn_phase = TurnPhase.ACTION

        action = AttackAction(attacker_id=attacker.id, defender_id=defender.id)
        success, msg, data = executor.execute_action(action, game_state, "player_0")

        assert success
        assert data["defender_killed"]
        assert not defender.is_alive


class TestDeployActionValidation:
    """Test deploy action validation."""

    def test_valid_deploy(self):
        """Test validating a valid deployment."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.MOVEMENT

        # Use (1,0) since (0,0)-(0,2) are occupied by auto-deployed tokens
        action = DeployAction(health_value=10, position=(1, 0))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert is_valid

    def test_deploy_wrong_phase(self):
        """Test deploy fails in wrong phase."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.ACTION  # Wrong phase

        action = DeployAction(health_value=10, position=(0, 0))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "wrong phase" in msg.lower()

    def test_deploy_invalid_health(self):
        """Test deploy fails with invalid health value."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.MOVEMENT

        action = DeployAction(health_value=15, position=(0, 0))  # Invalid health
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "invalid health" in msg.lower()

    def test_deploy_occupied_position(self):
        """Test deploy fails when position is occupied."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.deploy_token("player_0", 10, (0, 0))  # Occupy the position
        game_state.turn_phase = TurnPhase.MOVEMENT

        action = DeployAction(health_value=8, position=(0, 0))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "occupied" in msg.lower()

    def test_deploy_invalid_position(self):
        """Test deploy fails at invalid position (not corner)."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.MOVEMENT

        # Try to deploy at center of board (not a valid corner position)
        action = DeployAction(health_value=10, position=(12, 12))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "not a valid deployment location" in msg.lower()


class TestDeployActionExecution:
    """Test deploy action execution."""

    def test_execute_deploy(self):
        """Test executing a deployment."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.MOVEMENT
        initial_reserve = len(game_state.get_reserve_tokens("player_0"))

        # Use (1,0) since (0,0)-(0,2) are occupied by auto-deployed tokens
        action = DeployAction(health_value=10, position=(1, 0))
        success, msg, data = executor.execute_action(action, game_state, "player_0")

        assert success
        assert "new_token_id" in data
        assert data["health_value"] == 10
        assert data["position"] == (1, 0)

        # Check reserve decreased
        final_reserve = len(game_state.get_reserve_tokens("player_0"))
        assert final_reserve == initial_reserve - 1

    def test_execute_deploy_phase_transition(self):
        """Test that deploy transitions to ACTION phase."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.MOVEMENT

        # Use (1,0) since (0,0)-(0,2) are occupied by auto-deployed tokens
        action = DeployAction(health_value=10, position=(1, 0))
        success, msg, data = executor.execute_action(action, game_state, "player_0")

        assert success
        assert game_state.turn_phase == TurnPhase.ACTION


class TestEndTurnActionValidation:
    """Test end turn action validation."""

    def test_valid_end_turn(self):
        """Test validating end turn in ACTION phase."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.ACTION

        action = EndTurnAction()
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert is_valid

    def test_end_turn_wrong_phase(self):
        """Test end turn works in both MOVEMENT and ACTION phases."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        # Can end turn in MOVEMENT phase (to pass)
        game_state.turn_phase = TurnPhase.MOVEMENT
        action = EndTurnAction()
        is_valid, msg = executor.validate_action(action, game_state, "player_0")
        assert is_valid

        # Can also end turn in ACTION phase
        game_state.turn_phase = TurnPhase.ACTION
        is_valid, msg = executor.validate_action(action, game_state, "player_0")
        assert is_valid


class TestEndTurnActionExecution:
    """Test end turn action execution."""

    def test_execute_end_turn(self):
        """Test executing end turn."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.ACTION
        initial_turn = game_state.turn_number
        initial_player = game_state.current_turn_player_id

        action = EndTurnAction()
        success, msg, data = executor.execute_action(action, game_state, "player_0")

        assert success
        # Turn should have advanced or player changed
        assert (game_state.turn_number > initial_turn or
                game_state.current_turn_player_id != initial_player)

    def test_end_turn_advances_turn_number(self):
        """Test that ending turn eventually advances turn number."""
        game_state = create_test_game(2)  # 2 players
        executor = AIActionExecutor()

        initial_turn = game_state.turn_number

        # End turn for both players
        for _ in range(2):
            current_player = game_state.current_turn_player_id
            game_state.turn_phase = TurnPhase.ACTION
            action = EndTurnAction()
            executor.execute_action(action, game_state, current_player)

        # After all players have gone, turn number should increase
        assert game_state.turn_number > initial_turn


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_game_not_started(self):
        """Test actions fail when game is not started."""
        game_state = GameState()
        game_state.add_player("p1", "Player 1", PlayerColor.CYAN)
        # Don't start the game
        executor = AIActionExecutor()

        action = DeployAction(health_value=10, position=(0, 0))
        is_valid, msg = executor.validate_action(action, game_state, "p1")

        assert not is_valid
        assert "not in playing phase" in msg.lower()

    def test_nonexistent_token(self):
        """Test move fails with nonexistent token."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.MOVEMENT

        action = MoveAction(token_id=9999, destination=(5, 5))
        is_valid, msg = executor.validate_action(action, game_state, "player_0")

        assert not is_valid
        assert "does not exist" in msg.lower()

    def test_action_without_player(self):
        """Test action fails when player doesn't exist."""
        game_state = create_test_game()
        executor = AIActionExecutor()

        game_state.turn_phase = TurnPhase.MOVEMENT

        action = DeployAction(health_value=10, position=(0, 0))
        is_valid, msg = executor.validate_action(action, game_state, "nonexistent_player")

        assert not is_valid
        assert "not your turn" in msg.lower()
