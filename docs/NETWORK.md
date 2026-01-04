# Race to the Crystal - Network Infrastructure

This document describes the multiplayer network architecture for Race to the Crystal, including how to run servers, connect clients, and integrate AI players.

## Architecture Overview

### Design Philosophy

Race to the Crystal uses a **server-authoritative client-server** architecture:

- **Server**: Maintains the single source of truth for game state
- **Clients**: Send action requests and receive state updates
- **Validation**: All actions validated on server before execution
- **State Sync**: Full state sent to clients, no client-side prediction needed

This design prevents cheating, ensures consistency across all players, and works well for turn-based gameplay.

### Network Stack

- **Transport**: TCP sockets with asyncio for async I/O
- **Protocol**: JSON messages with length-prefixed framing
- **Message Types**: 35+ message types for lobby, actions, events, and sync
- **Client Types**: Supports both `HUMAN` (GUI) and `AI` (autonomous) clients

### Architecture Diagram

```
┌─────────────────┐         ┌─────────────────┐
│  Human Client   │         │   AI Client     │
│  (Arcade UI)    │         │  (Autonomous)   │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │      NetworkClient        │
         │    (TCP Connection)       │
         │                           │
         └───────────┬───────────────┘
                     │
                     │  JSON Messages
                     │  (length-prefixed)
                     │
         ┌───────────▼────────────┐
         │    Game Server         │
         │  ┌──────────────────┐  │
         │  │  ConnectionPool  │  │
         │  └──────────────────┘  │
         │  ┌──────────────────┐  │
         │  │  LobbyManager    │  │
         │  └──────────────────┘  │
         │  ┌──────────────────┐  │
         │  │ GameCoordinator  │  │
         │  │   ┌──────────┐   │  │
         │  │   │GameState │   │  │
         │  │   │  +       │   │  │
         │  │   │AIExecutor│   │  │
         │  │   └──────────┘   │  │
         │  └──────────────────┘  │
         └────────────────────────┘
```

## Quick Start

### Understanding the Architecture

**IMPORTANT:** The game uses a client-server architecture:

```
Server (race-server)      Client 1           Client 2
     │                        │                 │
     │  ◄────connect──────────┤                 │
     │  ─────CONNECT_ACK─────►│                 │
     │  ◄────CREATE_GAME──────┤                 │
     │  ─────LOBBY_UPDATE────►│                 │
     │                        │                 │
     │  ◄────connect──────────┼─────────────────┤
     │  ─────CONNECT_ACK──────┼────────────────►│
     │  ◄────JOIN_GAME────────┼─────────────────┤
     │  ─────LOBBY_UPDATE────►├────────────────►│
```

- **`race-server`** is a **central coordinator** (like a Discord server)
  - Starts empty with **no games**
  - Waits for clients to create game lobbies
  - Can host multiple games simultaneously

- **"Host Network Game"** creates a **game lobby** (like creating a voice channel)
  - A client connects to the server
  - Tells the server to create a new game lobby
  - Other clients can then join this lobby

### 1. Start the Server (Required First!)

```bash
# Terminal 1: Start the central server
uv run race-server

# The server starts EMPTY - no games exist yet!
# Output: "Server listening on 0.0.0.0:8888"
```

**The server just sits there waiting.** It doesn't create any games - clients do that!

### 2. Host a Game (Client Creates Lobby)

```bash
# Terminal 2: Launch game client to HOST
uv run race-to-the-crystal
```

#### Creating a Game Lobby:
1. Click **"Host Network Game"**
2. Enter your player name (e.g., "Alice")
3. Server host: **localhost** (connecting to server from step 1)
4. Port: **8888** (must match server port)
5. Enter game name (e.g., "Alice's Game")
6. Click **"Create Game"**
7. ✅ **A game lobby is now created on the server!**
8. Wait in the lobby for other players to join

### 3. Join the Game (Additional Clients)

```bash
# Terminal 3: Launch another game client to JOIN
uv run race-to-the-crystal
```

