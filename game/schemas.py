"""
Action schemas for AI agents.

This module provides TypedDict definitions for game actions, enabling
type-safe action creation and validation for AI agents.
"""

from typing import Literal, TypedDict

from shared.types import TokenID, Position


class MoveActionSchema(TypedDict):
    """
    Schema for moving a token to a new position.

    Example:
        >>> action: MoveActionSchema = {
        ...     "action_type": "MOVE",
        ...     "token_id": 5,
        ...     "destination": (12, 12),
        ... }
    """

    action_type: Literal["MOVE"]
    token_id: TokenID
    destination: Position


class AttackActionSchema(TypedDict):
    """
    Schema for attacking an enemy token.

    Example:
        >>> action: AttackActionSchema = {
        ...     "action_type": "ATTACK",
        ...     "attacker_id": 5,
        ...     "defender_id": 10,
        ... }
    """

    action_type: Literal["ATTACK"]
    attacker_id: TokenID
    defender_id: TokenID


class DeployActionSchema(TypedDict):
    """
    Schema for deploying a token from reserve.

    Example:
        >>> action: DeployActionSchema = {
        ...     "action_type": "DEPLOY",
        ...     "health_value": 8,
        ...     "position": (2, 2),
        ... }
    """

    action_type: Literal["DEPLOY"]
    health_value: Literal[10, 8, 6, 4]
    position: Position


class EndTurnActionSchema(TypedDict):
    """
    Schema for ending the current turn.

    Example:
        >>> action: EndTurnActionSchema = {"action_type": "END_TURN"}
    """

    action_type: Literal["END_TURN"]


# Union type for any action schema
ActionSchema = MoveActionSchema | AttackActionSchema | DeployActionSchema | EndTurnActionSchema


# Available action response schemas (from AIObserver.list_available_actions)
class MoveActionResponse(TypedDict):
    """Response schema for an available move action."""

    type: Literal["MOVE"]
    token_id: TokenID
    token_position: list[int]
    token_health: str
    valid_destinations: list[list[int]]
    description: str


class AttackActionResponse(TypedDict):
    """Response schema for an available attack action."""

    type: Literal["ATTACK"]
    attacker_id: TokenID
    attacker_position: list[int]
    defender_id: TokenID
    defender_position: list[int]
    defender_owner: str
    damage: int
    will_kill: bool
    description: str


class DeployActionResponse(TypedDict):
    """Response schema for an available deploy action."""

    type: Literal["DEPLOY"]
    health_value: Literal[10, 8, 6, 4]
    positions: list[list[int]]
    remaining: int
    description: str


class EndTurnActionResponse(TypedDict):
    """Response schema for the end turn action."""

    type: Literal["END_TURN"]
    description: str


# Union type for any action response
ActionResponse = (
    MoveActionResponse | AttackActionResponse | DeployActionResponse | EndTurnActionResponse
)


class AvailableActionsResponse(TypedDict):
    """Response schema from AIObserver.list_available_actions()."""

    phase: Literal["MOVEMENT", "ACTION", "NOT_PLAYING", "NOT_YOUR_TURN"]
    actions: list[ActionResponse]


# Action result data schemas
class MoveResultData(TypedDict, total=False):
    """Data returned from a successful move action."""

    token_id: TokenID
    old_position: list[int]
    new_position: list[int]
    mystery_triggered: bool
    mystery_effect: str


class AttackResultData(TypedDict, total=False):
    """Data returned from a successful attack action."""

    attacker_id: TokenID
    defender_id: TokenID
    damage_dealt: int
    defender_killed: bool
    attacker_position: list[int]
    defender_position: list[int]


class DeployResultData(TypedDict, total=False):
    """Data returned from a successful deploy action."""

    token_id: TokenID
    health_value: int
    position: list[int]


# Union type for action result data
ActionResultData = MoveResultData | AttackResultData | DeployResultData | None
