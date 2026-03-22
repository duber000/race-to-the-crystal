"""
AI Action Classes and Execution - Execute AI player actions with validation.

This module provides structured action classes and an executor that validates
and executes actions with detailed feedback for AI players.
"""

from dataclasses import dataclass
from game.game_state import GameState
from game.movement import MovementSystem
from game.combat import CombatSystem
from game.mystery_square import MysterySquareSystem
from game.token import Token
from shared.enums import TurnPhase, GamePhase, CellType
from shared.types import TokenID, PlayerID


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
    data: dict | None = None

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
        result: dict[str, object] = {"action_type": self.action_type}
        # Add all fields from the dataclass except action_type (already added)
        for field_name in self.__dataclass_fields__:
            if field_name != "action_type":
                value = getattr(self, field_name)
                # Convert tuples to lists for JSON serialization
                if isinstance(value, tuple):
                    value = list(value)
                result[field_name] = value
        return result


@dataclass
class MoveAction(AIAction):
    """
    Move a token to a new position.

    Attributes:
        token_id: ID of token to move
        destination: Target (x, y) position

    Example:
        >>> from game.ai_actions import AIActionExecutor, MoveAction
        >>> executor = AIActionExecutor()
        >>> action = MoveAction(token_id=5, destination=(12, 12))
        >>> result = executor.execute_action(action, game_state, player_id)
        >>> if result.success:
        ...     print(f"Moved to {result.data['new_position']}")
        ... else:
        ...     print(f"Failed: {result.message}")

    Validation requirements:
        - Game phase must be PLAYING
        - Turn phase must be MOVEMENT
        - Token must exist, be deployed, alive, and owned by player
        - Destination must be reachable within token's movement range
    """

    token_id: TokenID
    destination: tuple[int, int]

    def __init__(self, token_id: TokenID, destination: tuple[int, int]):
        super().__init__(action_type="MOVE")
        self.token_id = token_id
        self.destination = destination


@dataclass
class AttackAction(AIAction):
    """
    Attack an enemy token.

    Damage dealt equals attacker.health // 2. The attacker takes no damage.
    If damage >= defender's health, the defender is killed and removed from the game.

    Attributes:
        attacker_id: ID of attacking token
        defender_id: ID of defending token

    Example:
        >>> from game.ai_actions import AIActionExecutor, AttackAction
        >>> executor = AIActionExecutor()
        >>> action = AttackAction(attacker_id=5, defender_id=10)
        >>> result = executor.execute_action(action, game_state, player_id)
        >>> if result.success:
        ...     print(f"Dealt {result.data['damage_dealt']} damage")
        ...     if result.data['defender_killed']:
        ...         print("Target eliminated!")

    Validation requirements:
        - Game phase must be PLAYING
        - Turn phase must be ACTION
        - Attacker must exist, be deployed, alive, and owned by player
        - Defender must exist, be deployed, alive, and NOT owned by player
        - Attacker and defender must be adjacent (8-directional)
    """

    attacker_id: TokenID
    defender_id: TokenID

    def __init__(self, attacker_id: TokenID, defender_id: TokenID):
        super().__init__(action_type="ATTACK")
        self.attacker_id = attacker_id
        self.defender_id = defender_id


@dataclass
class DeployAction(AIAction):
    """
    Deploy a token from reserve to the board.

    Tokens can only be deployed to the player's 3x3 corner deployment zone.
    Each player starts with 20 tokens in reserve (5x10hp, 5x8hp, 5x6hp, 5x4hp).

    Attributes:
        health_value: Health value of token to deploy (10, 8, 6, or 4)
        position: Deployment (x, y) position within corner zone

    Example:
        >>> from game.ai_actions import AIActionExecutor, DeployAction
        >>> executor = AIActionExecutor()
        >>> action = DeployAction(health_value=8, position=(2, 2))
        >>> result = executor.execute_action(action, game_state, player_id)
        >>> if result.success:
        ...     print(f"Deployed token #{result.data['new_token_id']}")
        ...     print(f"Remaining 8hp tokens: {result.data['tokens_remaining']}")

    Validation requirements:
        - Game phase must be PLAYING
        - Turn phase must be MOVEMENT
        - health_value must be 10, 8, 6, or 4
        - Player must have tokens of that health value in reserve
        - Position must be in player's deployment zone and unoccupied
    """

    health_value: int
    position: tuple[int, int]

    def __init__(self, health_value: int, position: tuple[int, int]):
        super().__init__(action_type="DEPLOY")
        self.health_value = health_value
        self.position = position