#### Joining an Existing Lobby:
1. Click **"Join Network Game"**
2. Enter your player name (e.g., "Bob")
3. Server host: **localhost**
4. Port: **8888**
5. Click **"Start"**
6. 🎮 **Game browser shows all available games!**
7. Click on "Alice's Game" to join
8. **Chat** with other players (press Enter to type)
9. Click **"Ready"** when ready
10. Host clicks **"Start Game"** when all players are ready

#### In-Game Features:
- **Chat**: Press **Enter** to open chat, type message, press **Enter** to send
- **Victory Screen**: Automatically appears when game ends with statistics
- **Reconnection**: Automatic reconnection if connection drops (3 attempts with backoff)

### 2B. Connect AI Players (Command Line)

```bash
# AI creates a new game and waits for others
uv run race-ai-client --create "My Game" --name "Alice_AI"

# Another AI joins the game
uv run race-ai-client --join <game-id> --name "Bob_AI"

# AI with aggressive strategy
uv run race-ai-client --create "Battle" --strategy aggressive

# AI with defensive strategy
uv run race-ai-client --join <game-id> --strategy defensive
```

**AI Strategies**:
- `random`: Random action selection (default)
- `aggressive`: Prioritizes attacks and forward movement
- `defensive`: Prioritizes deployment and safe moves

### 3. Complete Multiplayer Setup Example

**Scenario: Human host, AI and human players**

```bash
# Terminal 1: Start the server
uv run race-server

# Terminal 2: Human hosts game via GUI
uv run race-to-the-crystal
# Click "Host Network Game"
# Enter name: "Alice", port: 8888, game: "Mixed Game"
# Click "Create Game"
# Wait in lobby...

# Terminal 3: AI player joins (get game-id from server logs)
uv run race-ai-client --join abc123... --name "Bob_AI" --strategy aggressive

# Terminal 4: Another AI joins
uv run race-ai-client --join abc123... --name "Carol_AI"

# Back in Terminal 2 (GUI):
# See Bob_AI and Carol_AI in the lobby
# Chat: "Hi everyone!"
# Click "Ready" when ready
# Wait for all players to ready
# Click "Start Game" (as host)
# Game begins!
```

### 4. Game Flow

1. **Lobby Phase**: Players join, chat, and ready up
2. **Game Phase**: Turn-based gameplay with server validation
3. **Victory Phase**: Winner announced with statistics screen
4. **Return to Menu**: Ready for another game!

## Network Protocol

### Message Format

All messages follow this JSON structure:

```json
{
  "type": "MESSAGE_TYPE",
  "timestamp": 1234567890.123,
  "player_id": "uuid-string",
  "data": {
    // Message-specific data
  }
}
```

### Message Types

#### Connection (8 types)
- `CONNECT`: Initial connection request
- `CONNECT_ACK`: Server assigns player_id
- `RECONNECT`: **[Phase 4]** Reconnect with existing player_id
- `RECONNECT_ACK`: **[Phase 4]** Reconnection successful
- `RECONNECT_FAILED`: **[Phase 4]** Reconnection failed (timeout/invalid)
- `DISCONNECT`: Graceful disconnect
- `HEARTBEAT`: Keep-alive ping
- `HEARTBEAT_ACK`: Keep-alive response

#### Lobby (9 types)
- `CREATE_GAME`: Create new game lobby
- `JOIN_GAME`: Join existing lobby
- `LEAVE_GAME`: Leave lobby
- `LIST_GAMES`: Request available games
- `GAME_LIST`: Response with game list
- `PLAYER_JOINED`: Broadcast when player joins
- `PLAYER_LEFT`: Broadcast when player leaves
- `READY`: Set ready status
- `START_GAME`: Host starts the game

#### Game Actions (4 types)
- `MOVE`: Move a token
- `ATTACK`: Attack enemy token
- `DEPLOY`: Deploy token from reserve
- `END_TURN`: End current turn

#### State Synchronization (3 types)
- `FULL_STATE`: Complete game state
- `STATE_UPDATE`: Delta update (future optimization)
- `TURN_CHANGE`: Turn changed notification

