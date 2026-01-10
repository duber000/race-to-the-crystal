"""
Tests for rate limiting functionality.
"""

import time
import pytest

from server.rate_limiter import RateLimiter, TokenBucket, SlidingWindowCounter


class TestTokenBucket:
    """Tests for TokenBucket rate limiter."""

    def test_initial_capacity(self):
        """Test token bucket starts with full capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.tokens == 10.0

    def test_consume_success(self):
        """Test consuming tokens when available."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.consume(5) is True
        assert bucket.tokens == 5.0

    def test_consume_failure(self):
        """Test consuming tokens when insufficient."""
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        assert bucket.consume(3) is True
        assert bucket.consume(3) is False  # Only 2 left
        assert pytest.approx(bucket.tokens, abs=0.1) == 2.0  # Approx due to refill timing

    def test_refill_over_time(self):
        """Test tokens refill at specified rate."""
        bucket = TokenBucket(capacity=10, refill_rate=5.0)  # 5 tokens/second
        bucket.consume(10)  # Empty bucket
        assert bucket.tokens == 0.0

        time.sleep(0.5)  # Wait 0.5 seconds -> should add ~2.5 tokens
        bucket._refill()
        assert 2.0 <= bucket.tokens <= 3.0

    def test_refill_max_capacity(self):
        """Test tokens don't exceed capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=100.0)
        bucket.consume(5)
        time.sleep(1.0)  # Would add 100 tokens, but capped at 10
        bucket._refill()
        assert bucket.tokens == 10.0


class TestSlidingWindowCounter:
    """Tests for SlidingWindowCounter rate limiter."""

    def test_allow_within_limit(self):
        """Test events allowed within limit."""
        counter = SlidingWindowCounter(max_events=5, window_seconds=60)
        for _ in range(5):
            assert counter.try_event() is True
        assert counter.get_count() == 5

    def test_reject_over_limit(self):
        """Test events rejected when limit exceeded."""
        counter = SlidingWindowCounter(max_events=3, window_seconds=60)
        assert counter.try_event() is True
        assert counter.try_event() is True
        assert counter.try_event() is True
        assert counter.try_event() is False  # Exceeds limit
        assert counter.get_count() == 3

    def test_window_expiration(self):
        """Test old events expire outside window."""
        counter = SlidingWindowCounter(max_events=2, window_seconds=1)
        assert counter.try_event() is True
        assert counter.try_event() is True
        assert counter.try_event() is False  # At limit

        time.sleep(1.1)  # Wait for window to expire
        assert counter.try_event() is True  # Should work now
        assert counter.get_count() == 1  # Old events cleaned up


class TestRateLimiter:
    """Tests for RateLimiter integration."""

    def test_connection_rate_limit(self):
        """Test connection rate limiting per IP."""
        limiter = RateLimiter()
        ip = "192.168.1.1"

        # Should allow up to MAX_CONNECTIONS_PER_IP
        for i in range(8):  # MAX_CONNECTIONS_PER_IP = 8
            allowed, error = limiter.check_connection(ip)
            assert allowed is True, f"Connection {i+1} should be allowed"
            assert error is None

        # Next connection should be rejected
        allowed, error = limiter.check_connection(ip)
        assert allowed is False
        assert "Too many connections" in error

    def test_connection_release(self):
        """Test releasing connection slots."""
        limiter = RateLimiter()
        ip = "192.168.1.1"

        # Connect and track
        limiter.check_connection(ip)
        assert limiter.active_connections[ip] == 1

        # Release
        limiter.release_connection(ip)
        assert ip not in limiter.active_connections  # Cleaned up when 0

    def test_action_rate_limit(self):
        """Test action rate limiting per player."""
        limiter = RateLimiter()
        player_id = "player_123"

        # Should allow burst up to capacity (10 actions, 5/s * 2)
        for _ in range(10):
            allowed, error = limiter.check_action(player_id)
            assert allowed is True

        # Next action should be rate limited
        allowed, error = limiter.check_action(player_id)
        assert allowed is False
        assert "too quickly" in error

    def test_game_creation_rate_limit(self):
        """Test game creation rate limiting per player."""
        limiter = RateLimiter()
        player_id = "player_123"

        # Should allow up to MAX_GAMES_CREATED_PER_HOUR (10)
        for _ in range(10):
            allowed, error = limiter.check_game_creation(player_id)
            assert allowed is True

        # Next creation should be rate limited
        allowed, error = limiter.check_game_creation(player_id)
        assert allowed is False
        assert "too many games" in error

    def test_different_ips_independent(self):
        """Test different IPs have independent limits."""
        limiter = RateLimiter()

        # Fill up first IP
        for _ in range(8):
            limiter.check_connection("192.168.1.1")

        # Second IP should still work
        allowed, error = limiter.check_connection("192.168.1.2")
        assert allowed is True

    def test_different_players_independent(self):
        """Test different players have independent action limits."""
        limiter = RateLimiter()

        # Exhaust player 1's tokens
        for _ in range(10):
            limiter.check_action("player_1")

        # Player 2 should still work
        allowed, error = limiter.check_action("player_2")
        assert allowed is True

    def test_get_stats(self):
        """Test getting rate limiter statistics."""
        limiter = RateLimiter()

        limiter.check_connection("192.168.1.1")
        limiter.check_action("player_1")
        limiter.check_game_creation("player_1")

        stats = limiter.get_stats()
        assert stats["active_ips"] == 1
        assert stats["total_active_connections"] == 1
        assert stats["tracked_players_actions"] == 1
        assert stats["tracked_players_game_creation"] == 1