@dataclass
class EndTurnAction(AIAction):
    """
    End the current turn.

    Ends the player's turn and advances to the next player.
    Generator and crystal capture progress is updated at end of turn.

    Example:
        >>> from game.ai_actions import AIActionExecutor, EndTurnAction
        >>> executor = AIActionExecutor()
        >>> action = EndTurnAction()
        >>> result = executor.execute_action(action, game_state, player_id)
        >>> if result.success:
        ...     print(f"Turn {result.data['turn_number']} begins")
        ...     print(f"Next player: {result.data['next_player_id']}")

    Validation requirements:
        - Game phase must be PLAYING
        - Turn phase must be MOVEMENT or ACTION
        - Can be used to "pass" without taking any action
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

    def _validate_game_phase(self, game_state: GameState) -> ValidationResult | None:
        """Validate that game is in PLAYING phase."""
        if game_state.phase != GamePhase.PLAYING:
            return ValidationResult(
                False,
                f"ACTION_FAILED: wrong_game_phase | current={game_state.phase.name} | required=PLAYING",
            )
        return None

    def _validate_player_turn(
        self, game_state: GameState, player_id: PlayerID
    ) -> ValidationResult | None:
        """Validate that it's the player's turn."""
        if game_state.current_turn_player_id != player_id:
            return ValidationResult(
                False,
                f"ACTION_FAILED: not_your_turn | current_player={game_state.current_turn_player_id} | you={player_id}",
            )
        return None

    def _validate_turn_phase(
        self, game_state: GameState, required_phase: TurnPhase, action_name: str
    ) -> ValidationResult | None:
        """Validate that game is in the required turn phase."""
        if game_state.turn_phase != required_phase:
            return ValidationResult(
                False,
                f"{action_name}_FAILED: wrong_phase | current={game_state.turn_phase.name} | required={required_phase.name}",
            )
        return None

    def _validate_token_exists(
        self, game_state: GameState, token_id: TokenID, action_name: str
    ) -> tuple[ValidationResult, Token] | tuple[ValidationResult, None]:
        """Validate that a token exists and return it."""
        token = game_state.get_token(token_id)
        if not token:
            return ValidationResult(
                False,
                f"{action_name}_FAILED: token_not_found | token_id={token_id}",
            ), None
        return ValidationResult(True, ""), token

    def _validate_token_ownership(
        self, token: Token, player_id: PlayerID, action_name: str
    ) -> ValidationResult:
        """Validate that player owns the token."""
        if token.player_id != player_id:
            return ValidationResult(
                False,
                f"{action_name}_FAILED: not_owner | token_id={token.id} | owner={token.player_id}",
            )
        return ValidationResult(True, "")

    def _validate_token_deployed(
        self, token: Token, action_name: str
    ) -> ValidationResult:
        """Validate that token is deployed."""
        if not token.is_deployed:
            return ValidationResult(
                False,
                f"{action_name}_FAILED: not_deployed | token_id={token.id} | hint=Use DEPLOY action first",
            )
        return ValidationResult(True, "")

    def _validate_token_alive(self, token: Token, action_name: str) -> ValidationResult:
        """Validate that token is alive."""
        if not token.is_alive:
            return ValidationResult(
                False,
                f"{action_name}_FAILED: token_dead | token_id={token.id}",
            )
        return ValidationResult(True, "")

    def validate_action(
        self, action: AIAction, game_state: GameState, player_id: PlayerID
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
        if result := self._validate_game_phase(game_state):
            return result

        if result := self._validate_player_turn(game_state, player_id):
            return result

        # Validate based on action type using pattern matching
        match action:
            case MoveAction():
                return self._validate_move(action, game_state, player_id)
            case AttackAction():
                return self._validate_attack(action, game_state, player_id)
            case DeployAction():
                return self._validate_deploy(action, game_state, player_id)
            case EndTurnAction():
                return self._validate_end_turn(action, game_state, player_id)
            case _:
                return ValidationResult(
                    False, f"Unknown action type: {type(action).__name__}"
                )

    def execute_action(
        self, action: AIAction, game_state: GameState, player_id: PlayerID
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

        # Execute based on action type using pattern matching
        match action:
            case MoveAction():
                return self._execute_move(action, game_state, player_id)
            case AttackAction():
                return self._execute_attack(action, game_state, player_id)
            case DeployAction():
                return self._execute_deploy(action, game_state, player_id)
            case EndTurnAction():
                return self._execute_end_turn(action, game_state, player_id)
            case _:
                return ActionResult(
                    False, f"Unknown action type: {type(action).__name__}", None
                )

    # --- MOVE ACTION ---

    def _validate_move(
        self, action: MoveAction, game_state: GameState, player_id: PlayerID
    ) -> ValidationResult:
        """Validate a move action."""
        # Check phase
        if game_state.turn_phase != TurnPhase.MOVEMENT:
            return ValidationResult(
                False,
                f"MOVE_FAILED: wrong_phase | current={game_state.turn_phase.name} | required=MOVEMENT",
            )

        # Check token exists
        if not (token := game_state.get_token(action.token_id)):
            player = game_state.get_player(player_id)
            valid_tokens = [tid for tid in (player.token_ids if player else [])]
            return ValidationResult(
                False,
                f"MOVE_FAILED: token_not_found | token_id={action.token_id} | valid_tokens={valid_tokens[:5]}",
            )

        # Check token ownership
        if token.player_id != player_id:
            return ValidationResult(
                False,
                f"MOVE_FAILED: not_owner | token_id={action.token_id} | owner={token.player_id}",
            )

        # Check token is deployed
        if not token.is_deployed:
            return ValidationResult(
                False,
                f"MOVE_FAILED: not_deployed | token_id={action.token_id} | hint=Use DEPLOY action first",
            )

        # Check token is alive
        if not token.is_alive:
            return ValidationResult(
                False,
                f"MOVE_FAILED: token_dead | token_id={action.token_id}",
            )

        # Check destination is valid (with effective movement range considering speed boost)
        effective_range = game_state.get_token_movement_range(token)
        valid_moves = MovementSystem.get_valid_moves(
            token,
            game_state.board,
            max_range=effective_range,
            tokens_dict=game_state.tokens,
        )
        if action.destination not in valid_moves:
            x, y = action.destination
            return ValidationResult(
                False,
                f"MOVE_FAILED: invalid_destination | dest=({x},{y}) | token_pos={token.position} | range={effective_range} | valid_count={len(valid_moves)}",
            )

        return ValidationResult(True, "Move is valid")

    def _execute_move(
        self, action: MoveAction, game_state: GameState, player_id: PlayerID
    ) -> ActionResult:
        """Execute a move action."""
        token = game_state.get_token(action.token_id)
        if token is None:
            return ActionResult(False, f"Token {action.token_id} not found", None)
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

                # Record mystery event for client animations
                game_state.last_triggered_mystery_event = (
                    action.token_id,
                    new_pos,
                    mystery_result.effect.name,
                )

                message += "\n→ Token landed on a MYSTERY square!"
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
        self, action: AttackAction, game_state: GameState, player_id: PlayerID
    ) -> ValidationResult:
        """Validate an attack action."""
        # Check phase
        if game_state.turn_phase != TurnPhase.ACTION:
            return ValidationResult(
                False,
                f"ATTACK_FAILED: wrong_phase | current={game_state.turn_phase.name} | required=ACTION",
            )

        # Check attacker exists
        if not (attacker := game_state.get_token(action.attacker_id)):
            return ValidationResult(
                False,
                f"ATTACK_FAILED: attacker_not_found | attacker_id={action.attacker_id}",
            )

        # Check attacker ownership
        if attacker.player_id != player_id:
            return ValidationResult(
                False,
                f"ATTACK_FAILED: not_owner | attacker_id={action.attacker_id} | owner={attacker.player_id}",
            )

        # Check attacker is deployed and alive
        if not attacker.is_deployed:
            return ValidationResult(
                False,
                f"ATTACK_FAILED: attacker_not_deployed | attacker_id={action.attacker_id}",
            )
        if not attacker.is_alive:
            return ValidationResult(
                False,
                f"ATTACK_FAILED: attacker_dead | attacker_id={action.attacker_id}",
            )

        # Check defender exists
        if not (defender := game_state.get_token(action.defender_id)):
            return ValidationResult(
                False,
                f"ATTACK_FAILED: defender_not_found | defender_id={action.defender_id}",
            )

        # Check defender is not owned by attacker
        if defender.player_id == player_id:
            return ValidationResult(
                False,
                f"ATTACK_FAILED: friendly_fire | defender_id={action.defender_id} | hint=Cannot attack own tokens",
            )

        # Check defender is deployed and alive
        if not defender.is_deployed:
            return ValidationResult(
                False,
                f"ATTACK_FAILED: defender_not_deployed | defender_id={action.defender_id}",
            )
        if not defender.is_alive:
            return ValidationResult(
                False,
                f"ATTACK_FAILED: defender_already_dead | defender_id={action.defender_id}",
            )

        # Check tokens are adjacent
        if not CombatSystem.can_attack(attacker, defender):
            return ValidationResult(
                False,
                f"ATTACK_FAILED: not_adjacent | attacker_pos={attacker.position} | defender_pos={defender.position}",
            )

        return ValidationResult(True, "Attack is valid")

    def _execute_attack(
        self, action: AttackAction, game_state: GameState, player_id: PlayerID
    ) -> ActionResult:
        """Execute an attack action."""
        attacker = game_state.get_token(action.attacker_id)
        defender = game_state.get_token(action.defender_id)

        if attacker is None:
            return ActionResult(
                False, f"Attacker token {action.attacker_id} not found", None
            )
        if defender is None:
            return ActionResult(
                False, f"Defender token {action.defender_id} not found", None
            )

        # Capture pre-combat info for reporting
        damage = attacker.health // 2
        defender_player = game_state.get_player(defender.player_id)
        defender_owner = defender_player.name if defender_player else "Unknown"

        # Execute combat (applies damage and rounds health down to nearest valid value)
        CombatSystem.resolve_combat(attacker, defender)

        # Check kill AFTER combat: take_damage kills tokens whose health rounds below 4,
        # so "damage >= defender.health" would miss cases like 6hp attacker vs 6hp defender
        was_killed = not defender.is_alive

        if was_killed:
            # Remove dead token from board and player token list
            game_state.remove_token(action.defender_id)

        # Build result message
        message = f"✓ Token #{action.attacker_id} attacked token #{action.defender_id} ({defender_owner})"
        message += f"\n→ Dealt {damage} damage"

        result_data = {
            "attacker_id": action.attacker_id,
            "defender_id": action.defender_id,
            "damage_dealt": damage,
            "defender_killed": was_killed,
        }

        if was_killed:
            message += f"\n→ Token #{action.defender_id} was KILLED!"
        else:
            message += f"\n→ Token #{action.defender_id} now has {defender.health}hp"

        return ActionResult(True, message, result_data)

    # --- DEPLOY ACTION ---

    def _validate_deploy(
        self, action: DeployAction, game_state: GameState, player_id: PlayerID
    ) -> ValidationResult:
        """Validate a deploy action."""
        # Check phase
        if game_state.turn_phase != TurnPhase.MOVEMENT:
            return ValidationResult(
                False,
                f"DEPLOY_FAILED: wrong_phase | current={game_state.turn_phase.name} | required=MOVEMENT",
            )

        # Check health value is valid
        if action.health_value not in [10, 8, 6, 4]:
            return ValidationResult(
                False,
                f"DEPLOY_FAILED: invalid_health | value={action.health_value} | valid=[10,8,6,4]",
            )

        # Check player has tokens of this type in reserve
        reserve_counts = game_state.get_reserve_token_counts(player_id)
        if reserve_counts[action.health_value] <= 0:
            return ValidationResult(
                False,
                f"DEPLOY_FAILED: no_reserve | health={action.health_value} | reserve={dict(reserve_counts)}",
            )

        # Check position is valid (in bounds)
        x, y = action.position
        if not game_state.board.is_valid_position(x, y):
            return ValidationResult(
                False,
                f"DEPLOY_FAILED: out_of_bounds | pos=({x},{y}) | board_size=24x24",
            )

        # Check position is not occupied
        cell = game_state.board.get_cell_at(action.position)
        if cell and cell.is_occupied():
            return ValidationResult(
                False,
                f"DEPLOY_FAILED: cell_occupied | pos=({x},{y}) | occupants={cell.occupants}",
            )

        # Check position is a valid deployment location (corner + adjacent)
        if not (player := game_state.get_player(player_id)):
            return ValidationResult(
                False,
                f"DEPLOY_FAILED: player_not_found | player_id={player_id}",
            )

        from game.ai_observation import AIObserver

        valid_positions = AIObserver._get_deployable_positions(
            game_state.board, player.color.value
        )

        if action.position not in valid_positions:
            return ValidationResult(
                False,
                f"DEPLOY_FAILED: invalid_position | pos=({x},{y}) | valid_positions={[list(p) for p in valid_positions[:3]]}...",
            )

        return ValidationResult(True, "Deployment is valid")

    def _execute_deploy(
        self, action: DeployAction, game_state: GameState, player_id: PlayerID
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
        message += (
            f"\n→ {remaining} × {action.health_value}hp tokens remaining in reserve"
        )

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
        self, action: EndTurnAction, game_state: GameState, player_id: PlayerID
    ) -> ValidationResult:
        """Validate an end turn action."""
        # Can end turn in both MOVEMENT and ACTION phases
        # This allows players to "pass" without taking an action
        if game_state.turn_phase not in [TurnPhase.MOVEMENT, TurnPhase.ACTION]:
            return ValidationResult(
                False, f"Cannot end turn: Invalid phase ({game_state.turn_phase.name})"
            )

        return ValidationResult(True, "Can end turn")

    def _execute_end_turn(
        self, action: EndTurnAction, game_state: GameState, player_id: PlayerID
    ) -> ActionResult:
        """Execute an end turn action."""
        # Update objectives and advance the turn
        newly_disabled, crystal_captured = game_state.end_turn_with_objective_update()

        # Get new current player
        new_player = game_state.get_current_player()
        new_player_name = new_player.name if new_player else "Unknown"

        message = "✓ Turn ended"
        message += f"\n→ Turn {game_state.turn_number} begins"
        message += f"\n→ Current player: {new_player_name}"

        result_data = {
            "turn_number": game_state.turn_number,
            "next_player_id": game_state.current_turn_player_id,
            "generators_disabled": newly_disabled,
            "crystal_captured": crystal_captured,
        }

        return ActionResult(True, message, result_data)