#### Events (9 types)
- `COMBAT_RESULT`: Combat outcome
- `TOKEN_MOVED`: Token moved event
- `TOKEN_DEPLOYED`: Token deployed event
- `MYSTERY_EVENT`: Mystery square triggered
- `GENERATOR_UPDATE`: Generator capture status changed
- `CRYSTAL_UPDATE`: Crystal capture progress changed
- `GAME_WON`: Game ended with winner
- `ERROR`: Server error
- `INVALID_ACTION`: Action validation failed

#### Communication (1 type)
- `CHAT`: **[Phase 4]** Chat message from player

**Total: 34 message types**

### TCP Framing

Messages are length-prefixed for TCP stream handling:

```
[4 bytes: length (big-endian)] [N bytes: JSON message]
```

This prevents message fragmentation issues over TCP streams.

## Components

### Server Components

#### `server/game_server.py` - Main TCP Server
- Accepts TCP connections from clients
- Routes messages to appropriate handlers
- Manages ConnectionPool for all active connections
- Coordinates between LobbyManager and GameCoordinator

**Key Methods**:
- `start()`: Start TCP server
- `_handle_new_connection()`: Accept new client
- `_handle_message()`: Route incoming messages
- `_broadcast_to_lobby()`: Send to all lobby players
- `_broadcast_to_game()`: Send to all game players

#### `server/lobby.py` - Lobby Management
- `LobbyManager`: Manages all game lobbies
- `GameLobby`: Represents a pre-game lobby
- `PlayerInfo`: Player metadata (name, client type, ready status)

**Lobby Lifecycle**:
1. WAITING - Accepting players
2. READY - All players ready, can start
3. STARTING - Game being created
4. IN_PROGRESS - Game active
5. FINISHED - Game ended

#### `server/game_coordinator.py` - Game Session Management
- `GameCoordinator`: Manages multiple active games
- `GameSession`: Wraps GameState for one game

**Key Features**:
- Maps network player UUIDs to game player_0, player_1, etc.
- Uses `AIActionExecutor` to validate/execute actions
- Provides game state from each player's perspective
- Tracks which player is in which game

### Client Components

#### `client/network_client.py` - Base Network Client
- Handles TCP connection to server
- Sends/receives messages with proper framing
- Provides async message loop
- Exposes lobby and game action methods

**Usage**:
```python
client = NetworkClient("PlayerName", ClientType.HUMAN)
await client.connect("localhost", 8888)
await client.create_game("My Game")
await client.set_ready(True)

# Send action
action = MoveAction(token_id=5, destination=(10, 12))
await client.send_action(action)
```

#### `client/ai_client.py` - Autonomous AI Player
- Extends NetworkClient for autonomous play
- Uses `AIObserver` to understand game state
- Makes decisions based on strategy
- Automatically takes turns when it's their turn

**AI Decision Making**:
1. Receive `FULL_STATE` from server
2. Deserialize to `GameState` object
3. Use `AIObserver.list_available_actions()` to get valid actions
4. Choose action based on strategy
5. Send action to server via `send_action()`

### Network Layer

#### `network/protocol.py` - Message Protocol
- `NetworkMessage`: Message data structure
- `ProtocolHandler`: Create and parse messages
- `MessageFraming`: Length-prefix framing for TCP

**Action Conversion**:
```python
# AI Action -> Network Message
handler = ProtocolHandler()
action = MoveAction(token_id=5, destination=(10, 12))
message = handler.action_to_message(action, player_id)

# Network Message -> AI Action
action = handler.message_to_action(message)
```

#### `network/connection.py` - Connection Wrapper
- `Connection`: Wraps asyncio StreamReader/StreamWriter
- `ConnectionPool`: Manages multiple connections
- Handles message framing automatically
- Provides async send/receive

## AI Integration

### How AI Players Work

The network infrastructure seamlessly integrates with the existing AI system:

