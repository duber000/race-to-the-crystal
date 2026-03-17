"""Shared module - Constants, enums, and types shared across the codebase."""

from shared.enums import (
    GamePhase,
    TurnPhase,
    PlayerColor,
    CellType,
    CombatResult,
    CrystalEffect,
)
from shared.constants import (
    BOARD_WIDTH,
    BOARD_HEIGHT,
    CELL_SIZE,
    TOKEN_HEALTH_VALUES,
    TOKENS_PER_HEALTH_VALUE,
    PLAYER_COLORS,
)
from shared.types import TokenID, PlayerID, Position
from shared.errors import (
    GameError,
    ValidationError,
    ServerError,
    ActionError,
    ErrorCode,
    format_error_response,
    format_websocket_error,
)

__all__ = [
    "GamePhase",
    "TurnPhase",
    "PlayerColor",
    "CellType",
    "CombatResult",
    "CrystalEffect",
    "BOARD_WIDTH",
    "BOARD_HEIGHT",
    "CELL_SIZE",
    "TOKEN_HEALTH_VALUES",
    "TOKENS_PER_HEALTH_VALUE",
    "PLAYER_COLORS",
    "TokenID",
    "PlayerID",
    "Position",
    "GameError",
    "ValidationError",
    "ServerError",
    "ActionError",
    "ErrorCode",
    "format_error_response",
    "format_websocket_error",
]
