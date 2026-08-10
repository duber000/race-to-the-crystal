# Learn to Program with Minecraft — Follow-Up

**Book:** *Learn to Program with Minecraft* by Craig Richardson (Python, Minecraft: Pi Edition).
Local copy: `~/Downloads/epubs/LearntoProgramwithMinecraft.epub`

**Linked repo:** Race to the Crystal (`~/repos/kukicha/race-to-the-crystal`) — Kukicha/Go multiplayer strategy game with desktop + browser clients.

## Status: IMPLEMENTED (2026-08-10)

The follow-up became the **learn-to-program course** in this repo:

- **Learner API + simulation** — `learn/learn_api.kuki` (the `LearnerAPI`
  teaching facade: `Say`/`Board`/`Place`/`Move`/`Attack`/`Done`/`Memo`/
  `Recall`/`Actions`/`MyTokens`/…) and `learn/simulation.kuki` (in-process
  game runner; learner plays player 0 against the AI strategies).
- **Ten example scripts** — `learn/examples/01-hello/` … `10-strategy-ladder/`,
  each runnable with `kukicha run learn/examples/<name>/`
  (or `make learn-run NAME=<name>`).
- **Ten tutorial chapters** — `docs/tutorials/`, mapping the book's
  project-based progression (variables → math → conditionals → loops →
  functions → collections → types/methods → action-driven strategy) onto
  the game, for programmers learning Kukicha.
- **Going-live path** — `docs/tutorials/10-going-live.md` adapts the same
  strategy code to the REST game server (the `client/ai/` bot clients are
  the reference).

**Design decisions recorded here:**
- Audience: programmers learning Kukicha (not complete beginners).
- Runtime: in-process simulation for the course, REST for going live.
- Scope: the real game only (no free-form sandbox build mode).
- Tutorials live in this repo so scripts import the game package directly
  and are covered by `make learn-check` / `make learn-test`.

**Side fix:** implementing the simulation surfaced a game bug —
`_auto_deploy_starting_tokens` mutated copies from the reserve slice
instead of the tokens in `GameState.tokens`, so starting tokens occupied
cells but were never marked deployed. Fixed in `game/game_state.kuki`;
`game/player.kuki` gained a `Name()` accessor and `game/token.kuki`
`Position()`/`ID()` for cross-package use by the learn package.