1. **Game State Observation**: Server sends `FULL_STATE` messages containing serialized `GameState`
2. **Action Planning**: AI uses `AIObserver.list_available_actions()` to see valid moves
3. **Action Execution**: AI creates `AIAction` objects (MoveAction, AttackAction, etc.)
4. **Network Transmission**: `ProtocolHandler.action_to_message()` converts to network message
5. **Server Validation**: Server uses `AIActionExecutor.execute_action()` to validate
6. **State Update**: Server broadcasts updated state to all players

### Creating Custom AI Strategies

Extend `AIPlayer` and override `_choose_action()`:

```python
class CustomAI(AIPlayer):
    def _choose_action(self, actions, game_state, player_id):
        # Your custom strategy here
        # 1. Analyze game_state
        # 2. Evaluate available actions
        # 3. Return chosen AIAction

        # Example: Always attack if possible
        attacks = [a for a in actions if a["type"] == "ATTACK"]
        if attacks:
            return self._action_dict_to_ai_action(attacks[0])

        return self._choose_random_action(actions)
```

## State Synchronization

### Full State Sync

The server sends complete game state to clients:

```json
{
  "type": "FULL_STATE",
  "timestamp": 1234567890.0,
  "player_id": "uuid",
  "data": {
    "game_state": {
      "board": {...},
      "players": {...},
      "tokens": {...},
      "generators": [...],
      "crystal": {...},
      "current_turn_player_id": "player_0",
      "turn_number": 5,
      "phase": "PLAYING",
      "turn_phase": "MOVEMENT"
    },
    "perspective_player_id": "player_0",
    "your_player_id": "player_0"
  }
}
```

**Client-Side Interpolation**:
To ensure smooth gameplay, the client implements state interpolation:
1. `NetworkGameView` receives the new state but does not immediately hard-reset the view.
2. It calls `sync_tokens()` on the renderer.
3. The renderer identifies existing tokens and updates their `target_position` instead of their immediate position.
4. The render loop smoothly animates tokens to their new targets over time.

**When State is Sent**:
- On game start
- After any action execution
- After turn changes
- On reconnect (future feature)

### Player ID Mapping

The server maintains bidirectional mapping:

```
Network ID (UUID)           Game ID
"550e8400-e29b-..."    <->  "player_0"
"6ba7b810-9dad-..."    <->  "player_1"
"6ba7b814-9dad-..."    <->  "player_2"
```

This allows:
- Network layer to use persistent UUIDs
- Game logic to use simple player_0, player_1, etc.
- Clean separation of concerns

## Testing

### Unit Tests

```bash
# Test network protocol
pytest tests/test_network_protocol.py -v

# Test message framing
pytest tests/test_network_protocol.py::TestMessageFraming -v

# Test action conversion
pytest tests/test_network_protocol.py::TestProtocolHandler::test_action_roundtrip -v
```

### Integration Testing

Test with multiple AI clients:

```bash
# Terminal 1: Start server
uv run race-server --debug

# Terminal 2: Create game with AI
uv run race-ai-client --create "Test Game" --debug

# Terminal 3: Join with another AI
uv run race-ai-client --join <game-id> --strategy aggressive --debug

# Terminal 4: Join with third AI
uv run race-ai-client --join <game-id> --strategy defensive --debug
```

Watch the server logs to see:
- Player connections
- Lobby join events
- Game start
- Turn-by-turn action execution
- Game completion

## Future Enhancements

### Planned Features

1. **Reconnection Support**
   - Save game state on disconnect
   - Allow players to rejoin active games
   - Resume from saved state

2. **Optimized State Sync**
   - Delta updates instead of full state
   - Only send changed data
   - Reduce bandwidth usage

3. **Heartbeat System**
   - Detect dead connections
   - Auto-forfeit on timeout
   - Connection quality monitoring

4. **Human Client Integration**
   - Update Arcade client to use NetworkClient
   - Network multiplayer with GUI
   - Spectator mode for observers

5. **Advanced Features**
   - In-game chat
   - Turn timer with auto-forfeit
   - Match history and statistics
   - ELO rating system

### Security Considerations

Current implementation is suitable for trusted environments (LAN, friends).

