# MCP proxy (Phase 2.1 — in progress)

The game server's HTTP API (`/api/game/{id}/...`) is the agent seat. It is
deliberately curl-friendly, so an agent can play without any SDK:

- `POST /api/game/{id}/seat` is not required — `POST /api/game/create` and
  `/api/game/{id}/join` already label HTTP seats `HTTP_AI` (and accept
  `model` / `agent_kind` in the body).
- `GET /api/game/{id}/state`            — fog-filtered observation
- `GET /api/game/{id}/actions`         — legal actions
- `POST /api/game/{id}/action`         — submit one action
- `POST /api/game/{id}/say`            — radio chatter (broadcast as a
  `RadioChatter` event)

A thin MCP (stdio) adapter that maps these to LLM tools is still TBD. When
it lands here it must hold no game logic and no state: proxy only.
