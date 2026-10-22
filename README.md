![Race to the Crystal Logo](logo.png)

# Race to the Crystal

A networked multiplayer strategy game for 2-4 players with Tron/Battlezone-style vector graphics. Play in your browser (3D web client) or locally on the desktop (2D).

> **AI Disclosure**: This project was created with AI assistance for both code and assets.

## About

Race to the Crystal is a turn-based strategy game where players compete to capture a central crystal by deploying tokens across a 24x24 grid. Features:

- **Web Client**: Browser-based 3D view (JavaScript + Babylon.js) — the networked client
- **Desktop Client**: 2D top-down view (Kukicha + Ebitengine) — local play only
- **Network Multiplayer**: Web clients and AI clients play together on the same server
- **AI Players**: Multiple strategy modes (random, aggressive, defensive)
- **Strategic Gameplay**: Generators, mystery squares, combat, and token deployment
- **GPU-Accelerated Graphics**: Tron-style wireframes with glow effects

## Tech Stack

- **Backend**: Kukicha (compiles to Go) — HTTP/WebSocket + REST API with JWT authentication, built on `stdlib/http`
- **Desktop Client**: Kukicha + Ebitengine (2D top-down)
- **Web Client**: Babylon.js 8. The WebSocket carries the full game state and a sequenced event stream; Mercure (SSE) support exists but is **not enabled by default** (see [docs/WEB.md](docs/WEB.md))
- **Testing**: 94 Kukicha unit tests covering core game logic and the server's action validation

## Quick Start

The web client and the game server are two processes: the web server serves the
page and proxies the game API to the game server.

```bash
# Terminal 1 — the game server (HTTP + WebSocket, port 8080)
make server-run

# Terminal 2 — the web client (port 8000)
make web-server-run
```

Then open **http://localhost:8000** in your browser, enter a name and connect.

To play locally on the desktop instead:

```bash
make desktop-run
```

## Game Modes

### 1. Local Single-Player (Desktop)

```bash
make desktop-run
```

The desktop client runs the game in-process against the `game` package — no
server involved. Its "Network Game" menu entry is a stub, so it cannot join a
networked match.

### 2. Network Multiplayer (Web)