For production deployment, add:
- Authentication (login/password or tokens)
- Encryption (TLS/SSL)
- Rate limiting (prevent spam)
- Input validation (additional server-side checks)
- Anti-cheat measures (server-authoritative already helps)

## Troubleshooting

### Connection Issues

**Problem**: AI can't connect to server
```
Solution: Ensure server is running and check host/port
$ uv run race-server --host 0.0.0.0 --port 8888
```

**Problem**: "Connection refused"
```
Solution: Check firewall allows port 8888
$ sudo ufw allow 8888/tcp  # Linux
```

### Game Issues

**Problem**: AI clients connect but game won't start
```
Solution: Ensure all players are ready
- Host must start game
- Minimum 2 players required
```

**Problem**: Invalid action errors
```
Solution: Check server logs for validation errors
$ uv run race-server --debug
```

**Problem**: Game state out of sync
```
Solution: Server is authoritative - client bug
- Check client message handling
- Ensure FULL_STATE is properly deserialized
```

## API Reference

### NetworkClient Methods

- `connect(host, port) -> bool`: Connect to server
- `disconnect()`: Disconnect from server
- `create_game(name, max_players) -> bool`: Create lobby
- `join_game(game_id) -> bool`: Join existing lobby
- `leave_game() -> bool`: Leave current lobby
- `set_ready(is_ready) -> bool`: Set ready status
- `list_games() -> bool`: Request available games
- `send_action(action) -> bool`: Send game action

### AIPlayer Methods

Inherits all NetworkClient methods, plus:
- `_take_turn()`: Execute AI turn
- `_choose_action(actions, game_state, player_id)`: Choose action
- `_choose_random_action(actions)`: Random strategy
- `_choose_aggressive_action(actions)`: Aggressive strategy
- `_choose_defensive_action(actions)`: Defensive strategy

### ProtocolHandler Methods

- `create_connect_message(name, client_type)`: CONNECT message
- `create_game_message(player_id, name, max_players)`: CREATE_GAME
- `action_to_message(action, player_id)`: Convert action to message
- `message_to_action(message)`: Convert message to action
- `create_full_state_message(state_dict, player_id)`: State sync

### GameCoordinator Methods

- `create_game(lobby) -> GameSession`: Create from lobby
- `get_game(game_id) -> GameSession`: Get active game
- `get_player_game(player_id) -> GameSession`: Find player's game
- `execute_action(player_id, action)`: Execute and validate action
- `end_game(game_id)`: End game and cleanup

## Performance

### Benchmarks

- **Server Capacity**: Tested with 4 concurrent games (16 AI players)
- **Message Latency**: <10ms on localhost
- **Turn Processing**: <50ms for action validation and state broadcast
- **Memory Usage**: ~50MB per active game session

### Optimization Tips

1. **Server**: Use one server instance for multiple games
2. **Clients**: Reuse connections, don't reconnect every action
3. **State**: Server already optimized with dict lookups (O(1))
4. **Network**: Use localhost for testing, LAN for low-latency play

## Examples

### Complete AI Client Example

```python
import asyncio
from client.ai_client import AIPlayer

async def main():
    # Create AI player
    ai = AIPlayer("MyBot", strategy="aggressive")

    # Connect to server
    await ai.connect("localhost", 8888)

    # Create and host a game
    await ai.create_game("MyGame")
    await ai.set_ready(True)

    # AI will automatically play when game starts
    # Keep running until disconnected
    while ai.is_connected():
        await asyncio.sleep(1)

asyncio.run(main())
```

### Custom Message Handler

```python
from client.network_client import NetworkClient
from network.messages import MessageType, ClientType

async def handle_message(message):
    if message.type == MessageType.GAME_WON:
        winner = message.data.get("winner_name")
        print(f"Game over! {winner} won!")

client = NetworkClient("Player", ClientType.HUMAN)
client.on_message = handle_message

await client.connect("localhost", 8888)
```

## Support

For issues or questions:
- Check server logs with `--debug` flag
- Review this documentation
- Check test files for usage examples
- Examine source code comments
