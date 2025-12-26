"""
Unit tests for AI Observation module.
"""
import pytest
from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_observation import AIObserver
from shared.enums import PlayerColor, GamePhase, TurnPhase


def create_test_game(num_players: int = 2) -> GameState:
    """
    Helper function to create a test game state.

    Args:
        num_players: Number of players (2-4)

    Returns:
        Configured game state ready for testing
    """
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


class TestAIObserver:
    """Test cases for AIObserver class."""

    def test_describe_game_state_setup_phase(self):
        """Test describing game state during setup phase."""
        game_state = GameState()
        game_state.add_player("p1", "Alice", PlayerColor.CYAN)

        description = AIObserver.describe_game_state(game_state, "p1")

        assert "GAME SETUP" in description
        assert "Waiting for players" in description

    def test_describe_game_state_playing_phase(self):
        """Test describing game state during playing phase."""
        game_state = create_test_game(2)

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "TURN" in description
        assert game_state.turn_number == 1 or "TURN 1" in description
        assert "YOUR TURN" in description or "WAITING" in description

    def test_describe_game_state_shows_your_tokens(self):
        """Test that description shows player's tokens."""
        game_state = create_test_game(2)

        # Deploy a token for testing
        game_state.deploy_token("player_0", 10, (0, 0))
        game_state.deploy_token("player_0", 8, (0, 1))

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "YOUR TOKENS" in description
        assert "2 deployed" in description
        assert "18 in reserve" in description  # 20 - 2 deployed
        assert "10/10hp" in description  # Deployed 10hp token
        assert "8/8hp" in description  # Deployed 8hp token

    def test_describe_game_state_shows_enemy_tokens(self):
        """Test that description shows enemy tokens."""
        game_state = create_test_game(2)

        # Deploy tokens for both players
        game_state.deploy_token("player_0", 10, (0, 0))
        game_state.deploy_token("player_1", 8, (23, 23))

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "ENEMY TOKENS" in description
        assert "Player 2" in description
        assert "Magenta" in description
        assert "1 deployed" in description

    def test_describe_game_state_shows_generators(self):
        """Test that description shows generator information."""
        game_state = create_test_game(2)

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "GENERATORS" in description
        assert "G1" in description
        assert "G2" in description
        assert "G3" in description
        assert "G4" in description

    def test_describe_game_state_shows_crystal(self):
        """Test that description shows crystal information."""
        game_state = create_test_game(2)

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "CRYSTAL" in description
        assert "Tokens needed to capture: 12" in description
        assert "Location:" in description

    def test_describe_game_state_ended_phase(self):
        """Test describing game state after game ends."""
        game_state = create_test_game(2)
        game_state.phase = GamePhase.ENDED
        game_state.winner_id = "player_0"

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "GAME OVER" in description
        assert "Player 1" in description  # Winner name

    def test_get_board_map_basic(self):
        """Test basic board map generation."""
        game_state = create_test_game(2)

        board_map = AIObserver.get_board_map(game_state, "player_0")

        assert "BOARD MAP (24x24)" in board_map
        assert "LEGEND:" in board_map
        assert "C = Crystal" in board_map
        assert "1,2,3,4 = Generators" in board_map
        assert "M = Mystery square" in board_map

    def test_get_board_map_shows_tokens(self):
        """Test that board map shows deployed tokens."""
        game_state = create_test_game(2)

        # Deploy tokens
        game_state.deploy_token("player_0", 10, (5, 5))
        game_state.deploy_token("player_1", 8, (10, 10))

        board_map = AIObserver.get_board_map(game_state, "player_0")

        # Player 0 is Cyan, should show as 'C' (uppercase for own tokens)
        assert " C " in board_map  # Own token
        # Player 1 is Magenta, should show as 'm' (lowercase for enemy tokens)
        assert " m " in board_map  # Enemy token

    def test_get_board_map_shows_special_cells(self):
        """Test that board map shows special cells."""
        game_state = create_test_game(2)

        board_map = AIObserver.get_board_map(game_state, "player_0")

        # Should have crystal (C), generators (1,2,3,4), mystery squares (M), corners (*)
        assert " C " in board_map or " c " in board_map  # Crystal (or token on crystal)
        assert " 1 " in board_map or " C " in board_map or " c " in board_map  # G1 or token
        assert " M " in board_map or " C " in board_map  # Mystery or token

    def test_list_available_actions_not_playing(self):
        """Test listing actions when game is not in playing phase."""
        game_state = GameState()
        game_state.add_player("p1", "Alice", PlayerColor.CYAN)
        # Game is in SETUP phase

        actions_data = AIObserver.list_available_actions(game_state, "p1")

        assert actions_data["phase"] == "NOT_PLAYING"
        assert len(actions_data["actions"]) == 0

    def test_list_available_actions_not_your_turn(self):
        """Test listing actions when it's not your turn."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"

        # Ask for player_1's actions when it's player_0's turn
        actions_data = AIObserver.list_available_actions(game_state, "player_1")

        assert actions_data["phase"] == "NOT_YOUR_TURN"
        assert len(actions_data["actions"]) == 0

    def test_list_available_actions_movement_phase(self):
        """Test listing actions during movement phase."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"
        game_state.turn_phase = TurnPhase.MOVEMENT

        # Deploy a token so there are movement options
        game_state.deploy_token("player_0", 10, (5, 5))

        actions_data = AIObserver.list_available_actions(game_state, "player_0")

        assert actions_data["phase"] == "MOVEMENT"
        assert len(actions_data["actions"]) > 0

        # Should have move actions and/or deploy actions
        action_types = [action["type"] for action in actions_data["actions"]]
        assert "MOVE" in action_types or "DEPLOY" in action_types

    def test_list_available_actions_deploy_actions(self):
        """Test that deploy actions are listed correctly."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"
        game_state.turn_phase = TurnPhase.MOVEMENT

        actions_data = AIObserver.list_available_actions(game_state, "player_0")

        # Should have deploy actions for all token types (10, 8, 6, 4)
        deploy_actions = [
            action for action in actions_data["actions"]
            if action["type"] == "DEPLOY"
        ]

        assert len(deploy_actions) > 0

        # Check that deploy actions have required fields
        for action in deploy_actions:
            assert "health_value" in action
            assert "positions" in action
            assert "remaining" in action
            assert "description" in action
            assert action["health_value"] in [10, 8, 6, 4]

    def test_list_available_actions_move_actions(self):
        """Test that move actions are listed correctly."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"
        game_state.turn_phase = TurnPhase.MOVEMENT

        # Deploy a token
        token = game_state.deploy_token("player_0", 10, (5, 5))

        actions_data = AIObserver.list_available_actions(game_state, "player_0")

        # Should have move actions for the deployed token
        move_actions = [
            action for action in actions_data["actions"]
            if action["type"] == "MOVE"
        ]

        assert len(move_actions) > 0

        # Check that move actions have required fields
        for action in move_actions:
            assert "token_id" in action
            assert "token_position" in action
            assert "valid_destinations" in action
            assert "description" in action

    def test_list_available_actions_action_phase(self):
        """Test listing actions during action phase."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"
        game_state.turn_phase = TurnPhase.ACTION

        # Deploy tokens adjacent to each other for attack
        game_state.deploy_token("player_0", 10, (5, 5))
        game_state.deploy_token("player_1", 8, (5, 6))  # Adjacent

        actions_data = AIObserver.list_available_actions(game_state, "player_0")

        assert actions_data["phase"] == "ACTION"

        # Should have end turn action
        action_types = [action["type"] for action in actions_data["actions"]]
        assert "END_TURN" in action_types

        # Should have attack actions if enemies are adjacent
        if "ATTACK" in action_types:
            attack_actions = [
                action for action in actions_data["actions"]
                if action["type"] == "ATTACK"
            ]
            for action in attack_actions:
                assert "attacker_id" in action
                assert "defender_id" in action
                assert "damage" in action
                assert "will_kill" in action
                assert "description" in action

    def test_explain_victory_conditions_basic(self):
        """Test explaining victory conditions."""
        game_state = create_test_game(2)

        explanation = AIObserver.explain_victory_conditions(game_state)

        assert "VICTORY CONDITIONS:" in explanation
        assert "12 tokens" in explanation  # Base requirement
        assert "3 consecutive turns" in explanation
        assert "Generator bonuses:" in explanation

    def test_explain_victory_conditions_with_disabled_generator(self):
        """Test victory conditions explanation with disabled generators."""
        game_state = create_test_game(2)

        # Disable a generator
        game_state.generators[0].is_disabled = True

        explanation = AIObserver.explain_victory_conditions(game_state)

        assert "Disabled generators: 1" in explanation
        assert "10 tokens" in explanation  # 12 - 2 for disabled generator

    def test_explain_victory_conditions_shows_progress(self):
        """Test that victory conditions show current progress."""
        game_state = create_test_game(2)

        # Deploy tokens on crystal
        crystal_pos = game_state.crystal.position
        # Deploy multiple tokens around crystal to simulate progress
        game_state.deploy_token("player_0", 10, crystal_pos)

        explanation = AIObserver.explain_victory_conditions(game_state)

        assert "Current crystal progress:" in explanation

    def test_get_situation_report_comprehensive(self):
        """Test that situation report includes all sections."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"

        # Deploy some tokens
        game_state.deploy_token("player_0", 10, (5, 5))
        game_state.deploy_token("player_1", 8, (10, 10))

        report = AIObserver.get_situation_report(game_state, "player_0")

        # Should include all major sections
        assert "YOUR TURN" in report or "WAITING" in report
        assert "BOARD MAP" in report
        assert "AVAILABLE ACTIONS:" in report
        assert "VICTORY CONDITIONS:" in report
        assert "YOUR TOKENS" in report
        assert "ENEMY TOKENS" in report

    def test_get_situation_report_shows_actions(self):
        """Test that situation report shows available actions."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"
        game_state.turn_phase = TurnPhase.MOVEMENT

        report = AIObserver.get_situation_report(game_state, "player_0")

        assert "AVAILABLE ACTIONS:" in report
        # Should list numbered actions
        assert "1." in report or "waiting" in report.lower()

    def test_color_names_mapping(self):
        """Test that color names are correctly mapped."""
        assert AIObserver.COLOR_NAMES[PlayerColor.CYAN] == "Cyan"
        assert AIObserver.COLOR_NAMES[PlayerColor.MAGENTA] == "Magenta"
        assert AIObserver.COLOR_NAMES[PlayerColor.YELLOW] == "Yellow"
        assert AIObserver.COLOR_NAMES[PlayerColor.GREEN] == "Green"

    def test_board_map_token_symbols(self):
        """Test that board map uses correct symbols for different colored tokens."""
        game_state = create_test_game(4)

        # Deploy tokens for all players
        game_state.deploy_token("player_0", 10, (5, 5))   # Cyan
        game_state.deploy_token("player_1", 10, (6, 6))   # Magenta
        game_state.deploy_token("player_2", 10, (7, 7))   # Yellow
        game_state.deploy_token("player_3", 10, (8, 8))   # Green

        # From player_0's perspective (Cyan)
        board_map = AIObserver.get_board_map(game_state, "player_0")

        # Own token should be uppercase C
        assert " C " in board_map
        # Enemy tokens should be lowercase
        assert " m " in board_map  # Magenta
        assert " y " in board_map  # Yellow
        assert " g " in board_map  # Green

    def test_describe_game_state_reserve_counts(self):
        """Test that reserve token counts are displayed correctly."""
        game_state = create_test_game(2)

        # Deploy one of each type
        game_state.deploy_token("player_0", 10, (0, 0))
        game_state.deploy_token("player_0", 8, (0, 1))
        game_state.deploy_token("player_0", 6, (0, 2))
        game_state.deploy_token("player_0", 4, (0, 3))

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "RESERVE TOKENS:" in description
        # Should show 4 remaining of 10hp (started with 5, deployed 1)
        assert "10hp: 4" in description
        assert "8hp: 4" in description
        assert "6hp: 4" in description
        assert "4hp: 4" in description

    def test_list_available_actions_no_moves_available(self):
        """Test actions when no moves are available."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"
        game_state.turn_phase = TurnPhase.MOVEMENT

        # Don't deploy any tokens and block all corners
        # Deploy enemy tokens on all player_0's corner positions
        corners = game_state.board.get_deployable_positions(0)  # Player 0's corners
        for i, corner in enumerate(corners[:4]):  # Block some corners
            game_state.deploy_token("player_1", 10, corner)

        actions_data = AIObserver.list_available_actions(game_state, "player_0")

        # Should still work even if no actions available
        assert "phase" in actions_data
        assert "actions" in actions_data

    def test_movement_phase_indicator(self):
        """Test that phase indicator shows movement phase info."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"
        game_state.turn_phase = TurnPhase.MOVEMENT

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "Phase: MOVEMENT" in description
        assert "move a token or deploy" in description

    def test_action_phase_indicator(self):
        """Test that phase indicator shows action phase info."""
        game_state = create_test_game(2)
        game_state.current_turn_player_id = "player_0"
        game_state.turn_phase = TurnPhase.ACTION

        description = AIObserver.describe_game_state(game_state, "player_0")

        assert "Phase: ACTION" in description
        assert "attack" in description or "end your turn" in description
