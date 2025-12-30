"""
Network Message Type Definitions.

Defines all message types used in client-server communication.
"""
from enum import Enum


class MessageType(Enum):
    """All network message types for Race to the Crystal."""

    # Connection management
    CONNECT = "CONNECT"
    CONNECT_ACK = "CONNECT_ACK"
    RECONNECT = "RECONNECT"
    RECONNECT_ACK = "RECONNECT_ACK"
    RECONNECT_FAILED = "RECONNECT_FAILED"
    DISCONNECT = "DISCONNECT"
    HEARTBEAT = "HEARTBEAT"
    HEARTBEAT_ACK = "HEARTBEAT_ACK"

    # Lobby management
    CREATE_GAME = "CREATE_GAME"
    JOIN_GAME = "JOIN_GAME"
    LEAVE_GAME = "LEAVE_GAME"
    LIST_GAMES = "LIST_GAMES"
    GAME_LIST = "GAME_LIST"
    PLAYER_JOINED = "PLAYER_JOINED"
    PLAYER_LEFT = "PLAYER_LEFT"
    PLAYER_RECONNECTED = "PLAYER_RECONNECTED"
    PLAYER_DISCONNECTED = "PLAYER_DISCONNECTED"
    READY = "READY"
    START_GAME = "START_GAME"

    # Game actions (map to AIAction types)
    MOVE = "MOVE"
    ATTACK = "ATTACK"
    DEPLOY = "DEPLOY"
    END_TURN = "END_TURN"

    # State synchronization
    FULL_STATE = "FULL_STATE"
    STATE_UPDATE = "STATE_UPDATE"
    TURN_CHANGE = "TURN_CHANGE"

    # Game events
    COMBAT_RESULT = "COMBAT_RESULT"
    TOKEN_MOVED = "TOKEN_MOVED"
    TOKEN_DEPLOYED = "TOKEN_DEPLOYED"
    MYSTERY_EVENT = "MYSTERY_EVENT"
    GENERATOR_UPDATE = "GENERATOR_UPDATE"
    CRYSTAL_UPDATE = "CRYSTAL_UPDATE"
    GAME_WON = "GAME_WON"

    # Chat
    CHAT = "CHAT"

    # Error handling
    ERROR = "ERROR"
    INVALID_ACTION = "INVALID_ACTION"


class ClientType(Enum):
    """Type of client connecting to server."""
    HUMAN = "HUMAN"  # Human player with GUI
    AI = "AI"  # AI agent player