Start the game server and the web server (see [Quick Start](#quick-start)),
then open http://localhost:8000. Create a game, and have the other player join
by game ID or from the lobby browser.

### 3. AI Players

The AI client is a Kukicha program (`client/ai/`) that speaks the same HTTP
API as the browser. It has two subcommands: `poll` (asks the server for the
state on a timer) and `sse`.

```bash
make ai-client        # builds ./race-ai-client
./race-ai-client poll --create "My Game" --name "Bot" --strategy aggressive
./race-ai-client poll --join <game-id> --strategy defensive
./race-ai-client --help
```

The strategy is one of `random`, `aggressive` or `defensive`. The server URL
defaults to `http://localhost:8080`; pass `--server` to point it elsewhere.

An AI player and a web player can share a match.

## Controls

**Web Client:**

- **Left-click**: Select a token, then click again to move or attack
- **Drag (left or right button)**: Pan the camera
- **Mouse wheel**: Zoom in/out
- **Space / Enter**: End turn
- **R**: Open the deploy menu
- **ESC**: Cancel the current action
- **V**: Toggle overview / first-person view
- **WASD / Arrow keys**: Move your token in first-person, pan the camera in overview
- **TAB**: Cycle through your tokens (first-person)
- **M**: Toggle music and sound
- **Ctrl+Q**: Quit

The in-game **Controls** panel lists the full set, and the mobile action bar
provides the same actions as buttons.

## Game Rules

1. **Win Condition**: Hold the crystal with 12 tokens for 3 consecutive turns
2. **Movement**: Tokens move 1-2 spaces based on current health
3. **Combat**: Attack adjacent enemies (damage = attacker HP ÷ 2)
4. **Generators**: Capture with 2 tokens for 2 turns to reduce crystal requirement
5. **Mystery Squares**: Random heal or teleport events
6. **Turn Timer**: You have 30 seconds to complete your turn. The HUD counts
   down, and if the timer runs out your turn is passed on automatically. AI
   players get 120 seconds, since a model may need a while to think.

**See [docs/GAME.md](docs/GAME.md) for complete rules and mechanics.**

## Configuration

The game server and web server are configured through environment variables:

| Variable | Default | Used by | Meaning |
|---|---|---|---|
| `HTTP_PORT` | `8080` | game server | HTTP + WebSocket port |
| `JWT_SECRET_KEY` | random per boot | game server | Token signing key |
| `TURN_TIMEOUT_SECONDS` | `30` | game server | Seconds a human has to move |
| `AGENT_TURN_TIMEOUT_SECONDS` | `120` | game server | Seconds an AI player has to move |
| `WS_ALLOWED_ORIGINS` | *(any)* | game server | Comma-separated origins allowed to open a WebSocket |
| `WEB_PORT` | `8000` | web server | Port the web client is served on |
| `GAME_SERVER_URL` | `http://localhost:8080` | web server | Where the game server lives |
| `DEBUG` | `false` | game server | Verbose logging |

## Development

### Project Structure

```
race-to-the-crystal/
├── game/          # Core game logic + *_test.kuki unit tests (no rendering deps)
│   └── game_events.kuki  # The game event vocabulary (see below)
├── learn/         # Learn-to-program package: LearnerAPI + in-process simulation
│   └── examples/  # Runnable learner scripts (01-hello … 10-strategy-ladder)
├── client/        # Desktop client (Kukicha + Ebitengine) and the AI client
├── server/        # Game server (HTTP/WebSocket + REST, JWT auth)
├── web_server/    # Web client host (Babylon.js frontend + reverse proxy)
├── shared/        # Constants, enums, types and error codes
├── deployment/    # Container deployment configs
└── docs/          # Detailed documentation
    └── tutorials/ # Learn to Program with Kukicha course (10 chapters)
```

### The game event stream

The server broadcasts a sequenced stream of game **events** alongside the full
state:

```json
{"type":"EVENT","game_id":"abc","seq":42,
 "event":{"type":"COMBAT_RESOLVED","attacker_id":5,"defender_id":9,
          "attacker_position":[3,4],"defender_position":[5,6],
          "damage":5,"defender_killed":true}}
```

Events are what drive feedback — sound, particles, camera moves — and they
carry the positions they refer to, so a client never has to look information
up in the current state. The same vocabulary is used for the live stream and
for battle replays.

### Learn to program

Write Kukicha programs that play the game, no server needed — modeled on
*Learn to Program with Minecraft*. See `docs/tutorials/` for the course
and `learn/examples/` for runnable scripts:

```bash
make learn-run NAME=01-hello   # run a learner example
make learn-check               # type-check the learn package + all examples
make learn-test                # run the learn package tests
```

### Testing

```bash
make test              # Transpile the test sources, then run `go test ./...`
make test-verbose      # Same, with verbose output
make lint              # Check Kukicha formatting (kukicha fmt --check)
```

`make test` runs `kukicha brew` first, which is what turns `*_test.kuki` into
the `*_test.go` files `go test` compiles. Running `go test ./...` on its own
uses whatever was transpiled last, so use `make test` after editing a test.

### Deployment

Deploy to production using containerized deployment:

```bash
# See complete deployment guide
cat deployment/docs/DEPLOYMENT.md

# Quick: Development deployment (localhost)
cd deployment/dockerfiles
podman build -f Dockerfile -t localhost/race-to-the-crystal:latest ../..
podman build -f Dockerfile.caddy -t localhost/race-caddy:latest ../..
# Deploy quadlets from deployment/development/
```

### Documentation

**Game & Development:**
- **[docs/GAME.md](docs/GAME.md)** - Complete game rules and mechanics
- **[docs/3D.md](docs/3D.md)** - Desktop 3D mode camera system and controls
- **[docs/WEB.md](docs/WEB.md)** - Web client architecture and API
- **[AGENTS.md](AGENTS.md)** - Repository guide for agents and contributors

> **Note**: `docs/NETWORK.md` and the `deployment/` guides predate the
> Go/Kukicha rewrite and still describe the earlier Python implementation
> (a TCP server on port 8888 with length-prefixed framing). They are being
> updated; for the current protocol, see [AGENTS.md](AGENTS.md) and
> `server/ws_endpoint.kuki`.

**Deployment:**
- **[deployment/docs/DEPLOYMENT.md](deployment/docs/DEPLOYMENT.md)** - Container deployment guide
- **[deployment/docs/MERCURE.md](deployment/docs/MERCURE.md)** - Mercure SSE configuration

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE.md) file for details.
