"""
Tests for network protocol and message handling.
"""
import time
import pytest

from network.protocol import NetworkMessage, ProtocolHandler, MessageFraming
from network.messages import MessageType, ClientType
from game.ai_actions import MoveAction, AttackAction, DeployAction, EndTurnAction


class TestNetworkMessage:
    """Test NetworkMessage serialization and deserialization."""

    def test_message_to_json(self):
        """Test converting NetworkMessage to JSON."""
        msg = NetworkMessage(
            type=MessageType.CONNECT,
            timestamp=time.time(),
            player_id="test-player",
            data={"player_name": "TestPlayer"}
        )

        json_str = msg.to_json()
        assert json_str is not None
        assert "CONNECT" in json_str
        assert "test-player" in json_str

    def test_message_from_json(self):
        """Test parsing NetworkMessage from JSON."""
        json_str = '{"type": "CONNECT", "timestamp": 1234567890.0, "player_id": "test", "data": {"foo": "bar"}}'

        msg = NetworkMessage.from_json(json_str)
        assert msg.type == MessageType.CONNECT
        assert msg.timestamp == 1234567890.0
        assert msg.player_id == "test"
        assert msg.data["foo"] == "bar"

    def test_message_roundtrip(self):
        """Test message serialization roundtrip."""
        original = NetworkMessage(
            type=MessageType.MOVE,
            timestamp=time.time(),
            player_id="player-123",
            data={"token_id": 5, "destination": [10, 12]}
        )

        json_str = original.to_json()
        restored = NetworkMessage.from_json(json_str)

        assert restored.type == original.type
        assert restored.player_id == original.player_id
        assert restored.data["token_id"] == 5
        assert restored.data["destination"] == [10, 12]

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises ValueError."""
        with pytest.raises(ValueError):
            NetworkMessage.from_json("not valid json")

        with pytest.raises(ValueError):
            NetworkMessage.from_json('{"invalid": "message"}')


class TestProtocolHandler:
    """Test ProtocolHandler message creation."""

    def test_create_connect_message(self):
        """Test creating CONNECT message."""
        handler = ProtocolHandler()
        msg = handler.create_connect_message("TestPlayer", ClientType.HUMAN)

        assert msg.type == MessageType.CONNECT
        assert msg.data["player_name"] == "TestPlayer"
        assert msg.data["client_type"] == "HUMAN"

    def test_create_connect_ack_message(self):
        """Test creating CONNECT_ACK message."""
        handler = ProtocolHandler()
        session_data = {"player_id": "test-123", "server_version": "1.0"}

        msg = handler.create_connect_ack_message("test-123", session_data)

        assert msg.type == MessageType.CONNECT_ACK
        assert msg.player_id == "test-123"
        assert msg.data["server_version"] == "1.0"

    def test_action_to_message_move(self):
        """Test converting MoveAction to network message."""
        handler = ProtocolHandler()
        action = MoveAction(token_id=5, destination=(10, 12))

        msg = handler.action_to_message(action, "player-123")

        assert msg.type == MessageType.MOVE
        assert msg.player_id == "player-123"
        assert msg.data["token_id"] == 5
        assert msg.data["destination"] == [10, 12]

    def test_action_to_message_attack(self):
        """Test converting AttackAction to network message."""
        handler = ProtocolHandler()
        action = AttackAction(attacker_id=3, defender_id=7)

        msg = handler.action_to_message(action, "player-456")

        assert msg.type == MessageType.ATTACK
        assert msg.player_id == "player-456"
        assert msg.data["attacker_id"] == 3
        assert msg.data["defender_id"] == 7

    def test_action_to_message_deploy(self):
        """Test converting DeployAction to network message."""
        handler = ProtocolHandler()
        action = DeployAction(health_value=10, position=(2, 3))

        msg = handler.action_to_message(action, "player-789")

        assert msg.type == MessageType.DEPLOY
        assert msg.data["health_value"] == 10
        assert msg.data["position"] == [2, 3]

    def test_action_to_message_end_turn(self):
        """Test converting EndTurnAction to network message."""
        handler = ProtocolHandler()
        action = EndTurnAction()

        msg = handler.action_to_message(action, "player-000")

        assert msg.type == MessageType.END_TURN
        assert msg.player_id == "player-000"

    def test_message_to_action_move(self):
        """Test converting MOVE message to MoveAction."""
        handler = ProtocolHandler()
        msg = NetworkMessage(
            type=MessageType.MOVE,
            timestamp=time.time(),
            player_id="test",
            data={"token_id": 5, "destination": [10, 12]}
        )

        action = handler.message_to_action(msg)

        assert isinstance(action, MoveAction)
        assert action.token_id == 5
        assert action.destination == (10, 12)

    def test_message_to_action_attack(self):
        """Test converting ATTACK message to AttackAction."""
        handler = ProtocolHandler()
        msg = NetworkMessage(
            type=MessageType.ATTACK,
            timestamp=time.time(),
            player_id="test",
            data={"attacker_id": 3, "defender_id": 7}
        )

        action = handler.message_to_action(msg)

        assert isinstance(action, AttackAction)
        assert action.attacker_id == 3
        assert action.defender_id == 7

    def test_action_roundtrip(self):
        """Test action -> message -> action roundtrip."""
        handler = ProtocolHandler()
        original_action = MoveAction(token_id=10, destination=(5, 7))

        # Convert to message
        msg = handler.action_to_message(original_action, "player-1")

        # Convert back to action
        restored_action = handler.message_to_action(msg)

        assert isinstance(restored_action, MoveAction)
        assert restored_action.token_id == original_action.token_id
        assert restored_action.destination == original_action.destination


class TestMessageFraming:
    """Test TCP message framing."""

    def test_frame_message(self):
        """Test framing a message."""
        json_str = '{"type": "TEST", "data": {}}'
        framed = MessageFraming.frame_message(json_str)

        # Should have 4-byte length prefix + JSON
        assert len(framed) == 4 + len(json_str)

        # First 4 bytes should be length
        length = int.from_bytes(framed[:4], byteorder='big')
        assert length == len(json_str)

    def test_parse_complete_frame(self):
        """Test parsing a complete framed message."""
        json_str = '{"type": "TEST"}'
        framed = MessageFraming.frame_message(json_str)

        message_bytes, remaining = MessageFraming.parse_frame(framed)

        assert message_bytes is not None
        assert message_bytes.decode('utf-8') == json_str
        assert remaining == b''

    def test_parse_incomplete_frame(self):
        """Test parsing incomplete data."""
        json_str = '{"type": "TEST"}'
        framed = MessageFraming.frame_message(json_str)

        # Only send first half
        partial = framed[:len(framed)//2]

        message_bytes, remaining = MessageFraming.parse_frame(partial)

        # Should return None and keep all data
        assert message_bytes is None
        assert remaining == partial

    def test_parse_multiple_frames(self):
        """Test parsing multiple messages in buffer."""
        json1 = '{"type": "MSG1"}'
        json2 = '{"type": "MSG2"}'

        framed1 = MessageFraming.frame_message(json1)
        framed2 = MessageFraming.frame_message(json2)

        # Concatenate both messages
        data = framed1 + framed2

        # Parse first message
        msg1_bytes, remaining = MessageFraming.parse_frame(data)
        assert msg1_bytes.decode('utf-8') == json1

        # Parse second message from remaining data
        msg2_bytes, final_remaining = MessageFraming.parse_frame(remaining)
        assert msg2_bytes.decode('utf-8') == json2
        assert final_remaining == b''

    def test_parse_partial_length_prefix(self):
        """Test parsing with incomplete length prefix."""
        # Less than 4 bytes
        data = b'\x00\x00'

        message_bytes, remaining = MessageFraming.parse_frame(data)

        assert message_bytes is None
        assert remaining == data
