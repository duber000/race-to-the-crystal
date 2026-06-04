![Race to the Crystal Logo](logo.png)

# Race to the Crystal

A networked multiplayer strategy game for 2-4 players with Tron/Battlezone-style vector graphics. Play on desktop (2D) or in your browser (3D web client).

> **AI Disclosure**: This project was created with AI assistance for both code and assets.

## About

Race to the Crystal is a turn-based strategy game where players compete to capture a central crystal by deploying tokens across a 24x24 grid. Features:

- **Desktop Client**: 2D top-down view (Kukicha + Ebitengine)
- **Web Client**: Browser-based 3D view (JavaScript + Babylon.js)
- **Network Multiplayer**: Desktop and web clients play together on the same server
- **AI Players**: Multiple strategy modes (random, aggressive, defensive)
- **Strategic Gameplay**: Generators, mystery squares, combat, and token deployment
- **GPU-Accelerated Graphics**: Tron-style wireframes with glow effects

## Tech Stack

- **Backend**: Kukicha (compiles to Go) — HTTP/WebSocket + REST API with JWT authentication, built on `stdlib/http`
- **Desktop Client**: Kukicha + Ebitengine (2D top-down)
- **Web Client**: Babylon.js 8 with Mercure (SSE) state synchronization, WebSocket fallback
- **Testing**: 61 Kukicha unit tests covering core game logic (`game/*_test.kuki`)

## Quick Start

```bash
# Build all Kukicha packages (requires the kukicha compiler + Go toolchain)
make build

# Play local single-player (desktop)
make desktop-run

# Play multiplayer (desktop + web clients)
make web-server-run        # TODO: confirm this is the unified-server entry point
# Then open http://localhost:8080 in your browser
# Or connect desktop clients via the game menu
```

## Game Modes

### 1. Local Single-Player (Desktop)
```bash
make desktop-run
# Toggle between 2D/3D views with 'V' key
```

### 2. Network Multiplayer (Desktop + Web)

**Start the unified server:**
```bash
make web-server-run        # TODO: confirm unified-server entry point
# Serves the HTTP/WebSocket API + web client (default port 8080)
```

**Option A: Desktop Client**
```bash
make desktop-run
# Click "Host Network Game" or "Join Network Game"
```

**Option B: Web Browser**
- Open http://localhost:8080 in your browser
- Play with 3D Babylon.js renderer

**Option C: AI Players**

The AI clients are now Kukicha (`client/ai_client.kuki` for HTTP poll/SSE, `client/http_ai_client.kuki`
a simpler HTTP/SSE variant), each with its own `func main`. No Makefile target wires them up yet.

```bash
# TODO: confirm invocation — likely one of:
#   kukicha run client/ai_client.kuki -- --create "My Game" --name "Bot"
#   kukicha run client/ai_client.kuki -- --join <game-id> --strategy aggressive
#   kukicha run client/http_ai_client.kuki -- --join <game-id> --strategy defensive
# (or build a binary first, then invoke it directly)
```

All client types (desktop, web, AI) can play together in the same game!

**See [docs/NETWORK.md](docs/NETWORK.md) for detailed multiplayer setup.**

## Controls

**Desktop Client:**
- **Mouse Click**: Select tokens, move, attack, deploy
- **Arrow Keys/WASD**: Pan camera
- **V**: Toggle 2D/3D view
- **TAB**: Cycle through tokens (3D first-person mode)
- **Space/Enter**: End turn
- **M**: Toggle music

**Web Client:**
- **Mouse**: Click to interact, drag to rotate camera, scroll to zoom
- **Space**: End turn

**See [docs/3D.md](docs/3D.md) for complete desktop 3D controls.**

## Game Rules

1. **Win Condition**: Hold the crystal with 12 tokens for 3 consecutive turns
2. **Movement**: Tokens move 1-2 spaces based on current health
3. **Combat**: Attack adjacent enemies (damage = attacker HP ÷ 2)
4. **Generators**: Capture with 2 tokens for 2 turns to reduce crystal requirement
5. **Mystery Squares**: Random heal or teleport events

**See [docs/GAME.md](docs/GAME.md) for complete rules and mechanics.**

## Development

### Project Structure

```
race-to-the-crystal/
├── game/          # Core game logic + *_test.kuki unit tests (no rendering deps)
├── client/        # Desktop client (Kukicha + Ebitengine) and AI clients
├── server/        # Game server (HTTP/WebSocket + REST, JWT auth)
├── web_server/    # Web client host (Babylon.js frontend + Mercure config)
├── network/       # Protocol and connection handling
├── shared/        # Constants and enums
├── deployment/    # Container deployment configs
│   ├── docs/      # Deployment guides
│   ├── dockerfiles/ # Container images
│   ├── development/ # Dev quadlets
│   └── production/  # Production quadlets
├── tests/         # Legacy pytest suite (being ported to *_test.kuki)
└── docs/          # Detailed documentation
```

### Testing

```bash
make test              # Build all Kukicha, then run `go test ./...`
make test-verbose      # Same, with verbose output
make lint              # Check Kukicha formatting (kukicha fmt --check)
```

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

**[deployment/docs/DEPLOYMENT.md](deployment/docs/DEPLOYMENT.md)** - Complete deployment guide

### Documentation

**Game & Development:**
- **[docs/GAME.md](docs/GAME.md)** - Complete game rules and mechanics
- **[docs/NETWORK.md](docs/NETWORK.md)** - Network multiplayer setup and protocol
- **[docs/3D.md](docs/3D.md)** - Desktop 3D mode camera system and controls
- **[docs/WEB.md](docs/WEB.md)** - Web client architecture and API
- **[CLAUDE.md](CLAUDE.md)** - Development guide for contributors

**Deployment:**
- **[deployment/docs/DEPLOYMENT.md](deployment/docs/DEPLOYMENT.md)** - Container deployment guide
- **[deployment/docs/MERCURE.md](deployment/docs/MERCURE.md)** - Mercure SSE configuration

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE.md) file for details.
