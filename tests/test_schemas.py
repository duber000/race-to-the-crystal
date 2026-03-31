"""
Unit tests for action schemas.
"""

from game.schemas import (
    MoveActionSchema,
    AttackActionSchema,
    DeployActionSchema,
    EndTurnActionSchema,
    ActionSchema,
    MoveActionResponse,
    AttackActionResponse,
    DeployActionResponse,
    EndTurnActionResponse,
    ActionResponse,
    AvailableActionsResponse,
    MoveResultData,
    AttackResultData,
    DeployResultData,
    ActionResultData,
)


class TestMoveActionSchema:
    """Test cases for MoveActionSchema."""

    def test_valid_move_schema(self):
        """Test creating a valid move action schema."""
        action: MoveActionSchema = {
            "action_type": "MOVE",
            "token_id": 5,
            "destination": (12, 12),
        }
        assert action["action_type"] == "MOVE"
        assert action["token_id"] == 5
        assert action["destination"] == (12, 12)

    def test_move_schema_with_different_values(self):
        """Test move schema with different values."""
        action: MoveActionSchema = {
            "action_type": "MOVE",
            "token_id": 1,
            "destination": (0, 0),
        }
        assert action["token_id"] == 1
        assert action["destination"] == (0, 0)

    def test_move_schema_with_large_token_id(self):
        """Test move schema with large token ID."""
        action: MoveActionSchema = {
            "action_type": "MOVE",
            "token_id": 999999,
            "destination": (23, 23),
        }
        assert action["token_id"] == 999999


class TestAttackActionSchema:
    """Test cases for AttackActionSchema."""

    def test_valid_attack_schema(self):
        """Test creating a valid attack action schema."""
        action: AttackActionSchema = {
            "action_type": "ATTACK",
            "attacker_id": 5,
            "defender_id": 10,
        }
        assert action["action_type"] == "ATTACK"
        assert action["attacker_id"] == 5
        assert action["defender_id"] == 10

    def test_attack_schema_same_token_fails_type_check(self):
        """Test attack with same token (type check would catch this)."""
        # Note: TypeDict doesn't enforce at runtime, but type checker would flag this
        action: AttackActionSchema = {
            "action_type": "ATTACK",
            "attacker_id": 5,
            "defender_id": 5,  # Same as attacker - semantically wrong
        }
        assert action["attacker_id"] == action["defender_id"]


class TestDeployActionSchema:
    """Test cases for DeployActionSchema."""

    def test_valid_deploy_schema_10hp(self):
        """Test deploying 10hp token."""
        action: DeployActionSchema = {
            "action_type": "DEPLOY",
            "health_value": 10,
            "position": (2, 2),
        }
        assert action["health_value"] == 10
        assert action["position"] == (2, 2)

    def test_valid_deploy_schema_8hp(self):
        """Test deploying 8hp token."""
        action: DeployActionSchema = {
            "action_type": "DEPLOY",
            "health_value": 8,
            "position": (3, 3),
        }
        assert action["health_value"] == 8

    def test_valid_deploy_schema_6hp(self):
        """Test deploying 6hp token."""
        action: DeployActionSchema = {
            "action_type": "DEPLOY",
            "health_value": 6,
            "position": (1, 1),
        }
        assert action["health_value"] == 6

    def test_valid_deploy_schema_4hp(self):
        """Test deploying 4hp token."""
        action: DeployActionSchema = {
            "action_type": "DEPLOY",
            "health_value": 4,
            "position": (0, 0),
        }
        assert action["health_value"] == 4

    def test_deploy_schema_all_valid_health_values(self):
        """Test all valid health values for deployment."""
        valid_healths = [10, 8, 6, 4]
        for health in valid_healths:
            action: DeployActionSchema = {
                "action_type": "DEPLOY",
                "health_value": health,  # type: ignore
                "position": (2, 2),
            }
            assert action["health_value"] == health


class TestEndTurnActionSchema:
    """Test cases for EndTurnActionSchema."""

    def test_valid_end_turn_schema(self):
        """Test creating a valid end turn action schema."""
        action: EndTurnActionSchema = {
            "action_type": "END_TURN",
        }
        assert action["action_type"] == "END_TURN"


