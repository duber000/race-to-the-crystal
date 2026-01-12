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

    SETUP = auto()  # Players joining, not started
    PLAYING = auto()  # Game in progress
    ENDED = auto()  # Game finished, winner declared


class TurnPhase(Enum):
    """Phases within a single turn."""

    MOVEMENT = auto()  # Player can move tokens
    ACTION = auto()  # Player can attack or capture
    END_TURN = auto()  # Turn ending, validation and updates


class PlayerColor(Enum):
    """Player color identifiers."""

    CYAN = 0
    MAGENTA = 1
    YELLOW = 2
    GREEN = 3


class MysteryEffect(Enum):
    """Effects from mystery squares."""

    HEAL = auto()  # Heal to full health
    TELEPORT = auto()  # Teleport back to start


class CombatResult(Enum):
    """Results of combat."""

    HIT = auto()  # Attack hit, defender damaged
    KILLED = auto()  # Attack killed defender
    INVALID = auto()  # Invalid attack attempt


class CrystalEffect(Enum):
    """Effects applied by the crystal to players."""

    FOG_OF_WAR = auto()  # Players can't see other players' tokens
    PHANTOM_ENEMIES = auto()  # Players see illusion enemy tokens
    DAMAGE_BOOST = auto()  # Player deals increased damage
    SPEED_BOOST = auto()  # Player's tokens move extra spaces
