# Race to the Crystal - Network Architecture

This document describes the multiplayer network architecture for Race to the
Crystal: how the processes fit together, how clients talk to the server, and
how state is synchronized.

> For the game rules see [GAME.md](GAME.md). For repository conventions see
> [../AGENTS.md](../AGENTS.md).

## Overview

Race to the Crystal uses a **server-authoritative client-server** architecture:

- **Server**: maintains the single source of truth for game state
- **Clients**: send action requests and receive state updates
- **Validation**: every action is validated on the server before execution
- **State sync**: the server sends per-player full state, plus a sequenced
  event stream for feedback. No client-side prediction is needed.

This prevents cheating, keeps all players consistent, and works well for
turn-based gameplay.

### Stack

- **Transport**: HTTP/1.1 and WebSocket (Kukicha `stdlib/http` + gorilla/websocket, Go underneath)
- **Protocol**: JSON messages over WebSocket; JSON over REST for agents
- **Auth**: JWT bearer tokens for the HTTP API (created/join/spectate); the
  WebSocket lobby flow identifies clients per connection
- **Clients**: web browser (Babylon.js 3D), AI client (HTTP), desktop client
  (local-only, in-process — no network), MCP proxy (agents)

## Processes and Ports

| Process | Port | Role |
|---|---|---|
| `race-server` (`make server-run`) | 8080 | Game server: HTTP REST API + WebSocket |
| web server (`make web-server-run`) | 8000 | Serves the Babylon.js client; reverse-proxies `/api` and `/ws` to the game server |

There is **no TCP listener** and no length-prefixed framing. The browser
connects to `ws://<host>:<web-port>/ws`, which the web server proxies to the
game server; the game server therefore sees the browser's `Origin` header,
not the proxy's.

## Quick Start

```bash
# Terminal 1 — game server (HTTP + WebSocket, port 8080)
make server-run

# Terminal 2 — web client host (port 8000)
make web-server-run
```

Open **http://localhost:8000**, enter a name, create a game, and share the
game ID for others to join.

### AI players

The AI client (`client/ai/`) is a Kukicha program that speaks the same HTTP
API as the browser. It polls the state on a timer and acts when it is its
turn:

```bash
make ai-client  # builds ./race-ai-client
./race-ai-client poll --create "My Game" --name "Alice_AI" --strategy aggressive
./race-ai-client poll --join <game-id> --name "Bob_AI" --strategy defensive
```

Strategies: `random` (default), `aggressive`, `defensive`. Pass `--server`
to point at a remote server.

An AI player and web players can share a match. HTTP seats are labelled
`HTTP_AI` automatically and get the longer agent turn timeout
(`AGENT_TURN_TIMEOUT_SECONDS`, default 120) instead of the human one
(`TURN_TIMEOUT_SECONDS`, default 60). A watchdog passes the turn on when the
timer runs out, so a stalled player cannot block the match.

### Agents over MCP

LLM agents can play a seat through the thin stdio MCP proxy in `mcp/`, which
forwards to the game server's REST API. See the "Agent / MCP client" section
of the README.

## Topology

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Web browser  │   │  AI client   │   │  MCP proxy   │
│ (Babylon.js) │   │ (HTTP poll)  │   │ (agent seat) │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       │ ws://…/ws        │ HTTP REST        │ HTTP REST
       ▼                  ▼                  ▼
