"""
Tests for HTTP REST API endpoints.

Tests the HTTP POST + SSE architecture for AI clients.
"""

import pytest
import jwt
import time
from server.auth import (
    create_player_token,
    verify_player_token,
    extract_token_from_header,
    validate_token_for_game,
    generate_secret_key,
)


class TestJWTAuthentication:
    """Test JWT token creation and verification."""

    def test_generate_secret_key(self):
        """Test secret key generation."""
        key = generate_secret_key()
        assert len(key) == 64  # 32 bytes in hex = 64 chars
        assert isinstance(key, str)

    def test_create_and_verify_token(self):
        """Test creating and verifying a valid token."""
        secret = "test-secret-key"
        player_id = "player-123"
        game_id = "game-456"

        token = create_player_token(player_id, game_id, secret)
        assert isinstance(token, str)
        assert len(token) > 0

        payload = verify_player_token(token, secret)
        assert payload.player_id == player_id
        assert payload.game_id == game_id
        assert payload.issued_at > 0
        assert payload.expires_at > payload.issued_at

    def test_verify_token_with_wrong_secret(self):
        """Test that wrong secret causes verification to fail."""
        secret1 = "secret-1"
        secret2 = "secret-2"

        token = create_player_token("player-1", "game-1", secret1)

        with pytest.raises(jwt.InvalidTokenError):
            verify_player_token(token, secret2)

    def test_verify_expired_token(self):
        """Test that expired token is rejected."""
        secret = "test-secret"
        player_id = "player-123"
        game_id = "game-456"

        # Create token that expires immediately
        token = create_player_token(player_id, game_id, secret, expiration_hours=0)

        # Wait a moment for it to expire
        time.sleep(0.1)

        with pytest.raises(jwt.ExpiredSignatureError):
            verify_player_token(token, secret)

    def test_extract_token_from_header(self):
        """Test extracting token from Authorization header."""
        token = "abc123def456"
        header = f"Bearer {token}"

        extracted = extract_token_from_header(header)
        assert extracted == token

    def test_extract_token_from_invalid_header(self):
        """Test that invalid headers return None."""
        # No Bearer prefix
        assert extract_token_from_header("abc123") is None

        # Wrong prefix
        assert extract_token_from_header("Basic abc123") is None

        # Empty
        assert extract_token_from_header("") is None
        assert extract_token_from_header(None) is None

    def test_validate_token_for_game(self):
        """Test validating token game_id matches requested game."""
        secret = "test-secret"
        player_id = "player-123"
        game_id = "game-456"

        token = create_player_token(player_id, game_id, secret)
        payload = verify_player_token(token, secret)

        # Correct game ID
        assert validate_token_for_game(payload, game_id) is True

        # Wrong game ID
        assert validate_token_for_game(payload, "different-game") is False


class TestHTTPEndpoints:
    """Test HTTP API endpoints (requires actual server)."""

    # Note: These are integration-style tests that would require a running server
    # For now, we test the JWT logic which is the core of authentication

    def test_token_payload_structure(self):
        """Test that token payload has correct structure."""
        secret = "test-secret"
        player_id = "player-uuid-123"
        game_id = "game-uuid-456"

        token = create_player_token(player_id, game_id, secret)
        payload = verify_player_token(token, secret)

        # Check all required fields exist
        assert hasattr(payload, "player_id")
        assert hasattr(payload, "game_id")
        assert hasattr(payload, "issued_at")
        assert hasattr(payload, "expires_at")

        # Check values
        assert payload.player_id == player_id
        assert payload.game_id == game_id

    def test_token_expiration_time(self):
        """Test that token expiration is set correctly."""
        secret = "test-secret"
        expiration_hours = 24

        token = create_player_token("p1", "g1", secret, expiration_hours)
        payload = verify_player_token(token, secret)

        expected_expiration = payload.issued_at + (expiration_hours * 3600)
        assert abs(payload.expires_at - expected_expiration) < 1  # Within 1 second


# More integration tests would go here that test the actual HTTP endpoints
# These would use aiohttp test client to test /api/game/{game_id}/join
# and /api/game/{game_id}/action endpoints
