"""
JWT Authentication for HTTP API.

Provides token creation and verification for stateless HTTP requests
from AI clients using the HTTP POST + SSE architecture.
"""

import jwt
import secrets
import time
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class TokenPayload:
    """Decoded JWT token payload."""

    player_id: str
    game_id: str
    issued_at: float
    expires_at: float

    @classmethod
    def from_dict(cls, data: dict) -> "TokenPayload":
        """Create TokenPayload from decoded JWT dictionary."""
        return cls(
            player_id=data["player_id"],
            game_id=data["game_id"],
            issued_at=data["iat"],
            expires_at=data["exp"],
        )


def generate_secret_key() -> str:
    """
    Generate a cryptographically secure secret key for JWT signing.

    Returns:
        32-byte secret key as hex string
    """
    return secrets.token_hex(32)


def create_player_token(
    player_id: str, game_id: str, secret_key: str, expiration_hours: int = 24
) -> str:
    """
    Create a JWT token for HTTP AI client authentication.

    Args:
        player_id: Network player ID (UUID)
        game_id: Game ID the player joined
        secret_key: Secret key for signing the token
        expiration_hours: Token expiration time (default: 24 hours)

    Returns:
        JWT token string

    Example:
        >>> token = create_player_token("player_123", "game_456", "secret")
        >>> # Use in Authorization header: Bearer {token}
    """
    now = time.time()
    expiration = now + (expiration_hours * 3600)

    payload = {
        "player_id": player_id,
        "game_id": game_id,
        "iat": now,  # Issued at
        "exp": expiration,  # Expiration
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    logger.debug(
        f"Created JWT token for player {player_id[:8]} in game {game_id[:8]}, "
        f"expires in {expiration_hours}h"
    )

    return token


def verify_player_token(token: str, secret_key: str) -> TokenPayload | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        secret_key: Secret key used to sign the token

    Returns:
        TokenPayload if valid, None if invalid/expired

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is malformed or invalid signature
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        logger.debug(
            f"Verified JWT token for player {payload.get('player_id', 'unknown')[:8]}"
        )
        return TokenPayload.from_dict(payload)

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise

    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise


def extract_token_from_header(authorization_header: str) -> str | None:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization_header: Value of Authorization header (e.g., "Bearer abc123")

    Returns:
        Token string, or None if header is invalid

    Example:
        >>> token = extract_token_from_header("Bearer abc123def456")
        >>> token
        'abc123def456'
    """
    if not authorization_header:
        return None

    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(
            f"Invalid Authorization header format: {authorization_header[:20]}"
        )
        return None

    return parts[1]


def validate_token_for_game(payload: TokenPayload | None, game_id: str) -> bool:
    """
    Validate that a token's game_id matches the requested game.

    Args:
        payload: Decoded token payload
        game_id: Game ID being accessed

    Returns:
        True if token is valid for this game

    Example:
        >>> payload = verify_player_token(token, secret)
        >>> if not validate_token_for_game(payload, requested_game_id):
        ...     return 403  # Forbidden
    """
    if payload is None:
        return False

    if payload.game_id != game_id:
        logger.warning(
            f"Token game_id mismatch: token={payload.game_id[:8]}, "
            f"requested={game_id[:8]}"
        )
        return False

    return True