class TestActionSchemaUnion:
    """Test cases for ActionSchema union type."""

    def test_action_schema_can_be_move(self):
        """Test ActionSchema can accept MoveActionSchema."""
        action: ActionSchema = {
            "action_type": "MOVE",
            "token_id": 1,
            "destination": (5, 5),
        }
        assert action["action_type"] == "MOVE"

    def test_action_schema_can_be_attack(self):
        """Test ActionSchema can accept AttackActionSchema."""
        action: ActionSchema = {
            "action_type": "ATTACK",
            "attacker_id": 1,
            "defender_id": 2,
        }
        assert action["action_type"] == "ATTACK"

    def test_action_schema_can_be_deploy(self):
        """Test ActionSchema can accept DeployActionSchema."""
        action: ActionSchema = {
            "action_type": "DEPLOY",
            "health_value": 10,
            "position": (2, 2),
        }
        assert action["action_type"] == "DEPLOY"

    def test_action_schema_can_be_end_turn(self):
        """Test ActionSchema can accept EndTurnActionSchema."""
        action: ActionSchema = {
            "action_type": "END_TURN",
        }
        assert action["action_type"] == "END_TURN"


class TestMoveActionResponse:
    """Test cases for MoveActionResponse."""

    def test_valid_move_response(self):
        """Test creating a valid move action response."""
        response: MoveActionResponse = {
            "type": "MOVE",
            "token_id": 5,
            "token_position": [10, 10],
            "token_health": "10/10",
            "valid_destinations": [[11, 10], [9, 10], [10, 11], [10, 9]],
            "description": "Move token 5 to (11, 10)",
        }
        assert response["type"] == "MOVE"
        assert response["token_id"] == 5
        assert len(response["valid_destinations"]) == 4

    def test_move_response_no_valid_destinations(self):
        """Test move response with no valid destinations."""
        response: MoveActionResponse = {
            "type": "MOVE",
            "token_id": 5,
            "token_position": [10, 10],
            "token_health": "10/10",
            "valid_destinations": [],
            "description": "Token 5 has no valid moves",
        }
        assert response["valid_destinations"] == []


class TestAttackActionResponse:
    """Test cases for AttackActionResponse."""

    def test_valid_attack_response(self):
        """Test creating a valid attack action response."""
        response: AttackActionResponse = {
            "type": "ATTACK",
            "attacker_id": 5,
            "attacker_position": [10, 10],
            "defender_id": 10,
            "defender_position": [11, 10],
            "defender_owner": "player2",
            "damage": 5,
            "will_kill": True,
            "description": "Attack enemy token 10 for 5 damage",
        }
        assert response["type"] == "ATTACK"
        assert response["damage"] == 5
        assert response["will_kill"] is True

    def test_attack_response_no_kill(self):
        """Test attack response that won't kill."""
        response: AttackActionResponse = {
            "type": "ATTACK",
            "attacker_id": 5,
            "attacker_position": [10, 10],
            "defender_id": 10,
            "defender_position": [11, 10],
            "defender_owner": "player2",
            "damage": 2,
            "will_kill": False,
            "description": "Attack enemy token 10 for 2 damage",
        }
        assert response["will_kill"] is False


class TestDeployActionResponse:
    """Test cases for DeployActionResponse."""

    def test_valid_deploy_response(self):
        """Test creating a valid deploy action response."""
        response: DeployActionResponse = {
            "type": "DEPLOY",
            "health_value": 8,
            "positions": [[2, 2], [2, 3], [3, 2]],
            "remaining": 4,
            "description": "Deploy 8hp token to deployment zone (4 remaining)",
        }
        assert response["type"] == "DEPLOY"
        assert response["health_value"] == 8
        assert response["remaining"] == 4

    def test_deploy_response_last_token(self):
        """Test deploy response for last token of a type."""
        response: DeployActionResponse = {
            "type": "DEPLOY",
            "health_value": 10,
            "positions": [[2, 2]],
            "remaining": 0,
            "description": "Deploy 10hp token to deployment zone (0 remaining)",
        }
        assert response["remaining"] == 0


class TestEndTurnActionResponse:
    """Test cases for EndTurnActionResponse."""

    def test_valid_end_turn_response(self):
        """Test creating a valid end turn action response."""
        response: EndTurnActionResponse = {
            "type": "END_TURN",
            "description": "End your turn",
        }
        assert response["type"] == "END_TURN"


class TestActionResponseUnion:
    """Test cases for ActionResponse union type."""

    def test_action_response_can_be_any_type(self):
        """Test ActionResponse can be any response type."""
        responses: list[ActionResponse] = [
            {
                "type": "MOVE",
                "token_id": 1,
                "token_position": [0, 0],
                "token_health": "10/10",
                "valid_destinations": [[1, 0]],
                "description": "Move",
            },
            {
                "type": "ATTACK",
                "attacker_id": 1,
                "attacker_position": [0, 0],
                "defender_id": 2,
                "defender_position": [1, 0],
                "defender_owner": "p2",
                "damage": 5,
                "will_kill": True,
                "description": "Attack",
            },
            {
                "type": "DEPLOY",
                "health_value": 10,
                "positions": [[2, 2]],
                "remaining": 5,
                "description": "Deploy",
            },
            {
                "type": "END_TURN",
                "description": "End turn",
            },
        ]
        assert len(responses) == 4


