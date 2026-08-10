# Chapter 10: Going Live — Playing a Real Server

The simulation runs everything in-process. The same strategic code can
play against a real game server over HTTP — the bot clients in
`client/ai/` already do exactly this.

## The wire protocol

The server exposes a simple JSON REST API (see `docs/NETWORK.md` for
details):

| Endpoint | Purpose |
|----------|---------|
| `POST /api/game/create` | create a lobby |
| `POST /api/game/{id}/join` | join; returns your `player_id` + JWT |
| `POST /api/game/{id}/ready` | mark ready |
| `POST /api/game/{id}/start` | start (host) |
| `POST /api/game/{id}/action` | submit `MOVE` / `ATTACK` / `DEPLOY` / `END_TURN` |
| `GET /api/game/{id}/state` | current state |
| `GET /api/game/{id}/actions` | your legal actions |

Action body:

```json
{"type": "MOVE", "data": {"token_id": 5, "destination": [10, 12]}}
```

## The bridge

`client/ai/http_ai_client.kuki` is a complete REST session wrapper:
create/join games, fetch state and actions, send actions. The AI client
(`client/ai/ai_client.kuki`) is the reference "turn loop":

```kukicha
state := sess.FetchState()
if IsGameOver(state)
    return
# is it my turn?
if cur_str isnt my_game_id
    return
actions := sess.FetchActions()
chosen := PickAction(actions, strategy)   # strategy here, not PlayTurn
sess.SendAction(chosen)
```

## What carries over from this course

Almost everything. The strategy logic — reading `Actions()`, picking
attacks by `WillKill`, marching toward objectives — is transport-agnostic.
The differences:

| Simulation (this course) | Live server |
|--------------------------|-------------|
| `api.Place(10, x, y)` | `{"type": "DEPLOY", "data": {"health_value": 10, "position": [x, y]}}` |
| `api.Actions()` | `GET .../actions` (same four variants, as JSON) |
| `api.MyTokens()` | state's `tokens` + your `player_id` |
| turn pushed to your function | you poll `state` / subscribe to SSE |
| `api.Memo` | your program's own state (or a database) |

## The shape of a live strategy

```
while game not over:
    wait for your turn (poll state, or SSE push)
    actions := fetch actions
    decision := YourStrategy(actions)   # the code you wrote in ch. 9
    send decision
```

The `choose_*` functions in `game/ai_strategy.kuki` are the production
versions of what you built in this course — read them as the reference
implementation.

## Your turn

1. Run the game server (`kukicha build ./server` then
   `./server/server`), create a game, and connect the bundled AI
   client: `./race-ai-client --create "test" --strategy random`.
2. Reimplement your chapter-9 `BestAttack` against the live API:
   fetch `/actions`, pick the `ATTACK` with `will_kill: true`, and
   POST it. The JSON shapes are the same four variants you switched
   over in the simulation.
3. Port `MarchBot` to a loop that polls `/state` every second and
   moves one token per poll — the exact shape of `client/ai/ai_client.kuki`.
