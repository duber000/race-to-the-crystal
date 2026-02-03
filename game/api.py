"""
GameAPI - Simplified facade for AI agents.

This module provides a single entry point for AI agents to interact with
the game. It wraps the lower-level ai_observation and ai_actions modules
into a more convenient API.

Example:
    >>> from game.api import GameAPI
    >>> from game.game_state import GameState
    >>>
    >>> game_state = GameState()
    >>> game_state.add_player("ai_1", "AI Player", 0)
    >>> game_state.start_game()
    >>>
    >>> api = GameAPI(game_state, "ai_1")
    >>> print(api.observe())  # Get situation report
    >>> actions = api.actions()  # Get available actions
    >>> result = api.move(5, 12, 12)  # Move token #5 to (12, 12)
"""

from game.game_state import GameState
from game.ai_observation import AIObserver
from game.ai_actions import (
    AIActionExecutor,
    ActionResult,
    MoveAction,
    AttackAction,
    DeployAction,
    EndTurnAction,
)
from shared.types import PlayerID, TokenID


class GameAPI:
    """
    Simplified API facade for AI agents.

    Provides a clean, method-based interface for game observation and action
    execution. All methods return structured results that are easy to parse
    and act upon.

    Attributes:
        game_state: The current game state (mutable)
        player_id: The player ID this API operates for
        executor: The action executor instance

    Example:
        >>> api = GameAPI(game_state, player_id)
        >>>
        >>> # Observation methods
        >>> report = api.observe()       # Full situation report
        >>> actions = api.actions()      # Available actions list
        >>> board = api.board_map()      # ASCII board representation
        >>>
        >>> # Action methods (all return ActionResult)
        >>> result = api.move(token_id, x, y)
        >>> result = api.attack(attacker_id, defender_id)
        >>> result = api.deploy(health_value, x, y)
        >>> result = api.end_turn()
    """

    def __init__(self, game_state: GameState, player_id: PlayerID):
        """
        Initialize the GameAPI.

        Args:
            game_state: The game state to operate on (will be modified by actions)
            player_id: The player ID to act as
        """
        self.game_state = game_state
        self.player_id = player_id
        self.executor = AIActionExecutor()

    # -------------------------------------------------------------------------
    # Observation Methods
    # -------------------------------------------------------------------------

    def observe(self) -> str:
        """
        Get a complete situation report.

        Returns a comprehensive text description of the game state including:
        - Turn and phase information
        - Your tokens (deployed and reserve)
        - Enemy tokens
        - Generator status
        - Crystal status
        - Available actions
        - Victory conditions

        Returns:
            Multi-line formatted string describing the complete game state
        """
        return AIObserver.get_situation_report(self.game_state, self.player_id)

    def actions(self) -> list[dict]:
        """
        Get list of available actions.

        Returns a list of action dictionaries, each containing:
        - type: "MOVE", "ATTACK", "DEPLOY", or "END_TURN"
        - Action-specific fields (token_id, positions, etc.)
        - description: Human-readable description

        Returns:
            List of action dictionaries. Empty list if no actions available
            or not your turn.
        """
        result = AIObserver.list_available_actions(self.game_state, self.player_id)
        return result.get("actions", [])

    def actions_with_phase(self) -> dict:
        """
        Get available actions with phase information.

        Returns:
            Dictionary with:
            - phase: "MOVEMENT", "ACTION", "NOT_PLAYING", or "NOT_YOUR_TURN"
            - actions: List of action dictionaries
        """
        return AIObserver.list_available_actions(self.game_state, self.player_id)

    def board_map(self) -> str:
        """
        Get ASCII representation of the board.

        Returns a visual map showing:
        - Your tokens (uppercase letters by color)
        - Enemy tokens (lowercase letters by color)
        - Crystal (C)
        - Generators (1, 2, 3, 4)
        - Mystery squares (M)
        - Deployment corners (*)

        Returns:
            Multi-line ASCII art board with legend
        """
        return AIObserver.get_board_map(self.game_state, self.player_id)

    def describe(self) -> str:
        """
        Get text description of game state (without board map).

        Returns:
            Multi-line description of game state
        """
        return AIObserver.describe_game_state(self.game_state, self.player_id)

    def victory_conditions(self) -> str:
        """
        Get explanation of victory conditions and progress.

        Returns:
            Multi-line description of how to win and current progress
        """
        return AIObserver.explain_victory_conditions(self.game_state)

    # -------------------------------------------------------------------------
    # Action Methods
    # -------------------------------------------------------------------------

    def move(self, token_id: TokenID, x: int, y: int) -> ActionResult:
        """
        Move a token to a new position.

        Args:
            token_id: ID of the token to move
            x: Target x coordinate
            y: Target y coordinate

        Returns:
            ActionResult with:
            - success: True if move succeeded
            - message: Description of what happened
            - data: Dict with old_position, new_position, mystery_triggered, etc.

        Example:
            >>> result = api.move(5, 12, 12)
            >>> if result.success:
            ...     print(f"Moved to {result.data['new_position']}")
        """
        action = MoveAction(token_id=token_id, destination=(x, y))
        return self.executor.execute_action(action, self.game_state, self.player_id)

    def attack(self, attacker_id: TokenID, defender_id: TokenID) -> ActionResult:
        """
        Attack an enemy token.

        Damage dealt equals attacker.health // 2. The attacker takes no damage.

        Args:
            attacker_id: ID of your attacking token
            defender_id: ID of the enemy token to attack

        Returns:
            ActionResult with:
            - success: True if attack succeeded
            - message: Description of what happened
            - data: Dict with damage_dealt, defender_killed, etc.

        Example:
            >>> result = api.attack(5, 10)
            >>> if result.success:
            ...     if result.data['defender_killed']:
            ...         print("Target eliminated!")
        """
        action = AttackAction(attacker_id=attacker_id, defender_id=defender_id)
        return self.executor.execute_action(action, self.game_state, self.player_id)

    def deploy(self, health_value: int, x: int, y: int) -> ActionResult:
        """
        Deploy a token from reserve to the board.

        Tokens can only be deployed to your 3x3 corner deployment zone.

        Args:
            health_value: Health of token to deploy (10, 8, 6, or 4)
            x: Target x coordinate (must be in deployment zone)
            y: Target y coordinate (must be in deployment zone)

        Returns:
            ActionResult with:
            - success: True if deployment succeeded
            - message: Description of what happened
            - data: Dict with new_token_id, tokens_remaining, etc.

        Example:
            >>> result = api.deploy(8, 2, 2)
            >>> if result.success:
            ...     print(f"Deployed token #{result.data['new_token_id']}")
        """
        action = DeployAction(health_value=health_value, position=(x, y))
        return self.executor.execute_action(action, self.game_state, self.player_id)

    def end_turn(self) -> ActionResult:
        """
        End the current turn.

        Can be called from either MOVEMENT or ACTION phase to pass/skip.
        Generator and crystal capture progress is updated at end of turn.

        Returns:
            ActionResult with:
            - success: True if turn ended
            - message: Description of what happened
            - data: Dict with turn_number, next_player_id, etc.

        Example:
            >>> result = api.end_turn()
            >>> print(f"Turn {result.data['turn_number']} begins")
        """
        action = EndTurnAction()
        return self.executor.execute_action(action, self.game_state, self.player_id)

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def is_my_turn(self) -> bool:
        """
        Check if it's currently this player's turn.

        Returns:
            True if it's this player's turn, False otherwise
        """
        return self.game_state.current_turn_player_id == self.player_id

    def get_phase(self) -> str:
        """
        Get current turn phase.

        Returns:
            "MOVEMENT", "ACTION", or game phase if not playing
        """
        from shared.enums import GamePhase

        if self.game_state.phase != GamePhase.PLAYING:
            return self.game_state.phase.name
        return self.game_state.turn_phase.name

    def get_my_tokens(self) -> list[dict]:
        """
        Get list of all tokens owned by this player.

        Returns:
            List of token dictionaries with id, position, health, etc.
        """
        player = self.game_state.get_player(self.player_id)
        if not player:
            return []

        tokens = []
        for token_id in player.token_ids:
            if token := self.game_state.get_token(token_id):
                tokens.append(token.to_dict())
        return tokens

    def get_deployed_tokens(self) -> list[dict]:
        """
        Get list of deployed tokens owned by this player.

        Returns:
            List of token dictionaries for deployed tokens only
        """
        return [t for t in self.get_my_tokens() if t.get("is_deployed")]

    def get_reserve_counts(self) -> dict[int, int]:
        """
        Get count of tokens in reserve by health value.

        Returns:
            Dictionary mapping health value to count, e.g. {10: 5, 8: 4, 6: 5, 4: 5}
        """
        return dict(self.game_state.get_reserve_token_counts(self.player_id))
