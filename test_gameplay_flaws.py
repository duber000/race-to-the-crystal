#!/usr/bin/env python3
"""
Comprehensive gameplay testing using AI API to find flaws in code or gameplay logic.
This script plays through multiple game scenarios looking for bugs, exploits, and logical inconsistencies.
"""

import sys
import random
from typing import List, Dict, Tuple, Optional
from game.game_state import GameState
from game.generator import Generator
from game.crystal import Crystal
from game.ai_observation import AIObserver
from game.ai_actions import (
    AIActionExecutor, MoveAction, AttackAction, DeployAction, EndTurnAction
)
from shared.enums import PlayerColor, TurnPhase
from shared.constants import BOARD_WIDTH, BOARD_HEIGHT


class GameplayTester:
    """Automated tester that plays games and looks for issues."""

    def __init__(self):
        self.observer = AIObserver()
        self.executor = AIActionExecutor()
        self.issues_found = []
        self.test_count = 0

    def log_issue(self, severity: str, category: str, description: str, game_state: GameState = None):
        """Log a discovered issue."""
        issue = {
            'severity': severity,  # CRITICAL, HIGH, MEDIUM, LOW
            'category': category,
            'description': description,
            'test_number': self.test_count,
        }
        if game_state:
            issue['turn'] = game_state.turn_number
            issue['phase'] = game_state.turn_phase.name
        self.issues_found.append(issue)
        print(f"\n🔴 [{severity}] {category}: {description}")

    def log_info(self, message: str):
        """Log informational message."""
        print(f"ℹ️  {message}")

    def log_success(self, message: str):
        """Log successful test."""
        print(f"✓ {message}")

    def create_test_game(self) -> GameState:
        """Create a fresh game for testing."""
        game_state = GameState()
        game_state.add_player("player1", "Test Player 1", PlayerColor.CYAN)
        game_state.add_player("player2", "Test Player 2", PlayerColor.MAGENTA)
        game_state.start_game()

        # Initialize generators
        for i, pos in enumerate(game_state.board.get_generator_positions()):
            game_state.generators.append(Generator(id=i, position=pos))

        # Initialize crystal
        game_state.crystal = Crystal(position=game_state.board.get_crystal_position())

        return game_state

    def get_valid_moves(self, game_state: GameState, player_id: str) -> List[Dict]:
        """Get all valid move actions for a player."""
        actions_data = self.observer.list_available_actions(game_state, player_id)
        return [a for a in actions_data.get("actions", []) if a["type"] == "MOVE"]

    def get_valid_attacks(self, game_state: GameState, player_id: str) -> List[Dict]:
        """Get all valid attack actions for a player."""
        actions_data = self.observer.list_available_actions(game_state, player_id)
        return [a for a in actions_data.get("actions", []) if a["type"] == "ATTACK"]

    def get_valid_deploys(self, game_state: GameState, player_id: str) -> List[Dict]:
        """Get all valid deploy actions for a player."""
        actions_data = self.observer.list_available_actions(game_state, player_id)
        return [a for a in actions_data.get("actions", []) if a["type"] == "DEPLOY"]

    def get_player_tokens(self, game_state: GameState, player_id: str) -> List:
        """Get all tokens belonging to a player."""
        player = game_state.get_player(player_id)
        if not player:
            return []
        return [game_state.tokens[tid] for tid in player.token_ids if tid in game_state.tokens]

    def execute_random_turn(self, game_state: GameState, player_id: str) -> bool:
        """Execute a random valid turn for the player. Returns True if successful."""
        try:
            # MOVEMENT PHASE
            if game_state.turn_phase == TurnPhase.MOVEMENT:
                moves = self.get_valid_moves(game_state, player_id)
                deploys = self.get_valid_deploys(game_state, player_id)

                # Randomly choose between move and deploy
                if moves and deploys:
                    if random.random() < 0.7:  # Prefer moves
                        action_data = random.choice(moves)
                        action = MoveAction(action_data["token_id"], tuple(action_data["valid_destinations"][0]))
                    else:
                        action_data = random.choice(deploys)
                        action = DeployAction(action_data["health_value"], tuple(action_data["positions"][0]))
                elif moves:
                    action_data = random.choice(moves)
                    action = MoveAction(action_data["token_id"], tuple(action_data["valid_destinations"][0]))
                elif deploys:
                    action_data = random.choice(deploys)
                    action = DeployAction(action_data["health_value"], tuple(action_data["positions"][0]))
                else:
                    self.log_issue("HIGH", "Game Logic",
                                 f"No valid moves or deploys in MOVEMENT phase for {player_id}", game_state)
                    return False

                success, msg, data = self.executor.execute_action(action, game_state, player_id)
                if not success:
                    self.log_issue("HIGH", "Action Execution",
                                 f"Failed to execute valid action: {msg}", game_state)
                    return False

            # ACTION PHASE
            if game_state.turn_phase == TurnPhase.ACTION:
                attacks = self.get_valid_attacks(game_state, player_id)

                if attacks and random.random() < 0.3:  # 30% chance to attack if available
                    action_data = random.choice(attacks)
                    action = AttackAction(action_data["attacker_id"], action_data["defender_id"])
                    success, msg, data = self.executor.execute_action(action, game_state, player_id)
                    if not success:
                        self.log_issue("HIGH", "Combat",
                                     f"Failed to execute valid attack: {msg}", game_state)
                        return False
                else:
                    # End turn
                    action = EndTurnAction()
                    success, msg, data = self.executor.execute_action(action, game_state, player_id)
                    if not success:
                        self.log_issue("CRITICAL", "Turn System",
                                     f"Failed to end turn: {msg}", game_state)
                        return False

            return True

        except Exception as e:
            self.log_issue("CRITICAL", "Exception", f"Unexpected error during turn: {str(e)}", game_state)
            import traceback
            traceback.print_exc()
            return False

    def test_basic_gameplay(self, max_turns: int = 50) -> None:
        """Test basic gameplay flow."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Basic Gameplay ({max_turns} turns)")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()

        for turn in range(max_turns):
            current_player = game_state.current_player_id

            # Check for win condition
            if game_state.winner_id:
                self.log_success(f"Game ended with winner: {game_state.winner_id} at turn {turn}")
                return

            # Execute turn
            success = self.execute_random_turn(game_state, current_player)
            if not success:
                self.log_issue("HIGH", "Game Flow", f"Failed to complete turn {turn}", game_state)
                break

        if not game_state.winner_id:
            self.log_info(f"Game completed {max_turns} turns without a winner (expected)")

    def test_movement_boundaries(self) -> None:
        """Test movement at board boundaries."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Movement Boundaries")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()

        # Try to move tokens to all corners and edges
        test_positions = [
            (0, 0), (BOARD_WIDTH-1, 0), (0, BOARD_HEIGHT-1), (BOARD_WIDTH-1, BOARD_HEIGHT-1),  # Corners
            (BOARD_WIDTH//2, 0), (BOARD_WIDTH//2, BOARD_HEIGHT-1),  # Top/bottom edges
            (0, BOARD_HEIGHT//2), (BOARD_WIDTH-1, BOARD_HEIGHT//2)   # Left/right edges
        ]

        for pos in test_positions:
            # Get a token to move
            player_tokens = self.get_player_tokens(game_state, "player1")
            if player_tokens:
                token = player_tokens[0]
                if not token.is_deployed:
                    # Deploy first
                    deploy_pos = (1, 1)
                    action = DeployAction(10, deploy_pos)
                    self.executor.execute_action(action, game_state, "player1")

                # Try to move to test position (might not be reachable in one turn, but shouldn't crash)
                player_tokens = self.get_player_tokens(game_state, "player1")
                if player_tokens and player_tokens[0].is_deployed:
                    # Get valid moves
                    moves = self.get_valid_moves(game_state, "player1")
                    if moves:
                        # Verify boundary positions are handled correctly
                        for move in moves:
                            for dest in move.get("valid_destinations", []):
                                x, y = dest
                                if x < 0 or x >= BOARD_WIDTH or y < 0 or y >= BOARD_HEIGHT:
                                    self.log_issue("CRITICAL", "Movement",
                                                 f"Invalid destination outside board: {dest}", game_state)

        self.log_success("Movement boundary checks completed")

    def test_combat_damage_calculation(self) -> None:
        """Test combat damage calculations."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Combat Damage Calculation")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()

        # Deploy tokens at adjacent positions directly (bypass deployment validation for testing)
        token1 = game_state.deploy_token("player1", 10, (10, 10))
        token2 = game_state.deploy_token("player2", 8, (11, 10))

        # Set current player to player1 and phase to ACTION to test combat
        game_state.current_turn_player_id = "player1"
        game_state.turn_phase = TurnPhase.ACTION

        # Perform attack
        initial_health = token2.health

        action = AttackAction(token1.id, token2.id)
        success, msg, data = self.executor.execute_action(action, game_state, "player1")

        if success:
            expected_damage = token1.max_health // 2  # 10 // 2 = 5
            actual_damage = initial_health - token2.health

            if actual_damage != expected_damage:
                self.log_issue("CRITICAL", "Combat",
                             f"Damage calculation error: expected {expected_damage}, got {actual_damage}",
                             game_state)
            else:
                self.log_success(f"Combat damage correct: {expected_damage} damage dealt")

            # Verify attacker took no damage
            if token1.health != token1.max_health:
                self.log_issue("CRITICAL", "Combat",
                             f"Attacker took damage when they shouldn't have", game_state)
        else:
            self.log_issue("HIGH", "Combat", f"Failed to execute combat: {msg}", game_state)

    def test_generator_capture(self) -> None:
        """Test generator capture mechanics."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Generator Capture")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()

        # Get generator position
        if not game_state.generators:
            self.log_issue("CRITICAL", "Game Setup", "No generators found in game", game_state)
            return

        gen = game_state.generators[0]
        gen_pos = gen.position

        # Deploy 2 tokens at generator directly (bypass deployment validation for testing)
        game_state.deploy_token("player1", 10, gen_pos)
        game_state.deploy_token("player1", 10, gen_pos)

        # Hold for 2 turns by ending turns
        for turns_held in range(1, 6):
            # End player 1 turn (holding generator)
            game_state.end_turn()
            # End player 2 turn
            game_state.end_turn()

            if turns_held >= 2:
                # Should be disabled now
                if not gen.is_disabled:
                    self.log_issue("CRITICAL", "Generator",
                                 f"Generator not disabled after {turns_held} turns with 2 tokens",
                                 game_state)
                else:
                    self.log_success(f"Generator correctly disabled after {turns_held} turns")
                break

    def test_crystal_capture(self) -> None:
        """Test crystal capture and win condition."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Crystal Capture")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()
        crystal_pos = game_state.crystal.position

        # Manually disable all generators to reduce requirement to 4 tokens
        for gen in game_state.generators:
            gen.is_disabled = True
            gen.capture_token_ids.clear()
            gen.turns_held = 0

        # Deploy 4 tokens at crystal directly (bypass deployment validation for testing)
        for i in range(4):
            game_state.deploy_token("player1", 10, crystal_pos)

        # Hold for 3 turns by ending turns
        for turn in range(4):
            # End player 1 turn (holding crystal)
            game_state.end_turn()
            # End player 2 turn
            game_state.end_turn()

            if turn >= 2:  # After 3rd turn
                if game_state.winner_id == "player1":
                    self.log_success(f"Crystal win condition correctly triggered")
                    return

        if not game_state.winner_id:
            self.log_issue("CRITICAL", "Win Condition",
                         "Player did not win after holding crystal with 4 tokens for 3 turns",
                         game_state)

    def test_token_destruction(self) -> None:
        """Test that tokens are properly removed when health reaches 0."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Token Destruction")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()

        # Deploy tokens at adjacent positions directly (bypass deployment validation for testing)
        defender_token = game_state.deploy_token("player1", 4, (10, 10))
        attacker_token = game_state.deploy_token("player2", 10, (11, 10))

        # Set current player to player2 and phase to ACTION to test combat
        game_state.current_turn_player_id = "player2"
        game_state.turn_phase = TurnPhase.ACTION

        defender_id = defender_token.id

        # 10hp token attacks 4hp token - should deal 5 damage and kill it
        action = AttackAction(attacker_token.id, defender_id)
        success, msg, data = self.executor.execute_action(action, game_state, "player2")

        if success:
            # Check if token was removed
            player1_tokens_after = self.get_player_tokens(game_state, "player1")
            token_exists = any(t.id == defender_id for t in player1_tokens_after)
            if token_exists:
                # Check if it's actually dead
                dead_token = next((t for t in player1_tokens_after if t.id == defender_id), None)
                if dead_token and dead_token.health > 0:
                    self.log_issue("CRITICAL", "Combat",
                                 f"Token survived with {dead_token.health}hp after lethal damage",
                                 game_state)
                elif dead_token and dead_token.is_deployed:
                    self.log_issue("HIGH", "Combat",
                                 f"Dead token still marked as deployed", game_state)
                else:
                    self.log_success("Token correctly destroyed")
            else:
                self.log_success("Token correctly removed from game")
        else:
            self.log_issue("HIGH", "Combat", f"Failed to execute attack: {msg}", game_state)

    def test_phase_transitions(self) -> None:
        """Test that phase transitions work correctly."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Phase Transitions")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()

        # Should start in MOVEMENT phase
        if game_state.turn_phase != TurnPhase.MOVEMENT:
            self.log_issue("CRITICAL", "Phase System",
                         f"Game should start in MOVEMENT phase, got {game_state.turn_phase}",
                         game_state)
            return

        # Try to attack in MOVEMENT phase (should fail)
        action = DeployAction(10, (1, 1))
        self.executor.execute_action(action, game_state, "player1")

        player1_tokens = self.get_player_tokens(game_state, "player1")
        if player1_tokens and player1_tokens[0].is_deployed:
            # Try to attack (should fail - wrong phase)
            action = AttackAction(player1_tokens[0].id, -1)
            success, msg, data = self.executor.execute_action(action, game_state, "player1")
            if success:
                self.log_issue("CRITICAL", "Phase System",
                             "Attack succeeded in MOVEMENT phase", game_state)

        # Move to ACTION phase
        if game_state.turn_phase == TurnPhase.MOVEMENT:
            # Already moved, should be in ACTION now
            pass
        elif game_state.turn_phase != TurnPhase.ACTION:
            self.log_issue("CRITICAL", "Phase System",
                         f"After movement, should be in ACTION phase, got {game_state.turn_phase}",
                         game_state)

        # Try to move in ACTION phase (should fail)
        moves = self.get_valid_moves(game_state, "player1")
        if moves:
            self.log_issue("CRITICAL", "Phase System",
                         "Move actions available in ACTION phase", game_state)

        self.log_success("Phase transition checks completed")

    def test_reserve_limits(self) -> None:
        """Test that token reserve limits are enforced."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Reserve Limits")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()
        player = game_state.get_player("player1")

        # Try to deploy all tokens of one health value
        tokens_deployed = 0
        for i in range(10):  # Try more than the 5 available
            action = DeployAction(10, (i, 0))
            success, msg, data = self.executor.execute_action(action, game_state, "player1")
            if success:
                tokens_deployed += 1
            action = EndTurnAction()
            self.executor.execute_action(action, game_state, "player1")
            # Player 2 turn
            action = EndTurnAction()
            self.executor.execute_action(action, game_state, "player2")

        if tokens_deployed > 5:
            self.log_issue("CRITICAL", "Reserve Management",
                         f"Deployed {tokens_deployed} tokens of 10hp when only 5 should be available",
                         game_state)
        else:
            self.log_success(f"Correctly limited to {tokens_deployed} deployments")

    def test_action_validation_consistency(self) -> None:
        """Test that validate_action and execute_action are consistent."""
        self.test_count += 1
        self.log_info(f"\n{'='*60}")
        self.log_info(f"TEST {self.test_count}: Action Validation Consistency")
        self.log_info(f"{'='*60}")

        game_state = self.create_test_game()

        # Get valid actions
        actions_data = self.observer.list_available_actions(game_state, "player1")

        inconsistencies = 0
        for action_data in actions_data.get("actions", [])[:10]:  # Test first 10
            if action_data["type"] == "MOVE":
                action = MoveAction(action_data["token_id"],
                                  tuple(action_data["valid_destinations"][0]))
            elif action_data["type"] == "DEPLOY":
                action = DeployAction(action_data["health_value"],
                                    tuple(action_data["positions"][0]))
            else:
                continue

            # Validate should succeed
            is_valid, msg = self.executor.validate_action(action, game_state, "player1")
            if not is_valid:
                self.log_issue("HIGH", "Validation",
                             f"Action from list_available_actions failed validation: {msg}",
                             game_state)
                inconsistencies += 1

        if inconsistencies == 0:
            self.log_success("All listed actions passed validation")
        else:
            self.log_issue("HIGH", "Validation",
                         f"Found {inconsistencies} inconsistencies between list and validation",
                         game_state)

    def run_all_tests(self):
        """Run all gameplay tests."""
        print("\n" + "="*60)
        print("STARTING COMPREHENSIVE GAMEPLAY TESTING")
        print("="*60)

        # Run tests
        self.test_basic_gameplay(max_turns=50)
        self.test_movement_boundaries()
        self.test_combat_damage_calculation()
        self.test_generator_capture()
        self.test_crystal_capture()
        self.test_token_destruction()
        self.test_phase_transitions()
        self.test_reserve_limits()
        self.test_action_validation_consistency()

        # Try a few more random games
        for i in range(3):
            self.test_basic_gameplay(max_turns=30)

        # Report results
        print("\n" + "="*60)
        print("TESTING COMPLETE")
        print("="*60)
        print(f"\nTotal tests run: {self.test_count}")
        print(f"Total issues found: {len(self.issues_found)}")

        if self.issues_found:
            print("\n📋 ISSUES SUMMARY:")
            print("-" * 60)

            by_severity = {}
            for issue in self.issues_found:
                severity = issue['severity']
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(issue)

            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if severity in by_severity:
                    print(f"\n{severity} ({len(by_severity[severity])}):")
                    for issue in by_severity[severity]:
                        print(f"  • [{issue['category']}] {issue['description']}")
                        if 'turn' in issue:
                            print(f"    Turn {issue['turn']}, Phase: {issue['phase']}")
        else:
            print("\n✅ NO ISSUES FOUND - All tests passed!")

        return len(self.issues_found)


if __name__ == "__main__":
    tester = GameplayTester()
    issue_count = tester.run_all_tests()
    sys.exit(0 if issue_count == 0 else 1)
