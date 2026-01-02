"""
Game Coordinator for Race to the Crystal server.

Manages running game instances, executes actions, and coordinates
game state synchronization.
"""
import logging
from typing import Dict, Optional, List, Tuple

from game.game_state import GameState
from game.player import Player
from game.ai_actions import AIAction, AIActionExecutor
from game.ai_observation import AIObserver
from server.lobby import GameLobby, PlayerInfo
from shared.enums import PlayerColor
from network.protocol import ProtocolHandler, NetworkMessage
from network.messages import MessageType


logger = logging.getLogger(__name__)


class GameSession:
    """
    Represents an active game instance.

    Manages game state and action execution for one game.
    """

    def __init__(self, game_id: str, lobby: GameLobby):
        """
        Initialize a game session from a lobby.

        Args:
            game_id: Unique game identifier
            lobby: GameLobby with players ready to start
        """
        self.game_id = game_id
        self.game_name = lobby.game_name

        # Create game state
        num_players = len(lobby.players)
        self.game_state = GameState.create_game(num_players)

        # Map player_ids to game state player_ids
        # The lobby has UUIDs, the game state has player indices
        self.network_to_game_id: Dict[str, str] = {}
        self.game_to_network_id: Dict[str, str] = {}

        # Initialize players from lobby
        self._initialize_players(lobby)

        # Start the game (creates tokens and auto-deploys initial positions)
        self.game_state.start_game()
        logger.info(f"Game started with {len(self.game_state.tokens)} tokens")

        # Action executor for validating and executing actions
        self.executor = AIActionExecutor()

        logger.info(
            f"Created game session {game_id} ({self.game_name}) "
            f"with {num_players} players"
        )

    def _initialize_players(self, lobby: GameLobby) -> None:
        """
        Initialize game players from lobby player info.

        Args:
            lobby: GameLobby with player information
        """
        # Get players sorted by color index (join order)
        sorted_players = sorted(
            lobby.players.values(),
            key=lambda p: p.color_index
        )

        # Map network player IDs to game player IDs
        for i, player_info in enumerate(sorted_players):
            # Game state uses player_0, player_1, etc.
            game_player_id = f"player_{i}"

            # Get the actual Player object from game state
            game_player = self.game_state.get_player(game_player_id)

            if game_player:
                # Update player name
                game_player.name = player_info.player_name

                # Create bidirectional mapping
                self.network_to_game_id[player_info.player_id] = game_player_id
                self.game_to_network_id[game_player_id] = player_info.player_id

                logger.info(
                    f"Mapped {player_info.player_name} "
                    f"({player_info.player_id[:8]}) -> {game_player_id}"
                )

    def execute_action(
        self,
        network_player_id: str,
        action: AIAction
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Execute a game action for a player.

        Args:
            network_player_id: Network UUID of the player
            action: AIAction to execute

        Returns:
            Tuple of (success, message, result_data)
        """
        # Map network player ID to game player ID
        game_player_id = self.network_to_game_id.get(network_player_id)
        if not game_player_id:
            return False, "Player not in game", None

        # Execute action using AIActionExecutor
        success, message, result_data = self.executor.execute_action(
            action,
            self.game_state,
            game_player_id
        )

        if success:
            logger.info(
                f"Action executed in game {self.game_id}: "
                f"{action.action_type} by {game_player_id}"
            )
        else:
            logger.warning(
                f"Action failed in game {self.game_id}: "
                f"{action.action_type} by {game_player_id} - {message}"
            )

        return success, message, result_data

    def get_game_state_for_player(self, network_player_id: str) -> Optional[dict]:
        """
        Get serialized game state from a player's perspective.

        Args:
            network_player_id: Network UUID of the player

        Returns:
            Dictionary with game state and perspective info
        """
        game_player_id = self.network_to_game_id.get(network_player_id)
        if not game_player_id:
            return None

        # Serialize game state
        state_dict = self.game_state.to_dict()

        # Add player perspective
        state_dict["perspective_player_id"] = game_player_id
        state_dict["your_player_id"] = game_player_id

        return state_dict

    def get_situation_report(self, network_player_id: str) -> Optional[str]:
        """
        Get AI-friendly text description of game state.

        Args:
            network_player_id: Network UUID of the player

        Returns:
            Text situation report, or None if player not found
        """
        game_player_id = self.network_to_game_id.get(network_player_id)
        if not game_player_id:
            return None

        return AIObserver.get_situation_report(self.game_state, game_player_id)

    def get_current_network_player_id(self) -> Optional[str]:
        """
        Get network player ID of current turn player.

        Returns:
            Network UUID of current player
        """
        game_player_id = self.game_state.current_turn_player_id
        return self.game_to_network_id.get(game_player_id)

    def is_game_over(self) -> bool:
        """Check if game has ended."""
        from shared.enums import GamePhase
        return self.game_state.phase == GamePhase.ENDED

    def get_winner_network_id(self) -> Optional[str]:
        """Get network player ID of winner (if game ended)."""
        if not self.is_game_over():
            return None

        game_winner_id = self.game_state.winner_id
        if not game_winner_id:
            return None

        return self.game_to_network_id.get(game_winner_id)


class GameCoordinator:
    """
    Coordinates multiple active game sessions on the server.

    Manages game lifecycle and routes actions to appropriate games.
    """

    def __init__(self):
        """Initialize the game coordinator."""
        self.active_games: Dict[str, GameSession] = {}
        self.player_to_game: Dict[str, str] = {}  # Maps player_id -> game_id
        logger.info("Game coordinator initialized")

    def create_game(self, lobby: GameLobby) -> GameSession:
        """
        Create a new game session from a lobby.

        Args:
            lobby: GameLobby ready to start

        Returns:
            Created GameSession
        """
        game_session = GameSession(lobby.game_id, lobby)
        self.active_games[lobby.game_id] = game_session

        # Map all players to this game
        for player_id in lobby.players.keys():
            self.player_to_game[player_id] = lobby.game_id

        logger.info(
            f"Created game session {lobby.game_id} with "
            f"{len(lobby.players)} players"
        )

        return game_session

    def get_game(self, game_id: str) -> Optional[GameSession]:
        """
        Get an active game session.

        Args:
            game_id: Game to retrieve

        Returns:
            GameSession or None if not found
        """
        return self.active_games.get(game_id)

    def get_player_game(self, player_id: str) -> Optional[GameSession]:
        """
        Get the game session a player is in.

        Args:
            player_id: Player to find

        Returns:
            GameSession or None if player not in a game
        """
        game_id = self.player_to_game.get(player_id)
        if not game_id:
            return None

        return self.active_games.get(game_id)

    def execute_action(
        self,
        player_id: str,
        action: AIAction
    ) -> Tuple[bool, str, Optional[Dict], Optional[GameSession]]:
        """
        Execute an action for a player in their current game.

        Args:
            player_id: Network player ID
            action: Action to execute

        Returns:
            Tuple of (success, message, result_data, game_session)
        """
        game_session = self.get_player_game(player_id)
        if not game_session:
            return False, "Player not in a game", None, None

        success, message, result_data = game_session.execute_action(player_id, action)

        return success, message, result_data, game_session

    def end_game(self, game_id: str) -> bool:
        """
        End a game session and clean up.

        Args:
            game_id: Game to end

        Returns:
            True if game ended successfully
        """
        game_session = self.active_games.pop(game_id, None)
        if not game_session:
            return False

        # Remove player mappings
        players_to_remove = [
            pid for pid, gid in self.player_to_game.items()
            if gid == game_id
        ]

        for player_id in players_to_remove:
            self.player_to_game.pop(player_id, None)

        logger.info(f"Ended game session {game_id}")
        return True

    def remove_player(self, player_id: str) -> Optional[str]:
        """
        Remove a player from their game (on disconnect).

        Args:
            player_id: Player to remove

        Returns:
            Game ID the player was in, or None
        """
        game_id = self.player_to_game.pop(player_id, None)
        if game_id:
            logger.info(f"Removed player {player_id[:8]} from game {game_id}")

        return game_id

    def get_active_game_count(self) -> int:
        """Get number of active games."""
        return len(self.active_games)

    def list_active_games(self) -> List[dict]:
        """
        Get list of active games.

        Returns:
            List of game info dictionaries
        """
        return [
            {
                "game_id": game_id,
                "game_name": session.game_name,
                "players": len(session.network_to_game_id),
                "turn": session.game_state.turn_number,
                "is_finished": session.is_game_over(),
            }
            for game_id, session in self.active_games.items()
        ]