┌───────────────────────────────────────────────────┐
│  Web server (port 8000)                           │
│  - serves static client files                      │
│  - reverse-proxies /api and /ws → game server      │
└──────────────────────┬────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────┐
│  Game server (port 8080)                          │
│  - HTTP REST API (JWT auth)                       │
│  - WebSocket endpoint (state + event stream)      │
│  - GameCoordinator / GameSession per game         │
└───────────────────────────────────────────────────┘
```

The desktop client (`make desktop-run`) is separate: it runs the game
in-process against the `game` package and has no network path.

## REST API (game server, port 8080)

| Route | Method | Purpose |
|---|---|---|
| `/api/games` | GET | list waiting/in-progress games |
| `/api/game/create` | POST | create a game (HTTP seats are labelled `HTTP_AI`) |
| `/api/game/{id}/join` | POST | join a waiting game (returns a JWT) |
| `/api/game/{id}/spectate` | POST | spectator token — see seat-cam note below |
| `/api/game/{id}/ready` | POST | toggle ready |
| `/api/game/{id}/start` | POST | start the game |
| `/api/game/{id}/state` | GET | per-player (or spectator) state |
| `/api/game/{id}/actions` | GET | legal actions for the seat |
| `/api/game/{id}/action` | POST | submit one action |
| `/api/game/{id}/say` | POST | radio chatter (broadcast as a `RadioChatter` event) |
| `/api/game/{id}/leave` | POST | leave a game |

Authenticated endpoints expect `Authorization: Bearer <jwt>` from the
create/join/spectate response.

### Spectating (seat-cam)

Spectating is open to anyone, but the spectator never sees through fog of
war. A spectator follows exactly one seat — chosen with the optional
`follow` field (`player_0`, `player_1`, ...) in the spectate request, or a
random seat if omitted. Every state frame, resync and event the spectator
receives is fog-filtered from that seat's point of view, so a spectator
sees precisely what that player can see, nothing more. The follow binding
is fixed for the spectate session; `SPECTATE_ACK` reports back
`{ "follow": "player_0", "follow_name": "..." }`. The web client shows a
"SPECTATING — following &lt;name&gt;" banner while spectating.

### Honest limits of spectator fog

Spectator fog is a politeness, **not** an integrity boundary. A spectator
follows exactly one seat per connection, but nothing stops a viewer from
opening one connection per seat and reconstructing the union of every
player's information — near-complete map knowledge. This includes a
seated player spectating the game they are playing, and includes AI
clients (the HTTP AI players and the MCP agent can do it trivially).
Per-connection spectators are anonymous — the server cannot distinguish a
seated player from a stranger — so this cannot be closed without an
identity system. It is accepted deliberately for casual play. If you need
spectating without the union leak, don't allow it live: watch the match
after it ends via the battle log, or gate spectate behind an invite. Do
not treat the seat binding as protection against a determined adversary.

## WebSocket Protocol

Connect to `/ws`, then send a `CONNECT` message:

```json
{"type": "CONNECT", "player_name": "Alice", "client_type": "WEB_BROWSER"}
```

The server responds with `CONNECT_ACK` and a connection-scoped `player_id`.

### Client → Server

| Type | Purpose |
|---|---|
| `CONNECT` | identify yourself (see above) |
| `LIST_GAMES` | request the open lobby list |
| `CREATE_GAME` | create a lobby (`game_name`, `max_players`) |
| `JOIN_GAME` | join a lobby (`game_id`) |
| `LEAVE_GAME` | leave a lobby |
| `READY` | toggle ready status |
| `START_GAME` | host starts the game |
| `MOVE` / `ATTACK` / `DEPLOY` / `END_TURN` | game actions |
| `RESYNC_STATE` | ask the server to resend the current state |
| `SPECTATE` | spectate a game (optional `follow`: seat id, e.g. `player_0`) |
| `DISCONNECT` | leave gracefully |

### Server → Client

| Type | Purpose |
|---|---|
| `CONNECT_ACK` | connection id + server version |
| `GAME_LIST` | list of open lobbies |
| `CREATE_GAME` / `JOIN_GAME` / `LEAVE_GAME` | lobby acknowledgements |
| `PLAYER_JOINED` / `PLAYER_LEFT` / `PLAYER_DISCONNECTED` | lobby roster updates |
| `READY` | ready status changed |
| `START_GAME` | game is starting |
| `FULL_STATE` | complete per-player state (carries `event_seq`) |
| `EVENT` | one game event (sound/animation/camera feedback) |
| `SPECTATE_ACK` | spectator bound to a seat (`follow`, `follow_name`) |
| `GAME_WON` | the match is over; names the winner |
| `INVALID_ACTION` | action validation failed |
| `ERROR` | server-side error |

### State synchronization

- The server sends **full state**, not deltas. `FULL_STATE` is per-player:
  it carries only what that player can see (fog of war).
- Every frame carries an event sequence number. `EVENT` frames include
  `{type: "EVENT", game_id, seq, event}` and `FULL_STATE` carries
  `event_seq`. The counter is per player.
- If the client detects a gap in the event stream it sends `RESYNC_STATE`;
  the reply includes the server's current `event_seq`, which repairs the
  counter.
- The web client interpolates token positions locally so movement animates
  smoothly between state frames.

### Fog of war

A player sees the terrain, their own tokens, and enemy tokens within
`VISIBILITY_RADIUS` (3 cells, Chebyshev) of one of their own tokens. Masked
enemy tokens have `position: null` and are omitted from the cell occupant
lists. Every message that leaves the server goes through the same per-player
filter (`game/visible_state.kuki`).

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `HTTP_PORT` | `8080` | Game server HTTP + WebSocket port |
| `JWT_SECRET_KEY` | random per boot | Token signing key |
| `TURN_TIMEOUT_SECONDS` | `60` | Seconds a human has to move |
| `AGENT_TURN_TIMEOUT_SECONDS` | `120` | Seconds an AI player has to move |
| `WS_ALLOWED_ORIGINS` | *(any)* | Comma-separated origins allowed to open a WebSocket |
| `WEB_PORT` | `8000` | Port the web client is served on |
| `GAME_SERVER_URL` | `http://localhost:8080` | Where the web server proxies to |
| `DEBUG` | `false` | Verbose logging |

## Troubleshooting

**Nobody can connect to the web client.** Check that both processes are
running (`make server-run` and `make web-server-run`) and that ports 8080
and 8000 are free.

**AI connects but never moves.** HTTP seats only get state via polling;
check that `race-ai-client poll` is running and that the strategy flag is
valid (`random|aggressive|defensive`).

**WebSocket rejected at the proxy.** Set `WS_ALLOWED_ORIGINS` on the game
server to include the web origin exactly (scheme + host + port).

**Turn passes by itself.** The 60/120-second turn timer expired; the watchdog
passed the turn on. Act faster or raise `TURN_TIMEOUT_SECONDS`.

## Where the code lives

- `server/ws_endpoint.kuki` — WebSocket message routing
- `server/http_handler.kuki` — REST API
- `server/websocket_handler.kuki` — client registry + event/state broadcast
- `server/game_coordinator.kuki` — game sessions, turn timers, spectator handling
- `web_server/static/network_manager.js` — web client networking
- `game/visible_state.kuki` — fog-of-war filtering for state and events
