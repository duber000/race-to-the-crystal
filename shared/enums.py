"""
Enumerations for game types and states.
"""
from enum import Enum, auto


class CellType(Enum):
    """Types of cells on the game board."""
    NORMAL = auto()
    GENERATOR = auto()
    CRYSTAL = auto()
    MYSTERY = auto()
    START = auto()


class GamePhase(Enum):
    """Phases of the game."""
    SETUP = auto()          # Players joining, not started
    PLAYING = auto()        # Game in progress
    ENDED = auto()          # Game finished, winner declared


class TurnPhase(Enum):
    """Phases within a single turn."""
    MOVEMENT = auto()       # Player can move tokens
    ACTION = auto()         # Player can attack or capture
    END_TURN = auto()       # Turn ending, validation and updates


class PlayerColor(Enum):
    """Player color identifiers."""
    CYAN = 0
    MAGENTA = 1
    YELLOW = 2
    GREEN = 3


class MessageType(Enum):
    """Network message types."""
    # Connection messages
    CONNECT = "CONNECT"
    DISCONNECT = "DISCONNECT"
    HEARTBEAT = "HEARTBEAT"

    # Lobby messages
    JOIN_LOBBY = "JOIN_LOBBY"
    LEAVE_LOBBY = "LEAVE_LOBBY"
    READY = "READY"
    START_GAME = "START_GAME"

    # Game action messages
    MOVE_TOKEN = "MOVE_TOKEN"
    ATTACK = "ATTACK"
    CAPTURE_GENERATOR = "CAPTURE_GENERATOR"
    CAPTURE_CRYSTAL = "CAPTURE_CRYSTAL"
    END_TURN = "END_TURN"

    # State synchronization messages
    FULL_STATE = "FULL_STATE"
    STATE_UPDATE = "STATE_UPDATE"
    TURN_CHANGE = "TURN_CHANGE"

    # Event messages
    COMBAT_RESULT = "COMBAT_RESULT"
    MYSTERY_EVENT = "MYSTERY_EVENT"
    GENERATOR_CAPTURED = "GENERATOR_CAPTURED"
    GENERATOR_DISABLED = "GENERATOR_DISABLED"
    CRYSTAL_CAPTURED = "CRYSTAL_CAPTURED"
    GAME_WON = "GAME_WON"

    # Error messages
    INVALID_MOVE = "INVALID_MOVE"
    ERROR = "ERROR"


class MysteryEffect(Enum):
    """Effects from mystery squares."""
    HEAL = auto()           # Heal to full health
    TELEPORT = auto()       # Teleport back to start


class CombatResult(Enum):
    """Results of combat."""
    HIT = auto()            # Attack hit, defender damaged
    KILLED = auto()         # Attack killed defender
    INVALID = auto()        # Invalid attack attempt
