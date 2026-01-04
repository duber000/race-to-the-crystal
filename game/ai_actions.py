"""
AI Action Classes and Execution - Execute AI player actions with validation.

This module provides structured action classes and an executor that validates
and executes actions with detailed feedback for AI players.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from game.game_state import GameState
from game.movement import MovementSystem
from game.combat import CombatSystem
from game.mystery_square import MysterySquareSystem
from shared.enums import TurnPhase, GamePhase, CellType


@dataclass
class ValidationResult:
    """
    Result of action validation.

    Attributes:
        is_valid: True if action can be executed
        message: Success message or detailed error explanation
    """
    is_valid: bool
    message: str

    def __iter__(self):
        """Allow tuple unpacking for backward compatibility."""
        return iter((self.is_valid, self.message))


@dataclass
class ActionResult:
    """
    Result of action execution.

    Attributes:
        success: True if action executed successfully
        message: Detailed description of what happened
        data: Optional dict with action-specific results
    """
    success: bool
    message: str
    data: Optional[Dict] = None

    def __iter__(self):
        """Allow tuple unpacking for backward compatibility."""
        return iter((self.success, self.message, self.data))


@dataclass
class AIAction:
    """
    Base class for all AI actions.

    Attributes:
        action_type: String identifier for the action type
    """
    action_type: str

    def to_dict(self) -> dict:
        """Convert action to dictionary for serialization."""
        return {"action_type": self.action_type}


@dataclass
class MoveAction(AIAction):
    """
    Move a token to a new position.

    Attributes:
        token_id: ID of token to move
        destination: Target (x, y) position
    """
    token_id: int
    destination: Tuple[int, int]

    def __init__(self, token_id: int, destination: Tuple[int, int]):
        super().__init__(action_type="MOVE")
        self.token_id = token_id
        self.destination = destination

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "token_id": self.token_id,
            "destination": list(self.destination),
        }


@dataclass
class AttackAction(AIAction):
    """
    Attack an enemy token.

    Attributes:
        attacker_id: ID of attacking token
        defender_id: ID of defending token
    """
    attacker_id: int
    defender_id: int

    def __init__(self, attacker_id: int, defender_id: int):
        super().__init__(action_type="ATTACK")
        self.attacker_id = attacker_id
        self.defender_id = defender_id

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "attacker_id": self.attacker_id,
            "defender_id": self.defender_id,
        }


@dataclass
class DeployAction(AIAction):
    """
    Deploy a token from reserve to the board.

    Attributes:
        health_value: Health value of token to deploy (10, 8, 6, or 4)
        position: Deployment (x, y) position
    """
    health_value: int
    position: Tuple[int, int]

    def __init__(self, health_value: int, position: Tuple[int, int]):
        super().__init__(action_type="DEPLOY")
        self.health_value = health_value
        self.position = position

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "health_value": self.health_value,
            "position": list(self.position),
        }


@dataclass
class EndTurnAction(AIAction):
    """
    End the current turn.

    No additional attributes needed.
    """

    def __init__(self):
        super().__init__(action_type="END_TURN")


class AIActionExecutor:
    """
    Validates and executes AI actions with detailed feedback.

    This class provides validation and execution for all action types,
    ensuring that AI players receive clear error messages when actions
    are invalid.
    """

    def validate_action(
        self,
        action: AIAction,
        game_state: GameState,
        player_id: str
    ) -> ValidationResult:
        """
        Validate action without executing it.

        Args:
            action: Action to validate
            game_state: Current game state
            player_id: Player attempting the action

        Returns:
            ValidationResult with is_valid flag and message
        """
        # Check game phase
        if game_state.phase != GamePhase.PLAYING:
            return ValidationResult(False, "Cannot act: Game is not in PLAYING phase")

        # Check if it's the player's turn
        if game_state.current_turn_player_id != player_id:
            current_player = game_state.get_current_player()
            current_name = current_player.name if current_player else "Unknown"
            return ValidationResult(False, f"Cannot act: Not your turn (current: {current_name})")

        # Validate based on action type
        if isinstance(action, MoveAction):
            return self._validate_move(action, game_state, player_id)
        elif isinstance(action, AttackAction):
            return self._validate_attack(action, game_state, player_id)
        elif isinstance(action, DeployAction):
            return self._validate_deploy(action, game_state, player_id)
        elif isinstance(action, EndTurnAction):
            return self._validate_end_turn(action, game_state, player_id)
        else:
            return ValidationResult(False, f"Unknown action type: {type(action).__name__}")

    def execute_action(
        self,
        action: AIAction,
        game_state: GameState,
        player_id: str
    ) -> ActionResult:
        """
        Validate and execute an action.

        Args:
            action: Action to execute
            game_state: Current game state (will be modified)
            player_id: Player executing the action

        Returns:
            ActionResult with success flag, message, and optional data dict
        """
        # First validate
        validation = self.validate_action(action, game_state, player_id)
        if not validation.is_valid:
            return ActionResult(False, validation.message, None)

        # Execute based on action type
        if isinstance(action, MoveAction):
            return self._execute_move(action, game_state, player_id)
        elif isinstance(action, AttackAction):
            return self._execute_attack(action, game_state, player_id)
        elif isinstance(action, DeployAction):
            return self._execute_deploy(action, game_state, player_id)
        elif isinstance(action, EndTurnAction):
            return self._execute_end_turn(action, game_state, player_id)
        else:
            return ActionResult(False, f"Unknown action type: {type(action).__name__}", None)

    # --- MOVE ACTION ---

    def _validate_move(
        self,
        action: MoveAction,
        game_state: GameState,
        player_id: str
    ) -> ValidationResult:
        """Validate a move action."""
        # Check phase
        if game_state.turn_phase != TurnPhase.MOVEMENT:
            return ValidationResult(False, f"Cannot move: Wrong phase (currently in {game_state.turn_phase.name})")

        # Check token exists
        token = game_state.get_token(action.token_id)
        if not token:
            return ValidationResult(False, f"Cannot move: Token #{action.token_id} does not exist")

        # Check token ownership
        if token.player_id != player_id:
            return ValidationResult(False, f"Cannot move: Token #{action.token_id} does not belong to you")

        # Check token is deployed
        if not token.is_deployed:
            return ValidationResult(False, f"Cannot move: Token #{action.token_id} is not deployed")

        # Check token is alive
        if not token.is_alive:
            return ValidationResult(False, f"Cannot move: Token #{action.token_id} is dead")

        # Check destination is valid
        valid_moves = MovementSystem.get_valid_moves(token, game_state.board, tokens_dict=game_state.tokens)
        if action.destination not in valid_moves:
            x, y = action.destination
            return ValidationResult(False, f"Cannot move: Destination ({x},{y}) is not reachable from token's position")

        return ValidationResult(True, "Move is valid")

    def _execute_move(
        self,
        action: MoveAction,
        game_state: GameState,
        player_id: str
    ) -> ActionResult:
        """Execute a move action."""
        token = game_state.get_token(action.token_id)
        old_pos = token.position
        new_pos = action.destination

        # Execute the move
        success = game_state.move_token(action.token_id, new_pos)

        if not success:
            return ActionResult(False, "Move failed unexpectedly", None)

        # Build result message
        message = f"✓ Token #{action.token_id} moved from ({old_pos[0]},{old_pos[1]}) to ({new_pos[0]},{new_pos[1]})"
        result_data = {
            "token_id": action.token_id,
            "old_position": old_pos,
            "new_position": new_pos,
        }

        # Check for mystery square and trigger effect
        cell = game_state.board.get_cell_at(new_pos)
        if cell and cell.cell_type == CellType.MYSTERY:
            # Get player's index for potential teleport to deployment area
            player = game_state.get_player(player_id)
            if player:
                player_index = player.color.value

                # Trigger the mystery event (50/50 heal or teleport)
                mystery_result = MysterySquareSystem.trigger_mystery_event(
                    token, game_state.board, player_index
                )

                message += f"\n→ Token landed on a MYSTERY square!"
                result_data["mystery_triggered"] = True
                result_data["mystery_effect"] = mystery_result.effect.name

                if mystery_result.effect.name == "HEAL":
                    message += f"\n→ 🎲 HEADS! Token healed from {mystery_result.old_health} to {mystery_result.new_health} HP!"
                else:
                    # Token was teleported - update board occupancy
                    game_state.board.clear_occupant(new_pos, token.id)
                    game_state.board.set_occupant(mystery_result.new_position, token.id)
                    message += f"\n→ 🎲 TAILS! Token teleported back to deployment area {mystery_result.new_position}!"
                    result_data["new_position"] = mystery_result.new_position

        # Change phase to ACTION
        game_state.turn_phase = TurnPhase.ACTION
        message += "\n→ Phase changed to ACTION (you can attack or end turn)"

        return ActionResult(True, message, result_data)

    # --- ATTACK ACTION ---

    def _validate_attack(
        self,
        action: AttackAction,
        game_state: GameState,
        player_id: str
    ) -> ValidationResult:
        """Validate an attack action."""
        # Check phase
        if game_state.turn_phase != TurnPhase.ACTION:
            return ValidationResult(False, f"Cannot attack: Wrong phase (currently in {game_state.turn_phase.name})")

        # Check attacker exists
        attacker = game_state.get_token(action.attacker_id)
        if not attacker:
            return ValidationResult(False, f"Cannot attack: Attacker token #{action.attacker_id} does not exist")

        # Check attacker ownership
        if attacker.player_id != player_id:
            return ValidationResult(False, f"Cannot attack: Attacker #{action.attacker_id} does not belong to you")

        # Check attacker is deployed and alive
        if not attacker.is_deployed:
            return ValidationResult(False, f"Cannot attack: Attacker #{action.attacker_id} is not deployed")
        if not attacker.is_alive:
            return ValidationResult(False, f"Cannot attack: Attacker #{action.attacker_id} is dead")

        # Check defender exists
        defender = game_state.get_token(action.defender_id)
        if not defender:
            return ValidationResult(False, f"Cannot attack: Defender token #{action.defender_id} does not exist")

        # Check defender is not owned by attacker
        if defender.player_id == player_id:
            return ValidationResult(False, f"Cannot attack: Cannot attack your own token #{action.defender_id}")

        # Check defender is deployed and alive
        if not defender.is_deployed:
            return ValidationResult(False, f"Cannot attack: Defender #{action.defender_id} is not deployed")
        if not defender.is_alive:
            return ValidationResult(False, f"Cannot attack: Defender #{action.defender_id} is already dead")

        # Check tokens are adjacent
        if not CombatSystem.can_attack(attacker, defender):
            return ValidationResult(False, f"Cannot attack: Defender #{action.defender_id} is not adjacent to attacker")

        return ValidationResult(True, "Attack is valid")

    def _execute_attack(
        self,
        action: AttackAction,
        game_state: GameState,
        player_id: str
    ) -> ActionResult:
        """Execute an attack action."""
        attacker = game_state.get_token(action.attacker_id)
        defender = game_state.get_token(action.defender_id)

        # Calculate damage
        damage = attacker.health // 2
        will_kill = damage >= defender.health

        # Execute combat
        outcome = CombatSystem.resolve_combat(attacker, defender)

        # Build result message
        defender_player = game_state.get_player(defender.player_id)
        defender_owner = defender_player.name if defender_player else "Unknown"

        message = f"✓ Token #{action.attacker_id} attacked token #{action.defender_id} ({defender_owner})"
        message += f"\n→ Dealt {damage} damage"

        result_data = {
            "attacker_id": action.attacker_id,
            "defender_id": action.defender_id,
            "damage_dealt": damage,
            "defender_killed": will_kill,
        }

        if will_kill:
            message += f"\n→ Token #{action.defender_id} was KILLED!"
            result_data["defender_killed"] = True
            # Remove dead token from game
            game_state.remove_token(action.defender_id)
        else:
            message += f"\n→ Token #{action.defender_id} now has {defender.health}hp"

        return ActionResult(True, message, result_data)

    # --- DEPLOY ACTION ---

    def _validate_deploy(
        self,
        action: DeployAction,
        game_state: GameState,
        player_id: str
    ) -> ValidationResult:
        """Validate a deploy action."""
        # Check phase
        if game_state.turn_phase != TurnPhase.MOVEMENT:
            return ValidationResult(False, f"Cannot deploy: Wrong phase (currently in {game_state.turn_phase.name})")

        # Check health value is valid
        if action.health_value not in [10, 8, 6, 4]:
            return ValidationResult(False, f"Cannot deploy: Invalid health value {action.health_value} (must be 10, 8, 6, or 4)")

        # Check player has tokens of this type in reserve
        reserve_counts = game_state.get_reserve_token_counts(player_id)
        if reserve_counts[action.health_value] <= 0:
            return ValidationResult(False, f"Cannot deploy: No {action.health_value}hp tokens in reserve")

        # Check position is valid (in bounds)
        x, y = action.position
        if not game_state.board.is_valid_position(x, y):
            return ValidationResult(False, f"Cannot deploy: Position ({x},{y}) is out of bounds")

        # Check position is not occupied
        cell = game_state.board.get_cell_at(action.position)
        if cell and cell.is_occupied():
            return ValidationResult(False, f"Cannot deploy: Position ({x},{y}) is already occupied")

        # Check position is a valid deployment location (corner + adjacent)
        player = game_state.get_player(player_id)
        if not player:
            return ValidationResult(False, "Cannot deploy: Player not found")

        from game.ai_observation import AIObserver
        valid_positions = AIObserver._get_deployable_positions(
            game_state.board, player.color.value
        )

        if action.position not in valid_positions:
            return ValidationResult(False, f"Cannot deploy: Position ({x},{y}) is not a valid deployment location")

        return ValidationResult(True, "Deployment is valid")

    def _execute_deploy(
        self,
        action: DeployAction,
        game_state: GameState,
        player_id: str
    ) -> ActionResult:
        """Execute a deploy action."""
        # Deploy the token
        token = game_state.deploy_token(player_id, action.health_value, action.position)

        if not token:
            return ActionResult(False, "Deployment failed unexpectedly", None)

        # Build result message
        x, y = action.position
        message = f"✓ Deployed {action.health_value}hp token #{token.id} at ({x},{y})"

        # Check remaining reserve
        reserve_counts = game_state.get_reserve_token_counts(player_id)
        remaining = reserve_counts[action.health_value]
        message += f"\n→ {remaining} × {action.health_value}hp tokens remaining in reserve"

        result_data = {
            "new_token_id": token.id,
            "health_value": action.health_value,
            "position": action.position,
            "tokens_remaining": remaining,
        }

        # Change phase to ACTION
        game_state.turn_phase = TurnPhase.ACTION
        message += "\n→ Phase changed to ACTION (you can attack or end turn)"

        return ActionResult(True, message, result_data)

    # --- END TURN ACTION ---

    def _validate_end_turn(
        self,
        action: EndTurnAction,
        game_state: GameState,
        player_id: str
    ) -> ValidationResult:
        """Validate an end turn action."""
        # Can end turn in both MOVEMENT and ACTION phases
        # This allows players to "pass" without taking an action
        if game_state.turn_phase not in [TurnPhase.MOVEMENT, TurnPhase.ACTION]:
            return ValidationResult(False, f"Cannot end turn: Invalid phase ({game_state.turn_phase.name})")

        return ValidationResult(True, "Can end turn")

    def _execute_end_turn(
        self,
        action: EndTurnAction,
        game_state: GameState,
        player_id: str
    ) -> ActionResult:
        """Execute an end turn action."""
        # End the turn
        game_state.end_turn()

        # Get new current player
        new_player = game_state.get_current_player()
        new_player_name = new_player.name if new_player else "Unknown"

        message = f"✓ Turn ended"
        message += f"\n→ Turn {game_state.turn_number} begins"
        message += f"\n→ Current player: {new_player_name}"

        result_data = {
            "turn_number": game_state.turn_number,
            "next_player_id": game_state.current_turn_player_id,
        }

        return ActionResult(True, message, result_data)
