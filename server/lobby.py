"""
Lobby management for Race to the Crystal multiplayer.

Handles game creation, player joining, ready status, and game starting.
"""
import uuid
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from network.messages import ClientType


logger = logging.getLogger(__name__)


class GameStatus(Enum):
    """Status of a game in the lobby."""
    WAITING = "WAITING"  # Waiting for players
    READY = "READY"  # All players ready, can start
    STARTING = "STARTING"  # Game is being started
    IN_PROGRESS = "IN_PROGRESS"  # Game is active
    FINISHED = "FINISHED"  # Game has ended


@dataclass
class PlayerInfo:
    """Information about a player in the lobby."""
    player_id: str
    player_name: str
    client_type: ClientType
    is_ready: bool = False
    color_index: int = 0  # 0-3 for CYAN, MAGENTA, YELLOW, GREEN

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "client_type": self.client_type.value,
            "is_ready": self.is_ready,
            "color_index": self.color_index,
        }


@dataclass
class GameLobby:
    """Represents a game lobby that players can join."""
    game_id: str
    game_name: str
    host_player_id: str
    max_players: int = 4
    min_players: int = 2
    players: Dict[str, PlayerInfo] = field(default_factory=dict)
    status: GameStatus = GameStatus.WAITING

    def add_player(
        self,
        player_id: str,
        player_name: str,
        client_type: ClientType
    ) -> bool:
        """
        Add a player to the lobby.

        Args:
            player_id: Unique player identifier
            player_name: Player's display name
            client_type: HUMAN or AI

        Returns:
            True if player added successfully, False if lobby is full
        """
        if len(self.players) >= self.max_players:
            logger.warning(f"Cannot add player to full lobby {self.game_id}")
            return False

        if player_id in self.players:
            logger.warning(f"Player {player_id} already in lobby {self.game_id}")
            return False

        # Assign color based on join order
        color_index = len(self.players)

        player_info = PlayerInfo(
            player_id=player_id,
            player_name=player_name,
            client_type=client_type,
            color_index=color_index
        )

        self.players[player_id] = player_info
        logger.info(
            f"Player {player_name} ({client_type.value}) joined lobby {self.game_name} "
            f"({len(self.players)}/{self.max_players})"
        )

        return True

    def remove_player(self, player_id: str) -> bool:
        """
        Remove a player from the lobby.

        Args:
            player_id: Player to remove

        Returns:
            True if player was removed, False if not found
        """
        if player_id not in self.players:
            return False

        player_info = self.players.pop(player_id)
        logger.info(
            f"Player {player_info.player_name} left lobby {self.game_name} "
            f"({len(self.players)}/{self.max_players})"
        )

        # If host left, assign new host
        if player_id == self.host_player_id and self.players:
            self.host_player_id = next(iter(self.players.keys()))
            logger.info(f"New host for {self.game_name}: {self.host_player_id}")

        # Reassign color indices
        self._reassign_colors()

        return True

    def set_player_ready(self, player_id: str, is_ready: bool) -> bool:
        """
        Set a player's ready status.

        Args:
            player_id: Player to update
            is_ready: Ready status

        Returns:
            True if updated, False if player not found
        """
        if player_id not in self.players:
            return False

        self.players[player_id].is_ready = is_ready
        logger.info(
            f"Player {self.players[player_id].player_name} "
            f"{'ready' if is_ready else 'not ready'} in {self.game_name}"
        )

        return True

    def all_players_ready(self) -> bool:
        """
        Check if all players are ready and minimum player count is met.

        Returns:
            True if game can start
        """
        if len(self.players) < self.min_players:
            return False

        return all(player.is_ready for player in self.players.values())

    def can_start(self) -> bool:
        """
        Check if the game can be started.

        Returns:
            True if game can start (all ready, min players met, waiting status)
        """
        return (
            self.status == GameStatus.WAITING and
            self.all_players_ready() and
            len(self.players) >= self.min_players
        )

    def _reassign_colors(self) -> None:
        """Reassign color indices after a player leaves."""
        for i, player_info in enumerate(self.players.values()):
            player_info.color_index = i

    def get_player_list(self) -> List[dict]:
        """
        Get list of all players in the lobby.

        Returns:
            List of player info dictionaries
        """
        return [player.to_dict() for player in self.players.values()]

    def to_dict(self) -> dict:
        """Convert lobby to dictionary for serialization."""
        return {
            "game_id": self.game_id,
            "game_name": self.game_name,
            "host_player_id": self.host_player_id,
            "max_players": self.max_players,
            "min_players": self.min_players,
            "current_players": len(self.players),
            "status": self.status.value,
            "players": self.get_player_list(),
        }


