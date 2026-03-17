"""
Standardized error formatting for Race to the Crystal.

This module provides consistent error formatting across all modules:
- Game logic: CANNOT {action}: {reason} | {context}
- HTTP API: Structured JSON with error code, message, and details
- WebSocket: Consistent message format
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class GameError:
    """
    Standardized error for game logic.

    Format: CANNOT {action}: {reason} | {context}

    Example:
        CANNOT MOVE: token_not_found | token_id=99 | valid_tokens=[1,2,3,4,5]
        CANNOT ATTACK: not_adjacent | attacker_pos=(5,5) | defender_pos=(10,10)
    """

    action: str
    reason: str
    context: dict[str, Any] | None = None

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.context:
            context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
            return f"CANNOT {self.action}: {self.reason} | {context_str}"
        return f"CANNOT {self.action}: {self.reason}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": "game_error",
            "action": self.action,
            "reason": self.reason,
            "context": self.context or {},
            "message": str(self),
        }


@dataclass
class ValidationError:
    """
    Standardized validation error.

    Used for input validation failures.

    Example:
        ValidationError("player_name", "too_short", {"min_length": 3})
        -> "Invalid player_name: too_short | min_length=3"
    """

    field: str
    reason: str
    context: dict[str, Any] | None = None

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.context:
            context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
            return f"Invalid {self.field}: {self.reason} | {context_str}"
        return f"Invalid {self.field}: {self.reason}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": "validation_error",
            "field": self.field,
            "reason": self.reason,
            "context": self.context or {},
            "message": str(self),
        }


@dataclass
class ServerError:
    """
    Standardized server error.

    Used for internal server errors and unexpected conditions.

    Example:
        ServerError("database_connection", "Failed to connect to database")
        -> "Server error: database_connection | Failed to connect to database"
    """

    code: str
    message: str
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.details:
            details_str = " | ".join(f"{k}={v}" for k, v in self.details.items())
            return f"Server error: {self.code} | {self.message} | {details_str}"
        return f"Server error: {self.code} | {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": "server_error",
            "code": self.code,
            "message": self.message,
            "details": self.details or {},
        }


@dataclass
class ActionError:
    """
    Standardized action execution error.

    Used when action validation passes but execution fails.

    Example:
        ActionError("MOVE", "token_destroyed", {"token_id": 5})
        -> "Action MOVE failed: token_destroyed | token_id=5"
    """

    action: str
    reason: str
    context: dict[str, Any] | None = None

    def __str__(self) -> str:
        """Return formatted error message."""
        if self.context:
            context_str = " | ".join(f"{k}={v}" for k, v in self.context.items())
            return f"Action {self.action} failed: {self.reason} | {context_str}"
        return f"Action {self.action} failed: {self.reason}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": "action_error",
            "action": self.action,
            "reason": self.reason,
            "context": self.context or {},
            "message": str(self),
        }


# Common error codes for consistency
class ErrorCode:
    """Standardized error codes across the application."""

    # Game logic errors
    TOKEN_NOT_FOUND = "token_not_found"
    TOKEN_NOT_DEPLOYED = "token_not_deployed"
    TOKEN_NOT_OWNED = "token_not_owned"
    TOKEN_DESTROYED = "token_destroyed"
    NOT_ADJACENT = "not_adjacent"
    NOT_IN_RANGE = "not_in_range"
    INVALID_POSITION = "invalid_position"
    CELL_OCCUPIED = "cell_occupied"
    WRONG_PHASE = "wrong_phase"
    NOT_PLAYER_TURN = "not_player_turn"
    GAME_NOT_PLAYING = "game_not_playing"

    # Validation errors
    MISSING_FIELD = "missing_field"
    INVALID_TYPE = "invalid_type"
    INVALID_VALUE = "invalid_value"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"

    # Server errors
    SERVER_NOT_INITIALIZED = "server_not_initialized"
    DATABASE_ERROR = "database_error"
    INTERNAL_ERROR = "internal_error"

    # Auth errors
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"

    # Game state errors
    GAME_NOT_FOUND = "game_not_found"
    GAME_ALREADY_STARTED = "game_already_started"
    GAME_FINISHED = "game_finished"
    PLAYER_NOT_IN_GAME = "player_not_in_game"
    LOBBY_FULL = "lobby_full"


def format_error_response(
    error: GameError | ValidationError | ServerError | ActionError,
    status_code: int = 400,
) -> dict[str, Any]:
    """
    Format an error for HTTP JSON response.

    Args:
        error: The error to format
        status_code: HTTP status code

    Returns:
        Dictionary suitable for web.json_response
    """
    error_dict = error.to_dict()
    error_dict["status_code"] = status_code
    return error_dict


def format_websocket_error(
    error: GameError | ValidationError | ServerError | ActionError,
) -> dict[str, Any]:
    """
    Format an error for WebSocket message.

    Args:
        error: The error to format

    Returns:
        Dictionary suitable for WebSocket message
    """
    return {
        "type": "ERROR",
        "error": str(error),
        **error.to_dict(),
    }
