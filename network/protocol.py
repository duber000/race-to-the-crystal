"""
Network Protocol for Race to the Crystal.

Handles message serialization, deserialization, and validation for
client-server communication using JSON over TCP.
"""
import json
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from network.messages import MessageType, ClientType
from game.ai_actions import AIAction, MoveAction, AttackAction, DeployAction, EndTurnAction


@dataclass
class NetworkMessage:
    """
    Base network message structure.

    All messages follow this format:
    {
        "type": "MESSAGE_TYPE",
        "timestamp": 1234567890.123,
        "player_id": "uuid-string",
        "data": {...}
    }
    """
    type: MessageType
    timestamp: float
    player_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        msg_dict = {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "player_id": self.player_id,
            "data": self.data or {}
        }
        return json.dumps(msg_dict)

    @staticmethod
    def from_json(json_str: str) -> 'NetworkMessage':
        """Deserialize message from JSON string."""
        try:
            msg_dict = json.loads(json_str)
            return NetworkMessage(
                type=MessageType(msg_dict["type"]),
                timestamp=msg_dict["timestamp"],
                player_id=msg_dict.get("player_id"),
                data=msg_dict.get("data", {})
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Invalid message format: {e}")


class ProtocolHandler:
    """Handles message creation and parsing for the network protocol."""

    # --- CONNECTION MESSAGES ---

    @staticmethod
    def create_connect_message(
        player_name: str,
        client_type: ClientType = ClientType.HUMAN
    ) -> NetworkMessage:
        """Create a CONNECT message for initial connection."""
        return NetworkMessage(
            type=MessageType.CONNECT,
            timestamp=time.time(),
            data={
                "player_name": player_name,
                "client_type": client_type.value,
            }
        )

    @staticmethod
    def create_connect_ack_message(player_id: str, session_data: Dict) -> NetworkMessage:
        """Create a CONNECT_ACK response with assigned player_id."""
        return NetworkMessage(
            type=MessageType.CONNECT_ACK,
            timestamp=time.time(),
            player_id=player_id,
            data=session_data
        )

    @staticmethod
    def create_disconnect_message(player_id: str, reason: str = "") -> NetworkMessage:
        """Create a DISCONNECT message."""
        return NetworkMessage(
            type=MessageType.DISCONNECT,
            timestamp=time.time(),
            player_id=player_id,
            data={"reason": reason}
        )

    @staticmethod
    def create_reconnect_message(
        player_id: str,
        game_id: Optional[str] = None
    ) -> NetworkMessage:
        """Create a RECONNECT message to rejoin a game."""
        return NetworkMessage(
            type=MessageType.RECONNECT,
            timestamp=time.time(),
            player_id=player_id,
            data={"game_id": game_id} if game_id else {}
        )

    @staticmethod
    def create_reconnect_ack_message(
        player_id: str,
        game_id: str,
        session_data: Dict
    ) -> NetworkMessage:
        """Create a RECONNECT_ACK response confirming successful reconnection."""
        return NetworkMessage(
            type=MessageType.RECONNECT_ACK,
            timestamp=time.time(),
            player_id=player_id,
            data={
                "game_id": game_id,
                "session_data": session_data
            }
        )

    @staticmethod
    def create_reconnect_failed_message(
        player_id: str,
        reason: str
    ) -> NetworkMessage:
        """Create a RECONNECT_FAILED response when reconnection fails."""
        return NetworkMessage(
            type=MessageType.RECONNECT_FAILED,
            timestamp=time.time(),
            player_id=player_id,
            data={"reason": reason}
        )

    @staticmethod
    def create_heartbeat() -> NetworkMessage:
        """Create a HEARTBEAT message."""
        return NetworkMessage(
            type=MessageType.HEARTBEAT,
            timestamp=time.time()
        )

    # --- LOBBY MESSAGES ---

    @staticmethod
    def create_game_message(
        player_id: str,
        game_name: str,
        max_players: int = 4
    ) -> NetworkMessage:
        """Create a CREATE_GAME message."""
        return NetworkMessage(
            type=MessageType.CREATE_GAME,
            timestamp=time.time(),
            player_id=player_id,
            data={
                "game_name": game_name,
                "max_players": max_players,
            }
        )

    @staticmethod
    def join_game_message(player_id: str, game_id: str) -> NetworkMessage:
        """Create a JOIN_GAME message."""
        return NetworkMessage(
            type=MessageType.JOIN_GAME,
            timestamp=time.time(),
            player_id=player_id,
            data={"game_id": game_id}
        )

    @staticmethod
    def ready_message(player_id: str, is_ready: bool = True) -> NetworkMessage:
        """Create a READY message."""
        return NetworkMessage(
            type=MessageType.READY,
            timestamp=time.time(),
            player_id=player_id,
            data={"ready": is_ready}
        )

    @staticmethod
    def list_games_message(player_id: str) -> NetworkMessage:
        """Create a LIST_GAMES message."""
        return NetworkMessage(
            type=MessageType.LIST_GAMES,
            timestamp=time.time(),
            player_id=player_id
        )

    # --- ACTION MESSAGES ---

    @staticmethod
    def action_to_message(action: AIAction, player_id: str) -> NetworkMessage:
        """
        Convert an AIAction to a network message.

        This bridges the AI action system with network protocol.
        """
        # Map action type to message type
        action_type_map = {
            "MOVE": MessageType.MOVE,
            "ATTACK": MessageType.ATTACK,
            "DEPLOY": MessageType.DEPLOY,
            "END_TURN": MessageType.END_TURN,
        }

        msg_type = action_type_map.get(action.action_type)
        if not msg_type:
            raise ValueError(f"Unknown action type: {action.action_type}")

        return NetworkMessage(
            type=msg_type,
            timestamp=time.time(),
            player_id=player_id,
            data=action.to_dict()
        )

    @staticmethod
    def message_to_action(message: NetworkMessage) -> AIAction:
        """
        Convert a network message to an AIAction.

        This allows network messages to be executed using AIActionExecutor.
        """
        action_type = message.type
        data = message.data or {}

        if action_type == MessageType.MOVE:
            return MoveAction(
                token_id=data["token_id"],
                destination=tuple(data["destination"])
            )
        elif action_type == MessageType.ATTACK:
            return AttackAction(
                attacker_id=data["attacker_id"],
                defender_id=data["defender_id"]
            )
        elif action_type == MessageType.DEPLOY:
            return DeployAction(
                health_value=data["health_value"],
                position=tuple(data["position"])
            )
        elif action_type == MessageType.END_TURN:
            return EndTurnAction()
        else:
            raise ValueError(f"Cannot convert message type {action_type} to action")

    # --- STATE SYNC MESSAGES ---

    @staticmethod
    def create_full_state_message(game_state_dict: Dict, player_id: str) -> NetworkMessage:
        """
        Create a FULL_STATE message with complete game state.

        Used for initial sync when joining or reconnecting.
        """
        return NetworkMessage(
            type=MessageType.FULL_STATE,
            timestamp=time.time(),
            player_id=player_id,
            data={"game_state": game_state_dict}
        )

    @staticmethod
    def create_state_update_message(update_data: Dict) -> NetworkMessage:
        """
        Create a STATE_UPDATE message with delta changes.

        More efficient than full state for incremental updates.
        """
        return NetworkMessage(
            type=MessageType.STATE_UPDATE,
            timestamp=time.time(),
            data=update_data
        )

    @staticmethod
    def create_turn_change_message(
        current_player_id: str,
        turn_number: int,
        phase: str
    ) -> NetworkMessage:
        """Create a TURN_CHANGE notification."""
        return NetworkMessage(
            type=MessageType.TURN_CHANGE,
            timestamp=time.time(),
            data={
                "current_player_id": current_player_id,
                "turn_number": turn_number,
                "phase": phase,
            }
        )

    # --- EVENT MESSAGES ---

    @staticmethod
    def create_combat_result_message(result_data: Dict) -> NetworkMessage:
        """Create a COMBAT_RESULT event message."""
        return NetworkMessage(
            type=MessageType.COMBAT_RESULT,
            timestamp=time.time(),
            data=result_data
        )

    @staticmethod
    def create_token_moved_message(token_id: int, old_pos: Tuple, new_pos: Tuple) -> NetworkMessage:
        """Create a TOKEN_MOVED event message."""
        return NetworkMessage(
            type=MessageType.TOKEN_MOVED,
            timestamp=time.time(),
            data={
                "token_id": token_id,
                "old_position": list(old_pos),
                "new_position": list(new_pos),
            }
        )

    @staticmethod
    def create_game_won_message(winner_id: str, winner_name: str) -> NetworkMessage:
        """Create a GAME_WON event message."""
        return NetworkMessage(
            type=MessageType.GAME_WON,
            timestamp=time.time(),
            data={
                "winner_id": winner_id,
                "winner_name": winner_name,
            }
        )

    @staticmethod
    def create_error_message(error_msg: str, player_id: Optional[str] = None) -> NetworkMessage:
        """Create an ERROR message."""
        return NetworkMessage(
            type=MessageType.ERROR,
            timestamp=time.time(),
            player_id=player_id,
            data={"error": error_msg}
        )

    @staticmethod
    def create_invalid_action_message(
        action_type: str,
        reason: str,
        player_id: str
    ) -> NetworkMessage:
        """Create an INVALID_ACTION message."""
        return NetworkMessage(
            type=MessageType.INVALID_ACTION,
            timestamp=time.time(),
            player_id=player_id,
            data={
                "action_type": action_type,
                "reason": reason,
            }
        )


class MessageFraming:
    """
    Handles message framing for TCP streams.

    Messages are length-prefixed: [4 bytes length][JSON message]
    """

    @staticmethod
    def frame_message(json_str: str) -> bytes:
        """
        Frame a JSON message for transmission.

        Format: [4-byte big-endian length][UTF-8 JSON]
        """
        json_bytes = json_str.encode('utf-8')
        length = len(json_bytes)
        # Pack length as 4-byte big-endian integer
        length_bytes = length.to_bytes(4, byteorder='big')
        return length_bytes + json_bytes

    @staticmethod
    def parse_frame(data: bytes) -> Tuple[Optional[bytes], bytes]:
        """
        Parse a framed message from TCP stream.

        Args:
            data: Raw bytes from TCP stream

        Returns:
            Tuple of (message_bytes, remaining_data)
            - message_bytes: Complete message if available, None otherwise
            - remaining_data: Unparsed bytes for next call
        """
        # Need at least 4 bytes for length prefix
        if len(data) < 4:
            return None, data

        # Read length prefix
        length = int.from_bytes(data[:4], byteorder='big')

        # Check if we have the complete message
        if len(data) < 4 + length:
            return None, data  # Wait for more data

        # Extract message
        message_bytes = data[4:4+length]
        remaining = data[4+length:]

        return message_bytes, remaining