class LobbyManager:
    """
    Manages all game lobbies on the server.

    Handles lobby creation, joining, and lifecycle.
    """

    def __init__(self):
        """Initialize the lobby manager."""
        self.lobbies: Dict[str, GameLobby] = {}
        logger.info("Lobby manager initialized")

    def create_lobby(
        self,
        player_id: str,
        player_name: str,
        game_name: str,
        client_type: ClientType,
        max_players: int = 4
    ) -> GameLobby:
        """
        Create a new game lobby.

        Args:
            player_id: Host player ID
            player_name: Host player name
            game_name: Name of the game
            client_type: Host client type (HUMAN or AI)
            max_players: Maximum number of players (2-4)

        Returns:
            Created GameLobby
        """
        game_id = str(uuid.uuid4())

        lobby = GameLobby(
            game_id=game_id,
            game_name=game_name,
            host_player_id=player_id,
            max_players=max_players
        )

        # Add host as first player
        lobby.add_player(player_id, player_name, client_type)

        self.lobbies[game_id] = lobby

        logger.info(f"Created lobby '{game_name}' (ID: {game_id}) hosted by {player_name}")

        return lobby

    def get_lobby(self, game_id: str) -> Optional[GameLobby]:
        """
        Get a lobby by ID.

        Args:
            game_id: Lobby to retrieve

        Returns:
            GameLobby or None if not found
        """
        return self.lobbies.get(game_id)

    def join_lobby(
        self,
        game_id: str,
        player_id: str,
        player_name: str,
        client_type: ClientType
    ) -> Optional[GameLobby]:
        """
        Join an existing lobby.

        Args:
            game_id: Lobby to join
            player_id: Joining player ID
            player_name: Joining player name
            client_type: Client type (HUMAN or AI)

        Returns:
            GameLobby if joined successfully, None if failed
        """
        lobby = self.lobbies.get(game_id)
        if not lobby:
            logger.warning(f"Cannot join: Lobby {game_id} not found")
            return None

        if lobby.status != GameStatus.WAITING:
            logger.warning(f"Cannot join: Lobby {game_id} is not waiting for players")
            return None

        success = lobby.add_player(player_id, player_name, client_type)
        if not success:
            return None

        return lobby

    def leave_lobby(self, game_id: str, player_id: str) -> bool:
        """
        Remove a player from a lobby.

        Args:
            game_id: Lobby to leave
            player_id: Player leaving

        Returns:
            True if player removed, False otherwise
        """
        lobby = self.lobbies.get(game_id)
        if not lobby:
            return False

        success = lobby.remove_player(player_id)

        # If lobby is empty, remove it
        if len(lobby.players) == 0:
            self.lobbies.pop(game_id)
            logger.info(f"Removed empty lobby {game_id}")

        return success

    def set_ready(self, game_id: str, player_id: str, is_ready: bool) -> bool:
        """
        Set a player's ready status.

        Args:
            game_id: Lobby ID
            player_id: Player ID
            is_ready: Ready status

        Returns:
            True if updated successfully
        """
        lobby = self.lobbies.get(game_id)
        if not lobby:
            return False

        return lobby.set_player_ready(player_id, is_ready)

    def start_game(self, game_id: str) -> Optional[GameLobby]:
        """
        Start a game (if all players ready).

        Args:
            game_id: Lobby to start

        Returns:
            GameLobby if started, None if cannot start
        """
        lobby = self.lobbies.get(game_id)
        if not lobby:
            return None

        if not lobby.can_start():
            logger.warning(f"Cannot start game {game_id}: conditions not met")
            return None

        lobby.status = GameStatus.STARTING
        logger.info(f"Starting game {game_id} ({lobby.game_name})")

        return lobby

    def set_game_in_progress(self, game_id: str) -> bool:
        """
        Mark a game as in progress.

        Args:
            game_id: Game ID

        Returns:
            True if status updated
        """
        lobby = self.lobbies.get(game_id)
        if not lobby:
            return False

        lobby.status = GameStatus.IN_PROGRESS
        logger.info(f"Game {game_id} now IN_PROGRESS")
        return True

    def finish_game(self, game_id: str) -> bool:
        """
        Mark a game as finished.

        Args:
            game_id: Game ID

        Returns:
            True if status updated
        """
        lobby = self.lobbies.get(game_id)
        if not lobby:
            return False

        lobby.status = GameStatus.FINISHED
        logger.info(f"Game {game_id} FINISHED")
        return True

    def list_available_lobbies(self) -> List[dict]:
        """
        Get list of lobbies that can be joined.

        Returns:
            List of lobby info dictionaries
        """
        available = [
            lobby.to_dict()
            for lobby in self.lobbies.values()
            if lobby.status == GameStatus.WAITING and
               len(lobby.players) < lobby.max_players
        ]

        return available

    def get_player_lobby(self, player_id: str) -> Optional[GameLobby]:
        """
        Find which lobby a player is in.

        Args:
            player_id: Player to find

        Returns:
            GameLobby containing the player, or None
        """
        for lobby in self.lobbies.values():
            if player_id in lobby.players:
                return lobby

        return None

    def remove_player_from_all(self, player_id: str) -> None:
        """
        Remove a player from all lobbies (on disconnect).

        Args:
            player_id: Player to remove
        """
        lobby = self.get_player_lobby(player_id)
        if lobby:
            self.leave_lobby(lobby.game_id, player_id)
