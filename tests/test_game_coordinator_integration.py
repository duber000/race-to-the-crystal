"""
Integration tests for GameCoordinator with GameState.create_game().
"""
import pytest
from server.game_coordinator import GameCoordinator
from server.lobby import GameLobby, PlayerInfo
from network.messages import ClientType


class TestGameCoordinatorIntegration:
    """Test GameCoordinator integration with GameState.create_game()."""

    def test_create_game_from_lobby(self):
        """Test creating a game session from a lobby with 2 players."""
        # Create a lobby with 2 players
        lobby = GameLobby('test-game', 'Test Game', 'host-player')
        player1 = PlayerInfo('player1', 'Alice', ClientType.HUMAN, False, 0)
        player2 = PlayerInfo('player2', 'Bob', ClientType.HUMAN, False, 1)
        lobby.players['player1'] = player1
        lobby.players['player2'] = player2

        # Create game coordinator and game session
        coordinator = GameCoordinator()
        game_session = coordinator.create_game(lobby)

        # Verify game session was created
        assert game_session is not None
        assert game_session.game_id == 'test-game'
        assert game_session.game_name == 'Test Game'
        assert len(game_session.network_to_game_id) == 2
        assert len(game_session.game_state.players) == 2

        # Verify player mappings
        assert 'player1' in game_session.network_to_game_id
        assert 'player2' in game_session.network_to_game_id
        assert game_session.network_to_game_id['player1'] == 'player_0'
        assert game_session.network_to_game_id['player2'] == 'player_1'

        # Verify game state players
        assert 'player_0' in game_session.game_state.players
        assert 'player_1' in game_session.game_state.players
        assert game_session.game_state.players['player_0'].name == 'Alice'
        assert game_session.game_state.players['player_1'].name == 'Bob'

    def test_create_game_from_lobby_4_players(self):
        """Test creating a game session from a lobby with 4 players."""
        # Create a lobby with 4 players
        lobby = GameLobby('test-game-4p', '4 Player Game', 'host-player')
        
        players = []
        for i in range(4):
            player = PlayerInfo(f'player{i+1}', f'Player{i+1}', ClientType.HUMAN, False, i)
            lobby.players[f'player{i+1}'] = player
            players.append(player)

        # Create game coordinator and game session
        coordinator = GameCoordinator()
        game_session = coordinator.create_game(lobby)

        # Verify game session was created
        assert game_session is not None
        assert game_session.game_id == 'test-game-4p'
        assert game_session.game_name == '4 Player Game'
        assert len(game_session.network_to_game_id) == 4
        assert len(game_session.game_state.players) == 4

        # Verify all players are mapped
        for i in range(4):
            network_id = f'player{i+1}'
            game_id = f'player_{i}'
            assert network_id in game_session.network_to_game_id
            assert game_session.network_to_game_id[network_id] == game_id
            assert game_id in game_session.game_state.players

    def test_game_session_player_mapping(self):
        """Test that player mapping works correctly for game actions."""
        # Create a lobby with 2 players
        lobby = GameLobby('test-mapping', 'Mapping Test', 'host-player')
        player1 = PlayerInfo('player1', 'Alice', ClientType.HUMAN, False, 0)
        player2 = PlayerInfo('player2', 'Bob', ClientType.HUMAN, False, 1)
        lobby.players['player1'] = player1
        lobby.players['player2'] = player2

        # Create game coordinator and game session
        coordinator = GameCoordinator()
        game_session = coordinator.create_game(lobby)

        # Test network to game ID mapping
        game_player_id = game_session.network_to_game_id.get('player1')
        assert game_player_id == 'player_0'

        # Test game to network ID mapping
        network_player_id = game_session.game_to_network_id.get('player_0')
        assert network_player_id == 'player1'

        # Test getting game state for player
        state_dict = game_session.get_game_state_for_player('player1')
        assert state_dict is not None
        assert state_dict['perspective_player_id'] == 'player_0'
        assert state_dict['your_player_id'] == 'player_0'

    def test_game_coordinator_stores_game_session(self):
        """Test that GameCoordinator properly stores and retrieves game sessions."""
        # Create a lobby with 2 players
        lobby = GameLobby('test-storage', 'Storage Test', 'host-player')
        player1 = PlayerInfo('player1', 'Alice', ClientType.HUMAN, False, 0)
        player2 = PlayerInfo('player2', 'Bob', ClientType.HUMAN, False, 1)
        lobby.players['player1'] = player1
        lobby.players['player2'] = player2

        # Create game coordinator and game session
        coordinator = GameCoordinator()
        game_session = coordinator.create_game(lobby)

        # Verify game is stored in coordinator
        retrieved_game = coordinator.get_game('test-storage')
        assert retrieved_game is game_session

        # Verify players are mapped to game
        player1_game = coordinator.get_player_game('player1')
        player2_game = coordinator.get_player_game('player2')
        assert player1_game is game_session
        assert player2_game is game_session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
