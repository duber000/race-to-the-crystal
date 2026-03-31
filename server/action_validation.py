"""
Shared action validation utilities for Race to the Crystal server.

Eliminates duplicated action validation logic between HTTP and WebSocket handlers.
"""


def validate_action_fields(
    action_type: str, data: dict
) -> tuple[str, str, str] | None:
    """
    Validate that action data contains all required fields.

    Args:
        action_type: Action type string (MOVE, ATTACK, DEPLOY, END_TURN)
        data: Action data dictionary

    Returns:
        Tuple of (field_name, error_code, message) if validation fails, None if valid.
        error_code is one of "missing_field" or "invalid_value".
    """
    action_type_lower = action_type.lower()

    if action_type_lower == "move":
        if data.get("token_id") is None:
            return ("token_id", "missing_field", "token_id is required for MOVE")
        destination = data.get("destination")
        if (
            not destination
            or not isinstance(destination, list)
            or len(destination) != 2
        ):
            return ("destination", "invalid_value", "destination must be [x, y] coordinates")

    elif action_type_lower == "attack":
        if data.get("attacker_id") is None:
            return ("attacker_id", "missing_field", "attacker_id is required for ATTACK")
        defender_id = data.get("defender_id") or data.get("target_id")
        if defender_id is None:
            return ("defender_id", "missing_field", "defender_id or target_id is required for ATTACK")

    elif action_type_lower == "deploy":
        if data.get("health_value") is None:
            return ("health_value", "missing_field", "health_value is required for DEPLOY")
        position = data.get("position")
        if not position or not isinstance(position, list) or len(position) != 2:
            return ("position", "invalid_value", "position must be [x, y] coordinates")

    elif action_type_lower not in ("end_turn",):
        return (
            "type",
            "invalid_value",
            f"Unknown action type: {action_type}. Allowed: MOVE, ATTACK, DEPLOY, END_TURN",
        )

    return None


def normalize_action_data(data: dict) -> dict:
    """
    Normalize action data into a consistent format for message creation.

    Args:
        data: Raw action data dictionary

    Returns:
        Normalized action data dictionary
    """
    defender_id = data.get("defender_id") or data.get("target_id")

    return {
        "type": data.get("type", "").lower(),
        "token_id": data.get("token_id"),
        "destination": data.get("destination"),
        "attacker_id": data.get("attacker_id"),
        "defender_id": defender_id,
        "position": data.get("position"),
        "health_value": data.get("health_value"),
    }