class TestAvailableActionsResponse:
    """Test cases for AvailableActionsResponse."""

    def test_valid_actions_response(self):
        """Test creating a valid available actions response."""
        response: AvailableActionsResponse = {
            "phase": "MOVEMENT",
            "actions": [
                {
                    "type": "MOVE",
                    "token_id": 1,
                    "token_position": [0, 0],
                    "token_health": "10/10",
                    "valid_destinations": [[1, 0]],
                    "description": "Move token 1",
                },
                {
                    "type": "END_TURN",
                    "description": "End turn",
                },
            ],
        }
        assert response["phase"] == "MOVEMENT"
        assert len(response["actions"]) == 2

    def test_actions_response_no_actions(self):
        """Test available actions response with no actions."""
        response: AvailableActionsResponse = {
            "phase": "NOT_YOUR_TURN",
            "actions": [],
        }
        assert response["phase"] == "NOT_YOUR_TURN"
        assert response["actions"] == []

    def test_actions_response_all_phases(self):
        """Test actions response with all valid phases."""
        phases = ["MOVEMENT", "ACTION", "NOT_PLAYING", "NOT_YOUR_TURN"]
        for phase in phases:
            response: AvailableActionsResponse = {
                "phase": phase,  # type: ignore
                "actions": [],
            }
            assert response["phase"] == phase


class TestMoveResultData:
    """Test cases for MoveResultData."""

    def test_valid_move_result(self):
        """Test creating a valid move result data."""
        result: MoveResultData = {
            "token_id": 5,
            "old_position": [10, 10],
            "new_position": [11, 10],
            "mystery_triggered": False,
            "mystery_effect": "",
        }
        assert result["token_id"] == 5
        assert result["old_position"] == [10, 10]
        assert result["new_position"] == [11, 10]
        assert result["mystery_triggered"] is False

    def test_move_result_with_mystery(self):
        """Test move result with mystery square triggered."""
        result: MoveResultData = {
            "token_id": 5,
            "old_position": [10, 10],
            "new_position": [15, 15],
            "mystery_triggered": True,
            "mystery_effect": "TELEPORT",
        }
        assert result["mystery_triggered"] is True
        assert result["mystery_effect"] == "TELEPORT"

    def test_move_result_minimal(self):
        """Test move result with minimal fields."""
        # All fields are optional
        result: MoveResultData = {}
        assert result == {}


class TestAttackResultData:
    """Test cases for AttackResultData."""

    def test_valid_attack_result(self):
        """Test creating a valid attack result data."""
        result: AttackResultData = {
            "attacker_id": 5,
            "defender_id": 10,
            "damage_dealt": 5,
            "defender_killed": True,
            "attacker_position": [10, 10],
            "defender_position": [11, 10],
        }
        assert result["damage_dealt"] == 5
        assert result["defender_killed"] is True

    def test_attack_result_no_kill(self):
        """Test attack result where defender survives."""
        result: AttackResultData = {
            "attacker_id": 5,
            "defender_id": 10,
            "damage_dealt": 3,
            "defender_killed": False,
        }
        assert result["defender_killed"] is False


class TestDeployResultData:
    """Test cases for DeployResultData."""

    def test_valid_deploy_result(self):
        """Test creating a valid deploy result data."""
        result: DeployResultData = {
            "token_id": 50,
            "health_value": 8,
            "position": [2, 2],
        }
        assert result["token_id"] == 50
        assert result["health_value"] == 8
        assert result["position"] == [2, 2]


class TestActionResultDataUnion:
    """Test cases for ActionResultData union type."""

    def test_action_result_can_be_none(self):
        """Test ActionResultData can be None."""
        result: ActionResultData = None
        assert result is None

    def test_action_result_can_be_move(self):
        """Test ActionResultData can be MoveResultData."""
        result: ActionResultData = {
            "token_id": 1,
            "old_position": [0, 0],
            "new_position": [1, 0],
        }
        assert result is not None

    def test_action_result_can_be_attack(self):
        """Test ActionResultData can be AttackResultData."""
        result: ActionResultData = {
            "attacker_id": 1,
            "defender_id": 2,
            "damage_dealt": 5,
        }
        assert result is not None

    def test_action_result_can_be_deploy(self):
        """Test ActionResultData can be DeployResultData."""
        result: ActionResultData = {
            "token_id": 50,
            "health_value": 10,
        }
        assert result is not None
