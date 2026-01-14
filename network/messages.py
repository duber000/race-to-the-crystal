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
    AI = "AI"  # AI agent player (TCP/WebSocket)
    WEB_BROWSER = "WEB_BROWSER"  # Web browser client (Babylon.js)
    HTTP_AI = "HTTP_AI"  # AI agent using HTTP POST + SSE


# Message Classification for SSE-Primary Mode
# Messages sent via SSE (Server-Sent Events / Mercure)
SSE_MESSAGES = {
    MessageType.FULL_STATE,
    MessageType.STATE_UPDATE,
    MessageType.TURN_CHANGE,
    MessageType.TOKEN_MOVED,
    MessageType.COMBAT_RESULT,
    MessageType.GENERATOR_UPDATE,
    MessageType.CRYSTAL_UPDATE,
    MessageType.MYSTERY_EVENT,
    MessageType.TOKEN_DEPLOYED,
    MessageType.GAME_WON,
}

# Messages sent via WebSocket (commands, control, responses)
WEBSOCKET_MESSAGES = {
    # Game Commands
    MessageType.MOVE,
    MessageType.ATTACK,
    MessageType.DEPLOY,
    MessageType.END_TURN,
    # Lobby Operations
    MessageType.CREATE_GAME,
    MessageType.JOIN_GAME,
    MessageType.START_GAME,
    MessageType.READY,
    MessageType.LIST_GAMES,
    MessageType.LEAVE_GAME,
    # Connection Management
    MessageType.CONNECT,
    MessageType.RECONNECT,
    MessageType.DISCONNECT,
    MessageType.HEARTBEAT,
    # Responses
    MessageType.CONNECT_ACK,
    MessageType.RECONNECT_ACK,
    MessageType.RECONNECT_FAILED,
    MessageType.HEARTBEAT_ACK,
    MessageType.ERROR,
    MessageType.INVALID_ACTION,
    MessageType.GAME_LIST,
    # Lobby Events (Phase 1 - keep on WebSocket)
    MessageType.PLAYER_JOINED,
    MessageType.PLAYER_LEFT,
    MessageType.PLAYER_DISCONNECTED,
    MessageType.PLAYER_RECONNECTED,
    # Chat
    MessageType.CHAT,
}

# Client types that should receive state updates via SSE in SSE-primary mode
SSE_CAPABLE_CLIENTS = {ClientType.WEB_BROWSER, ClientType.HTTP_AI}
