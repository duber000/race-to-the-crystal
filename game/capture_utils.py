"""
Shared utilities for token counting and dominance logic.

Used by both Generator and Crystal capture mechanics to avoid duplication.
"""

from shared.types import TokenID, PlayerID


def count_tokens_by_player(
    tokens_at_position: list[tuple[TokenID, PlayerID]],
) -> dict[PlayerID, list[TokenID]]:
    """
    Group tokens by their controlling player.

    Args:
        tokens_at_position: List of (token_id, player_id) tuples

    Returns:
        Dictionary mapping player_id to list of their token_ids
    """
    player_token_counts: dict[PlayerID, list[TokenID]] = {}
    for token_id, player_id in tokens_at_position:
        if player_id not in player_token_counts:
            player_token_counts[player_id] = []
        player_token_counts[player_id].append(token_id)
    return player_token_counts


def find_dominant_player(
    player_token_counts: dict[PlayerID, list[TokenID]],
) -> tuple[PlayerID | None, int]:
    """
    Determine which player has the most tokens, if any.

    Args:
        player_token_counts: Dictionary mapping player_id to token_ids

    Returns:
        Tuple of (dominant_player_id, token_count). Returns (None, count) if contested.
    """
    dominant_player: PlayerID | None = None
    dominant_count = 0

    for player_id, token_ids in player_token_counts.items():
        if len(token_ids) > dominant_count:
            dominant_player = player_id
            dominant_count = len(token_ids)
        elif len(token_ids) == dominant_count and dominant_count > 0:
            dominant_player = None  # Contested

    return (dominant_player, dominant_count)
