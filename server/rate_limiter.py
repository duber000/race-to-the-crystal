"""
Rate Limiting for Race to the Crystal Server.

Provides token bucket and sliding window rate limiting for connections
and actions to prevent DoS attacks and abuse.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Optional

import logging

logger = logging.getLogger(__name__)

# Rate limit configurations
MAX_CONNECTIONS_PER_IP = 8  # Max concurrent connections per IP (4 players + buffer)
MAX_ACTIONS_PER_SECOND = 5  # Max actions per player per second
MAX_GAMES_CREATED_PER_HOUR = 10  # Max games created per player per hour
CONNECTION_WINDOW_SECONDS = 60  # Time window for connection tracking


@dataclass
class TokenBucket:
    """
    Token bucket rate limiter.

    Allows bursts up to capacity, refills at fixed rate.
    """

    capacity: int
    refill_rate: float  # Tokens per second
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize with full capacity."""
        self.tokens = float(self.capacity)

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens available and consumed, False if rate limited
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )

        self.last_refill = now


@dataclass
class SlidingWindowCounter:
    """
    Sliding window rate limiter.

    Tracks events in a time window, rejects if limit exceeded.
    """

    max_events: int
    window_seconds: int
    events: deque = field(default_factory=deque)

    def try_event(self) -> bool:
        """
        Try to record an event.

        Returns:
            True if event allowed, False if rate limited
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old events outside window
        while self.events and self.events[0] < cutoff:
            self.events.popleft()

        # Check if we're at limit
        if len(self.events) >= self.max_events:
            return False

        # Record event
        self.events.append(now)
        return True

    def get_count(self) -> int:
        """Get current count of events in window."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Remove old events
        while self.events and self.events[0] < cutoff:
            self.events.popleft()

        return len(self.events)


class RateLimiter:
    """
    Comprehensive rate limiter for game server.

    Tracks and limits:
    - Connections per IP address
    - Actions per player
    - Game creation per player
    """

    def __init__(self):
        """Initialize rate limiter."""
        # Connection tracking per IP
        self.ip_connections: Dict[str, SlidingWindowCounter] = defaultdict(
            lambda: SlidingWindowCounter(
                max_events=MAX_CONNECTIONS_PER_IP,
                window_seconds=CONNECTION_WINDOW_SECONDS
            )
        )

        # Action rate limiting per player (token bucket)
        self.player_actions: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=MAX_ACTIONS_PER_SECOND * 2,  # Allow bursts
                refill_rate=MAX_ACTIONS_PER_SECOND
            )
        )

        # Game creation rate limiting per player
        self.player_game_creation: Dict[str, SlidingWindowCounter] = defaultdict(
            lambda: SlidingWindowCounter(
                max_events=MAX_GAMES_CREATED_PER_HOUR,
                window_seconds=3600  # 1 hour
            )
        )

        # Track active connections per IP
        self.active_connections: Dict[str, int] = defaultdict(int)

    def check_connection(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """
        Check if connection from IP is allowed.

        Args:
            ip_address: Client IP address

        Returns:
            (allowed, error_message) tuple
        """
        # Check connection limit
        counter = self.ip_connections[ip_address]

        if not counter.try_event():
            logger.warning(
                f"Rate limit exceeded: Too many connections from {ip_address} "
                f"({counter.get_count()}/{MAX_CONNECTIONS_PER_IP} in {CONNECTION_WINDOW_SECONDS}s)"
            )
            return (
                False,
                f"Too many connections from your IP address. "
                f"Please wait before connecting again."
            )

        # Track active connection
        self.active_connections[ip_address] += 1

        logger.debug(
            f"Connection allowed from {ip_address} "
            f"(active: {self.active_connections[ip_address]}, "
            f"recent: {counter.get_count()})"
        )

        return (True, None)

    def release_connection(self, ip_address: str) -> None:
        """
        Release a connection slot for IP.

        Args:
            ip_address: Client IP address
        """
        if ip_address in self.active_connections:
            self.active_connections[ip_address] = max(
                0, self.active_connections[ip_address] - 1
            )

            # Clean up if no active connections
            if self.active_connections[ip_address] == 0:
                del self.active_connections[ip_address]

    def check_action(self, player_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if player action is allowed.

        Args:
            player_id: Player ID

        Returns:
            (allowed, error_message) tuple
        """
        bucket = self.player_actions[player_id]

        if not bucket.consume(1):
            logger.warning(
                f"Rate limit exceeded: Player {player_id[:8]} sending actions too fast "
                f"(limit: {MAX_ACTIONS_PER_SECOND}/s)"
            )
            return (
                False,
                f"You are sending actions too quickly. "
                f"Please slow down (limit: {MAX_ACTIONS_PER_SECOND} actions/second)."
            )

        return (True, None)

    def check_game_creation(self, player_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if player can create a game.

        Args:
            player_id: Player ID

        Returns:
            (allowed, error_message) tuple
        """
        counter = self.player_game_creation[player_id]

        if not counter.try_event():
            logger.warning(
                f"Rate limit exceeded: Player {player_id[:8]} creating too many games "
                f"({counter.get_count()}/{MAX_GAMES_CREATED_PER_HOUR} per hour)"
            )
            return (
                False,
                f"You have created too many games recently. "
                f"Please wait before creating another game (limit: {MAX_GAMES_CREATED_PER_HOUR}/hour)."
            )

        return (True, None)

    def cleanup_player(self, player_id: str) -> None:
        """
        Clean up rate limiting data for disconnected player.

        Args:
            player_id: Player ID
        """
        # Don't delete data immediately - keep for a while to prevent
        # rapid reconnect abuse. Data will naturally expire from sliding windows.
        pass

    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with current rate limiter stats
        """
        return {
            "active_ips": len(self.active_connections),
            "total_active_connections": sum(self.active_connections.values()),
            "tracked_players_actions": len(self.player_actions),
            "tracked_players_game_creation": len(self.player_game_creation),
        }
