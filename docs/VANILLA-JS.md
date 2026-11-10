# Vanilla JavaScript + WebGL2 for the Web Client

> **Status**: Phase 0 and Phase 1 are complete, and Phase 2 is under way —
> bloom, the crystal-effect animator and the marker-readability bump are
> built and verified in-browser. The vanilla WebGL2 renderer ships behind
> an opt-in flag (`?renderer=webgl2`); Babylon.js remains the default.
> The rest of Phase 2 (god rays, PBR/IBL) and the default-flip decision
> are open.
> Nothing in this document has been merged into a release — everything below
> was validated locally, in the browser, against a live game server.

This document records the argument for dropping Babylon.js, what has been
built and verified so far, the traps hit along the way, and what remains.

---

## 1. The premise

In October 2026 Paul Ford published ["The Web Is More Than
Enough"](https://ftrain.com/aboard-the-web-is-more-than-enough) (2026-10-21),
arguing that the browser's built-in platforms — Web Crypto, WebAssembly,
WebGL, Web Audio, SSE, offline storage — are vast, stable, and now far
cheaper to reach for than when they were built for Google-sized teams.
TinyLittleOffice shipped in 21 languages on Cloudflare's free tier.

The thesis gained a concrete proof point in the same thread: on the
[Hacker News discussion](https://news.ycombinator.com/item?id=50416456)
(2026-11-09), Simon Willison noted he builds features on three.js and
offline storage "multiple times per week", then took up socalgal2's comment
that "your LLM will do fine without it" and built a second, **no-libraries**
version of a Three.js Fabergé egg with plain JS and WebGL2. Per the
[HN comment](https://news.ycombinator.com/item?id=50416456) and the
[Claude transcript](https://claude.ai/share/e56d163e-2793-4677-aa11-191d5058b414)
of that session:

- three.js version: 77 KB, loads `three@0.170.0` from a CDN import-map
- vanilla version: ~98 KB, one self-contained file, hand-written PBR
  shader, shadow mapping, orbit controls, WebGL2-or-show-a-message fallback
- Reported results: whilenot-dev measured **120ms INP (vanilla) vs 504ms
  (three.js)**; Bengalilol reported **2.6 MB vs 173 KB** total downloads and
  better M1 frame rates; merelysounds notes some features were traded away
  (no glow, no glass transparency — faked with sparkles/inner glow)

The transferable lesson is not "WebGL2 is magic." It is: **for a bounded,
small, mostly-emissive stylized scene, one developer (or agent) can replace
a scene-graph library with a few thousand lines of plain JS + WebGL2 and get
a much smaller payload and faster page, at the price of owning all the
graphics code and losing a little visual gloss.**

### What our client actually spends on Babylon

Before any changes, the web client (`web_server/static/`, served with no
build step) shipped:

| Asset | Size | Gzip |
|---|---|---|
| `babylon.js` (Babylon.js 8.45.3, full UMD build) | 7.7 MB | **1.66 MB** |
| `babylon.gui.min.js` | 624 KB | 126 KB |
| `babylonjs.loaders.min.js` | 348 KB | 75 KB |
| First-party JS (25 files, 9,311 lines) | 325 KB | ~75 KB |

Findings from the survey (November 2026):

- The GUI and loaders were **never used** — zero first-party references, no
  `SceneLoader`/`.glb`/`.gltf`/`.obj`/`.stl` anywhere, no `BABYLON.GUI`.
  ~200 KB of gzip shipped for nothing.
- Two assets were fetched from `playground.babylonjs.com` at runtime: the
  `environment.env` IBL map and the `flare.png` particle sprite. A
  production dependency on a third-party CDN — a supply-chain and
  availability problem regardless of the migration.
- The first-party Babylon surface is ~223 `BABYLON.*` references across 11
  files (Vector3/Color3/MeshBuilder, StandardMaterial/PBRMaterial,
  GlowLayer, DefaultRenderingPipeline, VolumetricLightScatteringPostProcess,
  ParticleSystem, DynamicTexture, ArcRotateCamera, one ray-pick).
  Not used: GUI, loaders, shadow maps, physics, skeletons, WebGPU.
- First-party Babylon-coupled code was ~4,000 lines (~43% of client JS);
  the other 57% (DOM HUD, CSS, Web Audio, WebSocket, device detection) was
  already framework-free.

### The decision

Yes, we can convert — this codebase is an unusually good candidate (tiny
scene, no asset pipeline, DOM HUD, audio already raw Web Audio). Strategy:
stage it, keep Babylon as fallback, gate on a decision point.

---

## 2. What has been done

### Phase 0 — dead weight and third-party dependencies (done)

- Deleted `babylon.js` GUI/loaders scripts and vendored files (~200 KB gzip).
- Replaced the two `playground.babylonjs.com` assets:
  - `environment.env` → dropped IBL; gold frame and shard pillars got small
    emissive terms to stand in for it
  - `flare.png` → 64×64 radial-gradient `DynamicTexture` (local, no fetch)
- Fixed the board size: client `BOARD_CONFIG` said 24×24; server
  `shared/constants` says 18×18. The 3D view was framed for a board 6 cells
  wider than the one the server sends. Constants now 18×18.
- Fixed the server's `LOBBY_UPDATE` broadcast being unhandled — the client
  logged `Unknown message type: LOBBY_UPDATE` and dropped every lobby roster
  update. Added the case; verified the roster refreshes live.
- Silenced the crystal-effect replay: the fog/lightning/ghost effect and
  its sound re-fired on **every FULL_STATE echo** (10k+ duplicate log lines
  and blaring audio in one match). Both paths now replay only when the
  effect changes (`lastProcessedCrystalEffect`, like the mystery-event
  path).

### Phase 1 — vanilla WebGL2 spike, opt-in (done)

New `web_server/static/webgl2/` (~4,378 lines after Phase 2, ~38 KB gzip), wired in with
`?renderer=webgl2`:

| File | Lines | Role |
|---|---|---|
| `glmath.js` | 228 | vec3 + column-major mat4 (perspective/lookAt/multiply/invert/TRS) |
| `webgl2_core.js` | 170 | context, program/attrib management, VAO mesh builders (triangles/lines/points) |
| `webgl2_geometry.js` | 368 | ground/box/cylinder/UV/ico sphere/torus/quad/circle/square builders |
| `webgl2_camera.js` | 644 | spherical orbit overview + first person, wheel zoom, two-finger pinch/pan, focus/transition/FP smoothing |
| `webgl2_renderer.js` | 2,200 | `VanillaRenderer3D` — drop-in for `Renderer3D` (duck-typed), same public interface |
| `webgl2_textures.js` | 85 | canvas-generated textures (grid, health labels, soft-circle billboards) |
| `webgl2_bloom.js` | 313 | half-res bloom + composite (vignette, grain) — Phase 2 |
| `webgl2_crystal_effects.js` | 370 | fog/ghosts/lightning/whirlwind animator — Phase 2 |

Total ~4,378 lines (Phase 2 adds ~683, about 7 KB gzip).

Reached via `game_client.modules.js` → `VANILLA_RENDERER` const; falls back
to Babylon automatically if the vanilla renderer throws during init.

**Verified in-browser (Chrome), page by page:**

- Scene renders: board grid/cage, hex tokens, health labels, generators,
  crystal + gold wireframe cage, mystery torus rings, laser beams,
  objective pips, hover/valid-move/attack/threat indicators, selection
  glow (white emissive + 1.25 scale), star field, ambient/explosion/
  confetti particles, camera shake.
- Interaction works through the real event path: pick ray → cell, select,
  valid moves populate, click to move, server accepts, token eases to the
  cell, HUD updates, deploy flow (menu → canvas click → `TOKEN_DEPLOYED`).
- Sounds (AudioManager unchanged), timer, fog-of-war filtering, spectate
  mode (seat-cam), `?renderer=webgl2` + Babylon fallback both exercised.
- Multi-turn AI-vs-AI play: combat, deployments, turn timer, crystal effect
  triggers, all flowing correctly.

**Not yet observed:** a natural GAME_WON arriving over the wire (no match
has concluded yet). The victory path is verified otherwise: "triggerVictoryOnce()"
(confetti burst, camera trauma, crystal burst, the crystal sound) was
exercised and renders, and the alert() path is unmodified browser-native
code. Crystal effects were observed firing over the wire once (see Phase 2).

**Two silent white-box renderer bugs found and fixed:**

1. A soft white curved streak across the sky — UV-sphere star dome's pole
   pinch stretched texture to a smear. Replaced the sphere with a static
   point-sprite dome (250 tiny points, no texture, no poles).
2. `gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true)` was leaked to all
   subsequent texture uploads; would have rendered health-label text upside
   down. Each upload now flips then restores.

### Game-side bugs found while proving it played

The renderer worked before the game did. Three pre-existing defects had to
be fixed for the AI to function at all (see §3 for the shared cause):

- `game/ai_strategy.kuki` `resolveAction` panicked (`random.Choice` of an
  empty list) when a DeployAction had no valid positions — every AI died on
  turn 0. Now returns `ChosenEndTurn{}`.
- `ChooseAction` never reached `ChosenEndTurn{}` correctly — the AI chose
  END_TURN forever because the action parser dropped every field (see §3,
  "JSON / wire decoding"). With the parser fixed, two aggressive AIs play
  a full, combative match.
- `server/http_handler.kuki` and `server/ws_endpoint.kuki` read
  `max_players` as `is int` — JSON numbers decode as `float64`, so the
  lobby stepper was ignored and **every game was a 4-player one**. Now
  accepts `int`/`int64`/`float64` (matches `action_validation.kuki`).

`kukicha check ./game ./server ./client/ai` passes; `make test` passes;
`kukicha fmt --check .` clean. (Note: `game/main.go` et al. are
gitignored; `make test` regenerated everything it needed.)

### Phase 2 — visual parity (partial; built and verified in-browser)

Built since the Phase 1 spike, including the verification pass in Chrome
(November 2026):

- **Bloom** (`webgl2_bloom.js`) — half-res separable gaussian (9 taps,
  two ping-pong iterations) composited additively over the scene, plus a
  soft vignette and a whisper of film grain in the same pass. The scene
  renders into a full-res FBO (RGBA16F where `EXT_color_buffer_float` is
  available — it is, in Chrome — RGBA8 otherwise) with a depth
  renderbuffer. `?bloom=0` opts out entirely and draws straight to the
  canvas, identical to the Phase 1 path. Verified live: toggling
  `renderer.bloomPass` off at runtime flattens the beams and generators
  visibly; the FBO comes up complete, no shader or link errors are
  logged.
- **Crystal-effect animator** (`webgl2_crystal_effects.js`) — the Babylon
  `CrystalEffectAnimator` ported against the vanilla renderer's
  primitives. Exercised in-browser, all four effects: fog (16 radial
  smoke billboards — seen hazing the whole board), whirlwind (8 spiral
  point emitters — cyan spiral streams seen spreading), damage boost
  (jagged sky→token bolt + additive flash sphere + spark burst — a forced
  strike renders, the flash sphere catches the bloom knee), phantom
  enemies (5 ghost billboards — object emission verified: correct
  alpha/color/texture; hard to make out at overview distance). The
  trigger path itself (`checkCrystalEffectTrigger`) is unchanged and
  replay-guarded; not yet observed firing end-to-end from the wire — the
  "whoosh" heard during verification was the selection sound, not an
  effect. Sounds flow through the unchanged `AudioManager`.
- **Marker readability** — valid-move/attack fill quads raised from 0.16
  to 0.35 alpha, drawn additively with brightness 1.8; threat-hover
  squares bumped to match. Still to be judged at zoom on a busy board.
- **Two more silent white-box bugs found by reading, then fixed:**
  3. `VERT_UNLIT` declared `aUV` at location 1 — the *normal* attribute's
     location (fixed VAO layout is 0=position, 1=normal, 2=UV), so every
     unlit draw read the normal vector as its UVs. `aUV` is now location 2.
  4. The floating-text texture upload leaked `UNPACK_FLIP_Y_WEBGL`
     (same global-state trap as the Phase 1 health-label bug). Each
     upload now flips then restores.

Re-verified after the changes: page loads clean, full match plays, pick →
select works through the real event path (valid moves populate, the
"MOVEMENT • 3 targets" hint appears, selection glow shows), turn timer,
fog-of-war opponent filtering, and the AI seat all behave.

**Verification notes (second pass, as a spectator):**

- **Seat-cam spectating works end-to-end.** `SPECTATE` with `follow=player_0`
  binds the connection, the vanilla renderer comes up, and the fog-filtered
  stream flows. Nice trick for watching a match conclude without a seat.
- **A crystal effect observed firing over the wire**: on connect, the fresh
  client logged `Crystal effect triggered: 3 for player player_0` (damage
  boost replayed once from the persisted `last_triggered_crystal_effect`,
  replay-guard intact) and played the matching sound. The forced-trigger
  path was already proven; this closes the loop.
- **Zoom is glued to the board center.** Wheel dollies the radius but the
  target never leaves the crystal — past ~radius 110 the crystal fills the
  frame. Pan/drag moves it (map-style grab pan), and direct spherical edits
  (`camera.target/alpha/beta/radius`) work for a precise camera. Noted, not
  changed: this matches the Babylon overview design.
- **First-person mode toggles (V) and survives WASD**: with no controlled
  token, `W` prints the "No token controlled! Press TAB to cycle tokens"
  banner. WASD movement with a controlled token and TAB cycling remain
  untested.
- **Health labels are crisp quads but glyph legibility at zoom is
  unverified** (fog of war masks enemy tokens; friendly tokens sit far
  away in the deployment corner). The flip_y leak is fixed; verify
  readability on a zoomed-in board next.
- **In-browser spectating is wired end-to-end (fixed and verified).** Two
  defects stood between the lobby browser and the seat-cam view, both
  fixed: (1) WS `LIST_GAMES` returned only joinable lobbies, so the
  `IN_PROGRESS` Spectate button never rendered — it now mirrors the HTTP
  `/api/games` list (available + in-progress); (2) the seat-chooser overlay
  sat at a lower z-index than the always-on-top HUD (100) and then the
  fixed lobby panel (2000), so clicks hit those layers instead of the
  seat buttons — now 2100, below the victory modal (3000) and toast
  (9999). Verified with a side instance (`HTTP_PORT=8081` game server +
  `WEB_PORT=8001 GAME_SERVER_URL=http://localhost:8081` web proxy):
  lobby browser lists the IN_PROGRESS match → SPECTATE → seat chooser →
  click "VerifyAI HTTP_AI" → spectator view streams for that seat. Note:
  the page's CSP (`default-src 'self'`) blocks a :8000 page from opening
  `ws://localhost:8081` directly, so side-instance verification must go
  through a side web proxy, not a direct port.

---

## 3. Gotchas

### JSON / wire decoding (the big one)

This stack — Go's `jsonv2` used under the hood everywhere including the
stdlib fetch decoder — has two properties that break naive assertions:

1. **Numbers decode as `float64`.** `if x is int as v` never matches a JSON
   number. Silently. Three unrelated bugs turned out to be exactly this:
   the AI's action parser dropped all numerics, the lobby's `max_players`
   silently stayed at 4, and any hand-rolled `is int` on a wire is a landmine.
2. **Arrays decode as one-level `[]any`.** `[][]int` from the wire simply
   does not match `is list of list of int as v` — you must walk one level at
   a time (`[]any` → each element `[]any` → each element a float). The old
   parser's nested assertion never matched and silently dropped
   `valid_destinations`/`positions`.

Rules for this codebase:

- Decode one level at a time; convert with `stdlib/cast` (`cast.ToIntOr`).
- Accept `int`/`int64`/`float64` anywhere a JSON number lands (see
  `action_validation.kuki` for the pattern; replicate it).
- Never trust a bare `is` assertion on a wire value. Ask the probe
  program (`/tmp/opencode/probe/main.go` pattern) if the types confuse you.

### The game package

- `//` is **not a comment** in Kukicha — it's two division operators and a
  syntax error. Use `#`. (Cost me a silently-broken `game/` once;
  `kukicha check ./client/ai` then blamed the importer for a missing type.)
- `kukicha check` errors surface at the **importer**, not the culprit.
  "undefined type X in package gamepkg" against `client/ai/` or `learn/`
  usually means a syntax error inside `game/` — fix `game/` first.
- A variant enum cannot have methods. Use free functions.
- Empty `when` arms are not allowed (`syntax/empty-arm`).
- `map` iteration order is random. Anything order-dependent (seat order,
  colors, turn order) must go through the explicit ordered helpers
  (`orderedPlayerIds`, `orderedPlayers`, `PlayerColorIndexes`). This has
  caused real defects; keep the discipline.
- Tests are `*_test.kuki` and are only transpiled by `kukicha brew`
  (`make test`). `go test ./...` alone runs stale generated code.

### The web client

- **No build step, no bundler, no cache headers or hash busting.** Every
  page load heuristically re-fetches modules, but Chrome's heuristic caching
  can serve stale JS with no error. If the page behaves like the old code,
  hard-reload (`ignoreCache: true` in DevTools terms, or Ctrl+Shift+R).
  Verify with a fresh `?param` if in doubt.
- The game board is **18×18** (server `shared/constants`). Any client that
  assumes otherwise produces an oversized cage and an off-center camera.
- Fog of war is real: invisible enemy tokens are absent/masked and have
  `position: null`. Every `token.position[0/1]` read needs a null check.
  This is why spectators see "Tokens: 0/20" for the opponent — expected,
  not a bug.
- The server's `last_triggered_crystal_effect` **persists** until the next
  effect fires. Any code that reacts to it on every update (the Babylon
  client does the same thing) will replay the effect + sound hundreds of
  times per match. Guard on change, like the mystery-event path.
- Spectator is seat-cam: one seat per connection, union-of-vision across
  seats can reconstruct the board. Fine for casual play; not an integrity
  boundary.
- **Full-res screenshots blow the upstream media budget.** The canvas is
  devicePixelRatio-scaled (e.g. 728×629 CSS at DPR 1.667 → 1213×1048
  device pixels), and Chrome DevTools screenshots of it saved as inline
  PNG run ~3.5 MB each. Ten of those in one session exceed the
  `airlock_error: inlined media exceeds the 33554432 byte total limit`
  budget, and every subsequent upstream call then fails. Take them with
  `format: "jpeg"`, `quality: 60` and an explicit `filePath` (~100 KB), or
  quality 25 for a quick check (~55 KB); prefer text snapshots over images
  otherwise. This error ended an earlier Phase 2 session.
- **A full lobby is invisible to the list endpoints, and join 400s with no
  explanation.** `/api/games` and WS `GAME_LIST` only show lobbies with a
  free seat (WAITING) or already in progress. A full WAITING lobby (2/2)
  simply disappears, and `JOIN_GAME` → the HTTP join endpoint both return
  a bare `failed to join game`. The trap: a timed-out foreground
  `./race-ai-client poll --join …` usually survives its shell, keeps its
  seat, and readies itself — the lobby then looks 1/2 from anywhere but
  is actually 2/2, and your second join attempt 400s. Check the lobby
  roster (WS `LOBBY_UPDATE` / the host screen), not the HTTP status.

### WebGL2 specifics worth remembering

- `gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, ...)` is global state and leaks
  into every subsequent texture upload. Flip per-texture, then restore.
- UNRESOLVED for later: lines are always 1px wide (WebGL ignores
  `lineWidth` on most platforms), which is fine for the neon look here.
- `antialias: true` on the context + no culling in the spike — tiny scene,
  overdraw irrelevant; revisit if profiling says otherwise.
- Eye-height first-person camera rides the same spherical representation
  (target 200 units ahead), so one camera implementation serves both modes.
- The board ground is an 18×18 **texture** grid; wall cage is `GL_LINES`;
  the ground and sky are deliberately untextured elsewhere.

---

## 4. The next phase

### Phase 2 — visual parity (in progress)

1. ~~Bump the marker readability~~ — **done**: fills 0.16 → 0.35 alpha,
   additive, brightness 1.8. Judged at playing distance; worth one more
   pass at zoom on a busy board.
2. ~~Bloom / glow~~ — **done** (`webgl2_bloom.js`; threshold 0.55, strength
   0.9, half-res, `?bloom=0` escape hatch). See §2.
3. **God rays** — Babylon's `VolumetricLightScatteringPostProcess`. Emulate
   with a radial-blur pass from the crystal's screen position, or delete
   outright (crystal already breathes/pulses).
4. ~~Crystal effects~~ — **done** (`webgl2_crystal_effects.js`, all four);
   see §2. First-choice follow-up is a wire-path (not forced) trigger
   observed in-browser.
5. **PBR/IBL** — currently Lambert + Blinn-Phong. True PBR (GGX) + a small
   procedural environment (or baked gradient cube) would restore the gold
   and gems to full richness. This is also the moment to decide on the
   gold: keep the current emissive fake (free, moody) or pay the shader
   rewrite.
6. **Floating text / health labels** — verify at zoom, check flip_y and
   readability.
7. **Chroma aberration / film grain / sharpen** — optional cosmetics from
   the Babylon pipeline. The composite pass already carries a static-hash
   film grain and a vignette at trivial cost; chromatic aberration and
   sharpen are still undecided.

### Decision gate

Make the call once parity is close:

- **A — Default vanilla.** `?renderer=` becomes the normal path; Babylon
  dropped (delete the 1.66 MB, the two `<script>` tags, `game_client.renderer.js`,
  `renderer.*.js`, `camera_controller.js`, `renderer.special.js` env map).
  Payload: ~85 KB gzip total for the whole client.
- **B — Keep Babylon default.** Only if parity stalls. In that case still
  consider tree-shaking `@babylonjs/core` (drops the 1.66 MB to maybe
  300–600 KB), accepting the new build step.
- **C — Ship both, flag-selected.** Current state; defensible only as a
  transition.

### Testing backlog (blocks calling it done)

- Game-over screen seen live from an actual GAME_WON. The confetti/trauma/
  crystal-burst path is verified (forced `triggerVictoryOnce()` renders;
  alert() unverified); no match has concluded yet — spectate the AI match
  with `SPECTATE` + `follow=<seat>` (see §2).
- Mobile/touch: tap-to-select, tap-to-move, pinch zoom, two-finger pan,
  health labels at small viewport sizes.
- Mid-game first-person toggle (V) works; WASD with a controlled token,
  TAB token cycle, and pointer-lock look remain untested.
- First-person pointer lock look.
- Long-match stability (memory: the mesh/material caches grow per
  `updateGameState`; watch for leaks across many turns).
- The lobby's live member list with three players; AI reconnection flow.

### Scoreboard (what Babylon parity means)

| Capability | Babylon | Vanilla |
|---|---|---|
| Board, cage, ground | ✓ | ✓ |
| Tokens, health labels, selection glow | ✓ | ✓ |
| Generators + crystal + lasers | ✓ | ✓ (no refraction) |
| Mystery rings | ✓ | ✓ (spin/pulse only, no landing burst) |
| Indicators (hover/move/attack/threat/pips) | ✓ | ✓ |
| Particles (explosions, confetti, ambient dust) | ✓ | ✓ |
| Camera (overview + first-person) | ✓ | ✓ |
| Picking | ✓ `scene.pick` | ✓ ray-plane (equivalent for grid cells) |
| Bloom / glow layer | ✓ | ✓ (half-res gaussian + composite bloom/vignette/grain) |
| Chromatic aberration / sharpen | ✓ | ✗ (but: vignette + film grain in the composite pass) |
| God rays | ✓ | ✗ |
| Crystal effects (fog/ghost/lightning/whirlwind) | ✓ | ✓ (stub replaced; verified in-browser) |
| PBR / IBL | ✓ | ~Lambert/Blinn-Phong |
| Refraction (shard pillars) | ✓ | ✗ |

---

## 5. Open questions

- **Bloom or no bloom?** Decided for now: on by default, half-res,
  `?bloom=0` as the escape hatch. Still worth an INP/frame-time check on
  a low-end device — the composite pass is cheap, but the half-float
  scene FBO write at full res is not free.
- **Overview framing is tight on square-ish viewports.** The overview pose
  (beta 60°, radius 0.8 × board diagonal, 40° fov) crops the deployment
  corners off-screen at ~1:1 aspect — my tokens at (0,0)-(2,0) sat pinned
  to the top edge. It matches the Babylon defaults, so it's not a
  regression, but consider raising the radius multiplier (or fov, or
  clamping by aspect ratio) before the default flip.
- **Keep Babylon in-repo as fallback forever?** Cost of keeping is one file
  + scripts; keeping it means we can flip back cheaply. Recommendation:
  keep it until the default-flip ships, then delete.
- **Test suite?** There is currently **no automated test for the 3D layer
  at all.** A headless screenshot/smoke test (playwright-style) before the
  default-flip would be the first net under the renderer.
- **Babylon version bump?** If we keep Babylon during transition: 8.45.3 is
  pinned; 9.35.0 is current. Don't upgrade unless forced.
- **`main.kuki` cache headers** — the web server sets no cache headers and
  no content hashing, so every deploy is a hard reload for first-time
  visitors anyway. Consider content hashes + immutable static paths if we
  flip the vanilla default.

## 6. Reproducing

```bash
make server-run          # game server, http://localhost:8080
make web-server-run      # web client + reverse proxy, http://localhost:8000
```

Then `http://localhost:8000/?renderer=webgl2` (hard-reload once). Add
`&bloom=0` to compare against the pre-bloom direct path. Create a
2-player game, add an AI with `./race-ai-client poll --join <game-id>
--name AI --strategy aggressive` next to your seat, ready both, start.

Launch the AI client **detached** (background), not in a foreground shell
with a timeout — see §3, "a full lobby is invisible … join 400s". Compare
against the Babylon path by dropping the flag.

When verifying in Chrome DevTools, take screenshots with `filePath` +
`format: "jpeg"` (see §3) — inline full-page PNGs at DPR 1.667 each run
~3.5 MB and kill the session.
