"""
Shared message routing for server-side network handling.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from network.messages import MessageType
from network.protocol import NetworkMessage

ServerHandler = Callable[[str, NetworkMessage], Awaitable[None]]


def build_server_routes(game_server) -> dict[MessageType, ServerHandler]:
    """Build message routing table for GameServer handlers."""
    return {
        MessageType.DISCONNECT: lambda player_id, message: game_server._handle_disconnect(
            player_id
        ),
        MessageType.HEARTBEAT: game_server._handle_heartbeat,
        MessageType.CREATE_GAME: game_server._handle_create_game,
        MessageType.JOIN_GAME: game_server._handle_join_game,
        MessageType.LEAVE_GAME: game_server._handle_leave_game,
        MessageType.LIST_GAMES: lambda player_id, message: game_server._handle_list_games(
            player_id
        ),
        MessageType.READY: game_server._handle_ready,
        MessageType.START_GAME: game_server._handle_start_game,
        MessageType.MOVE: game_server._handle_game_action,
        MessageType.ATTACK: game_server._handle_game_action,
        MessageType.DEPLOY: game_server._handle_game_action,
        MessageType.END_TURN: game_server._handle_game_action,
        MessageType.CHAT: game_server._handle_chat,
    }


async def route_server_message(
    routes: dict[MessageType, ServerHandler],
    player_id: str,
    message: NetworkMessage,
    on_unhandled: Callable[[NetworkMessage], Awaitable[None]] | None,
) -> bool:
    """Route a message to the registered handler."""
    handler = routes.get(message.type)
    if not handler:
        if on_unhandled:
            await on_unhandled(message)
        return False

    await handler(player_id, message)
    return True
