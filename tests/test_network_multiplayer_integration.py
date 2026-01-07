"""
Comprehensive integration test for network multiplayer functionality.

Tests the full workflow of two players connecting, creating a game, and taking turns.
"""

import asyncio
import pytest
import time
from typing import List, Dict

from server.game_server import GameServer
from client.network_client import NetworkClient
from network.messages import MessageType, ClientType
from network.protocol import NetworkMessage
from game.ai_actions import MoveAction, EndTurnAction


class MockMessageHandler:
    """Mock message handler to track received messages."""

    def __init__(self):
        self.received_messages: List[NetworkMessage] = []
        self.game_states: List[Dict] = []

    async def handle_message(self, message: NetworkMessage):
        """Handle received messages and track them."""
        self.received_messages.append(message)

        # Track game states
        if message.type == MessageType.FULL_STATE:
            data = message.data or {}
            if "game_state" in data:
                self.game_states.append(data["game_state"])


class TestNetworkMultiplayerIntegration:
    """Test network multiplayer functionality end-to-end."""

    @pytest.mark.asyncio
    async def test_two_player_game_workflow(self):
        """Test complete workflow: connect, create game, join, start, take turns."""
        # Create server
        server = GameServer(host="localhost", port=9999)

        # Start server in background
        server_task = asyncio.create_task(server.start())

        # Give server time to start
        await asyncio.sleep(0.5)

        try:
            # Create two clients
            client1 = NetworkClient("Player1", ClientType.HUMAN)
            client2 = NetworkClient("Player2", ClientType.HUMAN)

            # Create message handlers
            handler1 = MockMessageHandler()
            handler2 = MockMessageHandler()

            client1.on_message = handler1.handle_message
            client2.on_message = handler2.handle_message

            # Connect both clients
            assert await client1.connect("localhost", 9999)
            assert await client2.connect("localhost", 9999)

            # Verify both clients got player IDs
            assert client1.get_player_id() is not None
            assert client2.get_player_id() is not None

            # Client 1 creates a game
            assert await client1.create_game("Test Game", max_players=2)

            # Wait for game creation confirmation
            await asyncio.sleep(0.2)

            # Verify game was created (client1 should have game_id)
            assert client1.game_id is not None

            # Client 2 joins the game
            assert await client2.join_game(client1.game_id)

            # Wait for join confirmation
            await asyncio.sleep(0.2)

            # Both clients set ready
            assert await client1.set_ready(True)
            assert await client2.set_ready(True)

            # Wait for ready status updates
            await asyncio.sleep(0.2)

            # Client 1 starts the game (as host)
            start_msg = NetworkMessage(
                type=MessageType.START_GAME,
                timestamp=time.time(),
                player_id=client1.get_player_id(),
            )
            assert await client1.connection.send_message(start_msg)

            # Wait for game to start
            await asyncio.sleep(0.5)

            # Verify both clients received full game states
            assert len(handler1.game_states) > 0
            assert len(handler2.game_states) > 0

            # Check that game states are valid
            state1 = handler1.game_states[-1]
            state2 = handler2.game_states[-1]

            assert "current_turn_player_id" in state1
            assert "current_turn_player_id" in state2
            assert "turn_number" in state1
            assert "turn_number" in state2

            # Verify turn management - one player should be current
            current_player_id = state1["current_turn_player_id"]
            assert current_player_id in ["player_0", "player_1"]

            # Test taking turns
            # Player 1 tries to move (if it's their turn)
            if current_player_id == "player_0":
                # Player 1's turn - send a move action
                move_action = MoveAction(token_id=0, destination=(1, 0))  # Simple move
                assert await client1.send_action(move_action)

                # Wait for action processing
                await asyncio.sleep(0.2)

                # Player 1 ends turn
                end_turn_action = EndTurnAction()
                assert await client1.send_action(end_turn_action)

                # Wait for turn change
                await asyncio.sleep(0.2)

                # Verify turn changed to player 2
                latest_state = handler2.game_states[-1]
                assert latest_state["current_turn_player_id"] == "player_1"
                assert latest_state["turn_number"] == 1  # Should still be turn 1

            else:
                # Player 2's turn - similar logic
                move_action = MoveAction(token_id=1, destination=(1, 1))  # Simple move
                assert await client2.send_action(move_action)

                # Wait for action processing
                await asyncio.sleep(0.2)

                # Player 2 ends turn
                end_turn_action = EndTurnAction()
                assert await client2.send_action(end_turn_action)

                # Wait for turn change
                await asyncio.sleep(0.2)

                # Verify turn changed to player 1
                latest_state = handler1.game_states[-1]
                assert latest_state["current_turn_player_id"] == "player_0"
                assert latest_state["turn_number"] == 1  # Should still be turn 1

            print("✅ Two-player network game workflow completed successfully")

        finally:
            # Cleanup
            await client1.disconnect()
            await client2.disconnect()
            await server.stop()
            # Suppress CancelledError when awaiting server task after stop
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_heartbeat_functionality(self):
        """Test heartbeat mechanism between client and server."""
        # Create server
        server = GameServer(host="localhost", port=9998)
        server_task = asyncio.create_task(server.start())

        await asyncio.sleep(0.5)

        try:
            # Create client
            client = NetworkClient("HeartbeatTest", ClientType.HUMAN)
            handler = MockMessageHandler()
            client.on_message = handler.handle_message

            # Connect
            assert await client.connect("localhost", 9998)

            # Send heartbeat
            heartbeat_msg = NetworkMessage(
                type=MessageType.HEARTBEAT,
                timestamp=time.time(),
                player_id=client.get_player_id(),
            )
            assert await client.connection.send_message(heartbeat_msg)

            # Wait for heartbeat acknowledgment
            await asyncio.sleep(0.2)

            # Check if we received HEARTBEAT_ACK
            heartbeat_acks = [
                msg
                for msg in handler.received_messages
                if msg.type == MessageType.HEARTBEAT_ACK
            ]

            assert len(heartbeat_acks) > 0, "Should receive HEARTBEAT_ACK from server"

            print("✅ Heartbeat functionality working correctly")

        finally:
            await client.disconnect()
            await server.stop()
            # Suppress CancelledError when awaiting server task after stop
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_turn_change_notifications(self):
        """Test that turn changes are communicated via FULL_STATE updates."""
        # Create server
        server = GameServer(host="localhost", port=9997)
        server_task = asyncio.create_task(server.start())

        await asyncio.sleep(0.5)

        try:
            # Create two clients
            client1 = NetworkClient("TurnTest1", ClientType.HUMAN)
            client2 = NetworkClient("TurnTest2", ClientType.HUMAN)

            handler1 = MockMessageHandler()
            handler2 = MockMessageHandler()

            client1.on_message = handler1.handle_message
            client2.on_message = handler2.handle_message

            # Connect and setup game
            assert await client1.connect("localhost", 9997)
            assert await client2.connect("localhost", 9997)

            assert await client1.create_game("Turn Test Game", max_players=2)
            await asyncio.sleep(0.2)

            assert await client2.join_game(client1.game_id)
            await asyncio.sleep(0.2)

            assert await client1.set_ready(True)
            assert await client2.set_ready(True)
            await asyncio.sleep(0.2)

            # Start game
            start_msg = NetworkMessage(
                type=MessageType.START_GAME,
                timestamp=time.time(),
                player_id=client1.get_player_id(),
            )
            assert await client1.connection.send_message(start_msg)
            await asyncio.sleep(0.5)

            # Save initial state
            initial_state = handler1.game_states[-1]
            initial_player = initial_state["current_turn_player_id"]
            initial_state_count = len(handler1.game_states)

            # Take a turn to trigger turn change
            if initial_player == "player_0":
                # Player 1's turn
                end_turn_action = EndTurnAction()
                assert await client1.send_action(end_turn_action)
            else:
                # Player 2's turn
                end_turn_action = EndTurnAction()
                assert await client2.send_action(end_turn_action)

            await asyncio.sleep(0.2)

            # Check that we received updated FULL_STATE messages after turn change
            assert len(handler1.game_states) > initial_state_count, (
                "Should receive FULL_STATE update after turn change"
            )

            # Verify turn changed in the new state
            new_state = handler1.game_states[-1]
            new_player = new_state["current_turn_player_id"]

            assert "current_turn_player_id" in new_state
            assert "turn_number" in new_state
            assert "turn_phase" in new_state

            # Turn should have changed to the other player
            assert new_player != initial_player, (
                "Turn should change to the other player"
            )

            print("✅ Turn change notifications working correctly")

        finally:
            await client1.disconnect()
            await client2.disconnect()
            await server.stop()
            # Suppress CancelledError when awaiting server task after stop
            try:
                await server_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
